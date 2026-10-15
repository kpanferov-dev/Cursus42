"""API-key rotation.

Keys are used round-robin *on failure*: the current key stays active until
it is rate limited / exhausted / rejected, then the ring moves to the next
key that is not cooling down. Invalid keys (401/403) are disabled for the
rest of the run.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class _KeyState:
    key: str
    cooldown_until: float = 0.0
    disabled: bool = False
    failures: int = 0


class KeyRing:
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("KeyRing needs at least one key")
        self._keys = [_KeyState(k) for k in keys]
        self._idx = 0

    def __len__(self) -> int:
        return len(self._keys)

    @property
    def usable(self) -> int:
        return sum(1 for k in self._keys if not k.disabled)

    def current(self) -> str:
        return self._keys[self._idx].key

    def label(self) -> str:
        """Non-secret identifier of the current key, for logs."""
        return f"key#{self._idx + 1}/{len(self._keys)}"

    def disable_current(self) -> None:
        self._keys[self._idx].disabled = True
        self.rotate()

    def cool_down_current(self, seconds: float) -> None:
        st = self._keys[self._idx]
        st.failures += 1
        st.cooldown_until = time.monotonic() + max(seconds, 1.0)
        self.rotate()

    def rotate(self) -> None:
        """Move to the next enabled key, preferring one that is not cooling down."""
        n = len(self._keys)
        now = time.monotonic()
        for step in range(1, n + 1):
            cand = (self._idx + step) % n
            st = self._keys[cand]
            if not st.disabled and st.cooldown_until <= now:
                self._idx = cand
                return
        for step in range(1, n + 1):  # everyone cooling down: pick the soonest
            cand = (self._idx + step) % n
            if not self._keys[cand].disabled:
                best = min(
                    (i for i, s in enumerate(self._keys) if not s.disabled),
                    key=lambda i: self._keys[i].cooldown_until,
                )
                self._idx = best
                return

    def wait_time(self) -> float:
        """Seconds until the current key is usable again (0 if ready)."""
        return max(0.0, self._keys[self._idx].cooldown_until - time.monotonic())

    def all_disabled(self) -> bool:
        return self.usable == 0

    def next_ready_in(self) -> Optional[float]:
        now = time.monotonic()
        waits = [max(0.0, s.cooldown_until - now) for s in self._keys if not s.disabled]
        return min(waits) if waits else None
