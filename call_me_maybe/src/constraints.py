"""Constrained-decoding state machine.

This module is the heart of the project. The idea: we never let the
LLM choose the JSON structure -- we choose it. The model only fills
in the function name and the parameter values, and even there we
restrict its choices to the schema.

We represent the JSON we want to emit as a sequence of *segments*:

* :class:`LiteralSeg` -- a fixed string that must appear verbatim.
* :class:`EnumSeg`    -- pick exactly one string from a finite list
                        (e.g. the function name).
* :class:`ValueSeg`   -- a typed JSON scalar (number / integer /
                        string / boolean).

At every generation step the machine answers: *which token ids would
keep us on a valid path?* Every other token id receives ``-inf`` in
the logits, so the model is physically incapable of breaking the
schema.

Two subtle properties make this robust:

1. Tokens may **span segment boundaries** (e.g. ``", "`` may close
   one segment and start the next). We consume tokens
   character-by-character and roll over to the next segment as soon
   as the current one is complete.
2. Enum choices are only **locked in** when no longer prefix is still
   reachable. This prevents prematurely committing to ``fn_add`` when
   ``fn_add_numbers`` is also a valid choice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .schemas import FunctionDefinition, ParamSpec
from .vocabulary import Vocabulary


# ---------------------------------------------------------------------------
# Segment dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LiteralSeg:
    """A fixed string to emit verbatim."""

    text: str
    pos: int = 0

    def clone(self) -> "LiteralSeg":
        """Deep-copy enough to support snapshot/restore."""
        return LiteralSeg(self.text, self.pos)


@dataclass
class EnumSeg:
    """Pick exactly one string from ``choices``.

    ``typed`` records the characters produced so far; it must be a
    prefix of at least one remaining choice. The segment completes
    once ``typed`` equals one of the choices AND no other choice
    extends ``typed`` further.
    """

    choices: list[str]
    typed: str = ""

    def clone(self) -> "EnumSeg":
        return EnumSeg(list(self.choices), self.typed)


@dataclass
class ValueSeg:
    """A typed JSON scalar."""

    json_type: str
    buf: str = ""
    done: bool = False
    # For strings, optionally a max length to avoid runaway generation.
    max_string_len: int = 64

    def clone(self) -> "ValueSeg":
        return ValueSeg(
            self.json_type,
            self.buf,
            self.done,
            self.max_string_len,
        )


Segment = LiteralSeg | EnumSeg | ValueSeg


# ---------------------------------------------------------------------------
# Plan-building helpers
# ---------------------------------------------------------------------------


def _segments_for_value(spec: ParamSpec, prefix: str = "") -> list[Segment]:
    """Return the segments that emit a value of type ``spec``.

    ``prefix`` is prepended as a literal (e.g. ``", "`` between params).
    For objects we recurse, emitting ``{ "k1": v1, "k2": v2 }``.
    For arrays of scalars we emit ``[ v1 ]`` (single element).
    """
    out: list[Segment] = []
    t = spec.type

    if t == "string":
        out.append(LiteralSeg(f'{prefix}"'))
        out.append(ValueSeg(json_type="string"))
        out.append(LiteralSeg('"'))
    elif t in ("number", "integer", "boolean"):
        if prefix:
            out.append(LiteralSeg(prefix))
        out.append(ValueSeg(json_type=t))
    elif t == "object" and spec.properties:
        keys = list(spec.properties.keys())
        out.append(LiteralSeg(f"{prefix}{{"))
        for i, key in enumerate(keys):
            pfx = "" if i == 0 else ", "
            out.append(LiteralSeg(f'{pfx}"{key}": '))
            # Recurse: the value of this key.
            sub_spec = spec.properties[key]
            out.extend(_segments_for_value_inline(sub_spec))
        out.append(LiteralSeg("}"))
    elif t == "array" and spec.items:
        out.append(LiteralSeg(f"{prefix}["))
        out.extend(_segments_for_value_inline(spec.items))
        out.append(LiteralSeg("]"))
    else:
        # Fallback: treat unknown types as strings.
        out.append(LiteralSeg(f'{prefix}"'))
        out.append(ValueSeg(json_type="string"))
        out.append(LiteralSeg('"'))
    return out


def _segments_for_value_inline(spec: ParamSpec) -> list[Segment]:
    """Like :func:`_segments_for_value` but with no leading prefix."""
    return _segments_for_value(spec, prefix="")


def build_outer_plan(functions: list[FunctionDefinition]) -> list[Segment]:
    """Build the segments for the *outer* JSON object.

    The output stops after ``"parameters": {`` because the parameter
    body depends on which function the model picks, and we don't
    know that until the EnumSeg completes. The machine appends the
    rest dynamically; see :class:`ConstraintMachine._inject_params_tail`.
    """
    fn_names = [f.name for f in functions]
    return [
        LiteralSeg('{"name": "'),
        EnumSeg(choices=fn_names),
        LiteralSeg('", "parameters": {'),
    ]


def build_params_tail(fn: FunctionDefinition) -> list[Segment]:
    """Build the segments for the body of ``"parameters": { ... }}``.

    Produces ``"<key>": <value>`` pairs separated by ``", "``, then a
    closing ``"}"`` for the parameters object and a final ``"}"`` for
    the outer object.
    """
    segments: list[Segment] = []
    keys = list(fn.parameters.keys())

    if not keys:
        segments.append(LiteralSeg("}}"))
        return segments

    for i, key in enumerate(keys):
        pfx = "" if i == 0 else ", "
        segments.append(LiteralSeg(f'{pfx}"{key}": '))
        segments.extend(_segments_for_value_inline(fn.parameters[key]))

    # Closing brace of parameters object + closing brace of the outer
    # object. We split them so a single LiteralSeg cannot be confused
    # with a value boundary.
    segments.append(LiteralSeg("}}"))
    return segments


# ---------------------------------------------------------------------------
# Value-segment DFAs (small per-character grammars)
# ---------------------------------------------------------------------------


def _value_can_extend(seg: ValueSeg, ch: str) -> bool:
    """True iff appending ``ch`` keeps ``seg.buf`` a valid value prefix."""
    buf = seg.buf + ch
    t = seg.json_type

    if t == "boolean":
        return "true".startswith(buf) or "false".startswith(buf)

    if t == "integer":
        if buf == "-":
            return True
        body = buf[1:] if buf.startswith("-") else buf
        if not body or not body.isdigit():
            return False
        # No leading zeros except literal "0".
        return len(body) == 1 or body[0] != "0"

    if t == "number":
        if buf == "-":
            return True
        body = buf[1:] if buf.startswith("-") else buf
        if not body:
            return False
        if body.count(".") > 1:
            return False
        if body.endswith("."):
            head = body[:-1]
            if not head.isdigit():
                return False
            return len(head) == 1 or head[0] != "0"
        if "." in body:
            head, tail = body.split(".", 1)
            if not head.isdigit() or not tail.isdigit():
                return False
            return len(head) == 1 or head[0] != "0"
        if not body.isdigit():
            return False
        return len(body) == 1 or body[0] != "0"

    if t == "string":
        if len(seg.buf) >= seg.max_string_len:
            return False
        # Forbid characters that need JSON escaping; keeps the surface
        # simple and guarantees the next literal segment's ``"`` ends
        # the string cleanly.
        if ch in ('"', "\\"):
            return False
        # Forbid raw control characters.
        if ord(ch) < 0x20:
            return False
        return True

    return False


def _value_is_complete(seg: ValueSeg) -> bool:
    """True iff ``seg.buf`` is already a valid, complete value."""
    t = seg.json_type
    buf = seg.buf
    if t == "boolean":
        return buf in ("true", "false")
    if t == "integer":
        if not buf or buf == "-":
            return False
        body = buf[1:] if buf.startswith("-") else buf
        return body.isdigit() and (len(body) == 1 or body[0] != "0")
    if t == "number":
        if not buf or buf == "-":
            return False
        body = buf[1:] if buf.startswith("-") else buf
        if body.endswith(".") or body.startswith("."):
            return False
        if "." in body:
            head, tail = body.split(".", 1)
            return head.isdigit() and tail.isdigit()
        return body.isdigit()
    if t == "string":
        return len(buf) >= 1
    return False


def _value_must_continue(seg: ValueSeg) -> bool:
    """True iff the value cannot end yet (e.g. partial ``tru``)."""
    t = seg.json_type
    buf = seg.buf
    if t == "boolean":
        return buf not in ("true", "false")
    if t in ("integer", "number"):
        return buf in ("", "-") or buf.endswith(".")
    if t == "string":
        return len(buf) == 0
    return False


# ---------------------------------------------------------------------------
# The state machine
# ---------------------------------------------------------------------------


@dataclass
class ConstraintMachine:
    """Drives constrained decoding for one prompt.

    Lifecycle:

    1. Construct with the function list and a Vocabulary.
    2. At each step, call :meth:`allowed_token_ids` and mask logits.
    3. After picking a token id, call :meth:`advance`.
    4. Stop when :attr:`finished` is ``True``.
    """

    functions: list[FunctionDefinition]
    vocab: Vocabulary
    segments: list[Segment] = field(default_factory=list)
    cursor: int = 0
    finished: bool = False
    chosen_function: FunctionDefinition | None = None
    _tail_injected: bool = False

    def __post_init__(self) -> None:
        self.segments = build_outer_plan(self.functions)

    # -- snapshot / restore -------------------------------------------------

    def _snapshot(
        self,
    ) -> tuple[
        int,
        list[Segment],
        FunctionDefinition | None,
        bool,
    ]:
        """Capture mutable state so :meth:`_token_matches` can roll back."""
        return (
            self.cursor,
            [s.clone() for s in self.segments],
            self.chosen_function,
            self._tail_injected,
        )

    def _restore(
        self,
        snap: tuple[int, list[Segment], FunctionDefinition | None, bool],
    ) -> None:
        """Restore from :meth:`_snapshot`."""
        (
            self.cursor,
            self.segments,
            self.chosen_function,
            self._tail_injected,
        ) = snap

    # -- public API ---------------------------------------------------------

    def current(self) -> Segment | None:
        """The segment we are currently emitting, or ``None`` when done."""
        if self.cursor >= len(self.segments):
            return None
        return self.segments[self.cursor]

    def allowed_token_ids(self) -> set[int]:
        """Token ids whose surface keeps the machine on a valid path."""
        seg = self.current()
        if seg is None:
            return set()

        allowed: set[int] = set()
        for tid, text in self.vocab.id_to_text.items():
            if not text:
                continue
            if tid in self.vocab.banned_ids:
                continue
            if self._token_matches(text):
                allowed.add(tid)
        return allowed

    def advance(self, token_id: int) -> None:
        """Apply ``token_id`` to the real machine state (no rollback)."""
        text = self.vocab.text_of(token_id)
        if not text:
            return
        for ch in text:
            if not self._try_consume_char(ch):
                # Shouldn't happen if logits were properly masked.
                self.finished = True
                return
        if self.cursor >= len(self.segments):
            self.finished = True

    # -- character-level driver --------------------------------------------

    def _token_matches(self, text: str) -> bool:
        """Would emitting ``text`` keep us on a valid path?

        Simulated against a snapshot of the state; restores on return.
        """
        snap = self._snapshot()
        ok = True
        for ch in text:
            if not self._try_consume_char(ch):
                ok = False
                break
            if self.cursor >= len(self.segments):
                # Reached the end mid-token: any further char is invalid.
                # We accept this token only if it ends exactly here.
                ok = ch == text[-1]
                break
        self._restore(snap)
        return ok

    def _try_consume_char(self, ch: str) -> bool:
        """Consume one character; return ``False`` if it would be invalid.

        Returns:
            ``True`` if ``ch`` was absorbed. May advance ``self.cursor``
            and may inject the parameters tail when the function-name
            enum is locked in.
        """
        seg = self.current()
        if seg is None:
            return False

        if isinstance(seg, LiteralSeg):
            return self._consume_literal(seg, ch)
        if isinstance(seg, EnumSeg):
            return self._consume_enum(seg, ch)
        if isinstance(seg, ValueSeg):
            return self._consume_value(seg, ch)
        return False

    def _consume_literal(self, seg: LiteralSeg, ch: str) -> bool:
        """Match one character against a literal segment."""
        if seg.pos >= len(seg.text):
            return False
        if seg.text[seg.pos] != ch:
            return False
        seg.pos += 1
        if seg.pos == len(seg.text):
            self.cursor += 1
            self._maybe_inject_params_tail(seg)
        return True

    def _consume_enum(self, seg: EnumSeg, ch: str) -> bool:
        """Match one character against an enum segment.

        Lock in the choice only when:

        * ``typed + ch`` exactly matches one choice, AND
        * no other choice extends it further.
        """
        new_typed = seg.typed + ch
        viable = [c for c in seg.choices if c.startswith(new_typed)]
        if not viable:
            return False
        seg.typed = new_typed
        seg.choices = viable

        # Can we lock in now? Only if exactly one choice equals typed
        # AND nothing else extends it.
        exact = [c for c in viable if c == new_typed]
        longer = [c for c in viable if len(c) > len(new_typed)]
        if exact and not longer:
            self._lock_in_function(exact[0])
            self.cursor += 1
        return True

    def _consume_value(self, seg: ValueSeg, ch: str) -> bool:
        """Match one character against a value segment.

        If the value is already complete and ``ch`` does not extend
        it, close the value and forward the character to the next
        segment.
        """
        if seg.done:
            return False
        if _value_can_extend(seg, ch):
            seg.buf += ch
            return True
        if _value_is_complete(seg) and not _value_must_continue(seg):
            seg.done = True
            self.cursor += 1
            return self._try_consume_char(ch)
        return False

    # -- transitions --------------------------------------------------------

    def _maybe_inject_params_tail(self, just_finished: LiteralSeg) -> None:
        """If we just emitted ``", "parameters": {``, append the tail."""
        if self._tail_injected:
            return
        if self.chosen_function is None:
            return
        if just_finished.text != '", "parameters": {':
            return
        tail = build_params_tail(self.chosen_function)
        self.segments.extend(tail)
        self._tail_injected = True

    def _lock_in_function(self, name: str) -> None:
        """Record which function the model picked."""
        for fn in self.functions:
            if fn.name == name:
                self.chosen_function = fn
                return

    # -- diagnostics --------------------------------------------------------

    def rendered(self) -> str:
        """Best-effort reconstruction of the output produced so far.

        Useful for debugging and for the final JSON-parse step.
        """
        out: list[str] = []
        for i, seg in enumerate(self.segments):
            if i > self.cursor:
                break
            if i == self.cursor and not self.finished:
                if isinstance(seg, LiteralSeg):
                    out.append(seg.text[: seg.pos])
                elif isinstance(seg, EnumSeg):
                    out.append(seg.typed)
                else:
                    out.append(seg.buf)
            else:
                if isinstance(seg, LiteralSeg):
                    out.append(seg.text[: seg.pos])
                elif isinstance(seg, EnumSeg):
                    out.append(seg.typed)
                else:
                    out.append(seg.buf)
        return "".join(out)


def iter_allowed(machine: ConstraintMachine) -> Iterable[int]:
    """Convenience wrapper used by tests."""
    return iter(machine.allowed_token_ids())
