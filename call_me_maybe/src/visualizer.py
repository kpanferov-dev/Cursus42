"""Token-by-token visualization of the generation process (bonus).

Activated with ``--visualize`` on the command line. For each step we
print:

* The token being emitted (with non-printables escaped).
* The current segment kind (Literal / Enum / Value).
* How many tokens the constraint mask allowed at this step.
* The top-3 tokens by unmasked logit, and which ones survived
  masking. This makes it visible *why* the model didn't go off the
  rails: the bad tokens still had high logits, but they were masked
  to ``-inf``.

This is purely diagnostic; the visualizer never changes generation
behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .vocabulary import Vocabulary


@dataclass
class StepTrace:
    """One step of the generation, captured for display."""

    step: int
    segment_kind: str
    n_allowed: int
    chosen_id: int
    chosen_text: str
    top_unmasked: list[tuple[int, str, float]]
    top_masked: list[tuple[int, str, float]]


def _escape(text: str) -> str:
    """Make whitespace and control chars visible."""
    out: list[str] = []
    for ch in text:
        if ch == " ":
            out.append("·")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return "".join(out)


def make_trace(
    step: int,
    segment_kind: str,
    raw_logits: np.ndarray,
    masked_logits: np.ndarray,
    allowed: set[int],
    chosen_id: int,
    vocab: Vocabulary,
    k: int = 3,
) -> StepTrace:
    """Capture the data needed to display one step."""
    top_unmasked_idx = np.argsort(raw_logits)[-k:][::-1]
    top_masked_idx = np.argsort(masked_logits)[-k:][::-1]

    top_unmasked = [
        (int(i), _escape(vocab.text_of(int(i))), float(raw_logits[i]))
        for i in top_unmasked_idx
    ]
    top_masked = [
        (int(i), _escape(vocab.text_of(int(i))), float(masked_logits[i]))
        for i in top_masked_idx
        if not np.isneginf(masked_logits[int(i)])
    ]

    return StepTrace(
        step=step,
        segment_kind=segment_kind,
        n_allowed=len(allowed),
        chosen_id=chosen_id,
        chosen_text=_escape(vocab.text_of(chosen_id)),
        top_unmasked=top_unmasked,
        top_masked=top_masked,
    )


def print_trace(trace: Sequence[StepTrace], prompt: str) -> None:
    """Pretty-print a sequence of step traces to stdout."""
    bar = "-" * 78
    print(bar)
    print(f"Trace for prompt: {prompt!r}")
    print(bar)
    header = (
        f"{'step':>4} {'kind':<8} "
        f"{'#allow':>7}  token  "
        "(top unmasked vs allowed)"
    )

    print(header)
    print(bar)
    for t in trace:
        unmasked_str = ", ".join(
            f"{tok}({score:.1f})" for _, tok, score in t.top_unmasked
        )
        masked_str = ", ".join(
            f"{tok}({score:.1f})" for _, tok, score in t.top_masked
        )
        print(
            f"{t.step:>4} {t.segment_kind:<8} {t.n_allowed:>7}  "
            f"-> '{t.chosen_text}'\n"
            f"      raw top: {unmasked_str}\n"
            f"      allowed: {masked_str}"
        )
    print(bar)
