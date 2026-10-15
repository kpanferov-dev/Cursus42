"""Conversation memory with budget-aware rendering.

Token limits are *cumulative* over the whole task, and every request re-sends
the history, so the history must stay small. ``render()`` builds the message
list under a token budget by progressively:

  1. keeping the ``keep_full`` most recent steps verbatim,
  2. condensing older steps (clipped thought/code, clipped observation),
  3. dropping the oldest condensed steps (replaced by a one-line marker).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from smith.llm.base import Message


@dataclass
class Turn:
    assistant: str
    observation: str


def clip(text: str, limit: int, marker: str = "…[clipped]") -> str:
    return text if len(text) <= limit else text[:limit] + marker


class TokenEstimator:
    """chars -> tokens, calibrated on the provider's real usage numbers."""

    def __init__(self, chars_per_token: float = 3.2, safety: float = 1.1):
        self.cpt = chars_per_token
        self.safety = safety

    def estimate(self, messages: List[Message]) -> int:
        chars = sum(len(m["content"]) + 16 for m in messages)
        return int(chars / self.cpt * self.safety) + 8

    def calibrate(self, messages: List[Message], real_tokens: int) -> None:
        if real_tokens <= 0:
            return
        chars = sum(len(m["content"]) + 16 for m in messages)
        observed = chars / real_tokens
        # keep the estimate conservative (never assume more chars/token than observed)
        self.cpt = max(2.0, min(self.cpt if self.cpt < observed else observed, 4.5))


class Memory:
    def __init__(self, system_prompt: str, task_prompt: str, keep_full: int = 3,
                 old_assistant_chars: int = 900, old_obs_chars: int = 300):
        self.system_prompt = system_prompt
        self.task_prompt = task_prompt
        self.turns: List[Turn] = []
        self.keep_full = keep_full
        self.old_assistant_chars = old_assistant_chars
        self.old_obs_chars = old_obs_chars

    def add(self, assistant: str, observation: str) -> None:
        self.turns.append(Turn(assistant, observation))

    def _messages(self, keep_full: int, drop: int, footer: str) -> List[Message]:
        msgs: List[Message] = [{"role": "system", "content": self.system_prompt},
                               {"role": "user", "content": self.task_prompt}]
        n = len(self.turns)
        if drop:
            msgs.append({"role": "user", "content": f"[{drop} earlier step(s) omitted to save tokens]"})
        for i, t in enumerate(self.turns):
            if i < drop:
                continue
            recent = i >= n - keep_full
            a = t.assistant if recent else clip(t.assistant, self.old_assistant_chars)
            o = t.observation if recent else clip(
                t.observation, self.old_obs_chars, "…[old observation clipped]")
            msgs.append({"role": "assistant", "content": a or "(empty response)"})
            msgs.append({"role": "user", "content": "Observation:\n" + o})
        if footer:
            last = msgs[-1]
            msgs[-1] = {"role": last["role"], "content": last["content"] + "\n\n" + footer}
        return msgs

    def render(self, budget_tokens: int, estimator: TokenEstimator, footer: str = "") -> Optional[List[Message]]:
        """Best message list fitting ``budget_tokens`` (None if even the minimum does not fit)."""
        n = len(self.turns)
        for keep in range(min(self.keep_full, n), 0, -1):
            msgs = self._messages(keep, 0, footer)
            if estimator.estimate(msgs) <= budget_tokens:
                return msgs
        keep = 1 if n else 0
        for drop in range(0, max(0, n - keep) + 1):
            msgs = self._messages(keep, drop, footer)
            if estimator.estimate(msgs) <= budget_tokens:
                return msgs
        return None
