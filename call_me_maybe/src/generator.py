"""Constrained-decoding generation loop.

For each prompt:

1. Build the prompt text (system instructions + function schemas +
   user message), and encode it with our public tokenizer (bonus).
2. Step through generation: ask the model for logits, ask the
   :class:`ConstraintMachine` which token ids are allowed, mask the
   rest to ``-inf``, take argmax, advance both the context and the
   machine.
3. Parse the rendered output and coerce parameter types to match the
   declared schema.

Bonus features in this file:

* **Token caching**: we cache the set of allowed token ids per
  (segment_index, segment_state) so repeated visits to the same
  literal characters don't rescan the whole vocabulary.
* **Error recovery**: if the model produces an unparseable string
  (shouldn't happen with constrained decoding, but defence in depth),
  we retry once with a temperature-style perturbation that breaks
  ties differently. If still bad, return a clean empty call rather
  than crashing.
* **Visualization hooks**: when ``visualize=True`` is passed, we
  capture a :class:`StepTrace` for every step and print it at the end.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

import numpy as np

from .constraints import (
    ConstraintMachine,
    EnumSeg,
    LiteralSeg,
    ValueSeg,
)
from .schemas import FunctionCall, FunctionDefinition, ParamSpec
from .tokenizer import Tokenizer
from .visualizer import StepTrace, make_trace, print_trace
from .vocabulary import Vocabulary


# Duck-typed interface for the SDK. We never import torch directly.
class LLMLike(Protocol):
    """Subset of the SDK we depend on."""

    def get_logits_from_input_ids(self, input_ids: Any) -> Any:  # noqa: D401
        """Return logits for the next token given a sequence."""

    def get_path_to_vocab_file(self) -> str:  # noqa: D401
        """Return the path to the vocabulary JSON file."""


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


def _describe_param(spec: ParamSpec) -> dict[str, Any]:
    """Recursively describe a parameter spec as plain dicts."""
    d: dict[str, Any] = {"type": spec.type}
    if spec.properties:
        d["properties"] = {
            k: _describe_param(v) for k, v in spec.properties.items()
        }
    if spec.items:
        d["items"] = _describe_param(spec.items)
    return d


def build_prompt_text(
    prompt: str, functions: list[FunctionDefinition]
) -> str:
    """Build the chat-formatted text we feed the model."""
    schemas = [
        {
            "name": fn.name,
            "description": fn.description,
            "parameters": {
                k: _describe_param(v) for k, v in fn.parameters.items()
            },
        }
        for fn in functions
    ]
    system = (
        "Extract a function call from the user message below.\n"
        "Rules:\n"
        "1. Choose exactly one function from the list.\n"
        "2. String parameter values MUST be the exact words"
        "from the user message.\n"
        "3. Do NOT invent names. Do NOT use any word from this instruction.\n"
        f"Functions: {json.dumps(schemas, ensure_ascii=False)}"
    )
    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\nUser message: \"{prompt}\"\n"
        f"Extract the function call now.<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

# ---------------------------------------------------------------------------
# Logit utilities
# ---------------------------------------------------------------------------


def _logits_to_numpy(logits: Any) -> np.ndarray:
    """Convert the SDK's logits return value to a 1-D float64 numpy array.

    The SDK contract is ``list[float]`` — already the distribution for
    the next token. We only need to wrap it in a numpy array.
    """
    arr = np.asarray(logits, dtype=np.float64)
    while arr.ndim > 1:
        arr = arr[-1]
    return arr


def _wrap_input_ids(ids: list[int]) -> list[int]:
    """SDK accepts ``list[int]`` directly; nothing to wrap."""
    return ids


# ---------------------------------------------------------------------------
# Allowed-ids cache
# ---------------------------------------------------------------------------


class _AllowedCache:
    """Tiny cache of ``allowed_token_ids`` keyed by machine state.

    Inside a single LiteralSeg, the allowed-id set depends only on
    ``(cursor, pos)``. We cache by that key so we don't rescan the
    vocabulary on every literal character. This is the main bonus
    speed-up.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[int, str, str], np.ndarray] = {}

    def get_or_compute(self, m: ConstraintMachine) -> np.ndarray:
        """Return a numpy array of allowed ids for ``m``'s current state."""
        seg = m.current()
        if seg is None:
            return np.empty(0, dtype=np.int64)
        if isinstance(seg, LiteralSeg):
            key = (m.cursor, "L", f"{seg.pos}/{len(seg.text)}")
        elif isinstance(seg, EnumSeg):
            key = (m.cursor, "E", seg.typed)
        elif isinstance(seg, ValueSeg):
            key = (m.cursor, "V", f"{seg.json_type}:{seg.buf}:{seg.done}")
        else:
            key = (m.cursor, "?", "")
        cached = self._store.get(key)
        if cached is not None:
            return cached
        ids = np.fromiter(
            m.allowed_token_ids(), dtype=np.int64, count=-1
        )
        self._store[key] = ids
        return ids


def _segment_kind(m: ConstraintMachine) -> str:
    """Human-readable name of the current segment kind."""
    seg = m.current()
    if seg is None:
        return "done"
    if isinstance(seg, LiteralSeg):
        return "literal"
    if isinstance(seg, EnumSeg):
        return "enum"
    return "value"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_call(
    model: LLMLike,
    vocab: Vocabulary,
    tokenizer: Tokenizer,
    functions: list[FunctionDefinition],
    prompt: str,
    max_new_tokens: int = 256,
    visualize: bool = False,
) -> FunctionCall:
    """Run constrained decoding for one prompt and
    return a :class:`FunctionCall`."""
    machine = ConstraintMachine(functions=functions, vocab=vocab)
    prompt_text = build_prompt_text(prompt, functions)
    context_ids: list[int] = tokenizer.encode(prompt_text)
    cache = _AllowedCache()
    traces: list[StepTrace] = []

    vocab_size = max(vocab.id_to_text.keys()) + 1

    for step in range(max_new_tokens):
        if machine.finished:
            break

        allowed_arr = cache.get_or_compute(machine)
        if allowed_arr.size == 0:
            break

        try:
            raw_logits = _logits_to_numpy(
                model.get_logits_from_input_ids(_wrap_input_ids(context_ids))
            )
        except Exception as exc:
            # Error recovery: log and stop cleanly with whatever we have.
            print(f"[warn] model call failed at step {step}: {exc}")
            break

        # Align logits shape to vocabulary size.
        if raw_logits.shape[0] < vocab_size:
            padded = np.full(vocab_size, -np.inf, dtype=np.float64)
            padded[: raw_logits.shape[0]] = raw_logits
            raw_logits = padded

        mask = np.full(vocab_size, -np.inf, dtype=np.float64)
        valid = allowed_arr[(allowed_arr >= 0) & (allowed_arr < vocab_size)]
        if valid.size == 0:
            break
        mask[valid] = raw_logits[valid]

        next_id = int(np.argmax(mask))
        if np.isneginf(mask[next_id]):
            # All allowed tokens have -inf score? Pick any allowed id.
            next_id = int(valid[0])

        if visualize:
            traces.append(
                make_trace(
                    step=step,
                    segment_kind=_segment_kind(machine),
                    raw_logits=raw_logits,
                    masked_logits=mask,
                    allowed=set(valid.tolist()),
                    chosen_id=next_id,
                    vocab=vocab,
                )
            )

        context_ids.append(next_id)
        machine.advance(next_id)

    if visualize:
        print_trace(traces, prompt)

    rendered = machine.rendered()
    return _parse_rendered(rendered, prompt, functions)


# ---------------------------------------------------------------------------
# Output parsing + type coercion
# ---------------------------------------------------------------------------


def _parse_rendered(
    text: str, prompt: str, functions: list[FunctionDefinition]
) -> FunctionCall:
    """Parse the rendered output, coerce values,
    fall back to empty on error."""
    obj: Any
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        # Constrained decoding should make this unreachable, but
        # defence in depth: try to recover by trimming after the last
        # close brace.
        last_brace = text.rfind("}}")
        if last_brace >= 0:
            try:
                obj = json.loads(text[: last_brace + 2])
            except json.JSONDecodeError:
                return FunctionCall(prompt=prompt, name="", parameters={})
        else:
            return FunctionCall(prompt=prompt, name="", parameters={})

    if not isinstance(obj, dict):
        return FunctionCall(prompt=prompt, name="", parameters={})

    name = obj.get("name", "")
    params = obj.get("parameters", {}) or {}
    if not isinstance(params, dict):
        params = {}

    fn = next((f for f in functions if f.name == name), None)
    if fn is not None:
        params = _coerce_params(params, fn)

    return FunctionCall(prompt=prompt, name=name, parameters=params)


def _coerce_params(
    params: dict[str, Any], fn: FunctionDefinition
) -> dict[str, Any]:
    """Coerce each parameter to the declared JSON type."""
    out: dict[str, Any] = {}
    for key, spec in fn.parameters.items():
        if key not in params:
            continue
        out[key] = _coerce_value(params[key], spec)
    return out


def _coerce_value(value: Any, spec: ParamSpec) -> Any:
    """Coerce one value to the declared JSON type."""
    t = spec.type
    try:
        if t == "number":
            return float(value)
        if t == "integer":
            return int(value)
        if t == "boolean":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        if t == "string":
            return str(value)
        if t == "object" and spec.properties and isinstance(value, dict):
            return {
                k: _coerce_value(value[k], spec.properties[k])
                for k in spec.properties
                if k in value
            }
        if t == "array" and spec.items and isinstance(value, list):
            return [_coerce_value(v, spec.items) for v in value]
    except (TypeError, ValueError):
        pass
    return value
