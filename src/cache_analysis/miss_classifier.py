"""Miss classification helpers for compulsory/conflict/capacity attribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from .models import MissType


@dataclass
class MissClassifierState:
    """Tracks history needed for miss categorization heuristics.

    Notes:
    - Compulsory misses are exact: first time block observed.
    - Conflict vs capacity in practical simulators can be estimated by comparing
      against a fully-associative cache of equal capacity. This implementation
      uses a compact approximation based on unique working set tracking and
      current cache residency pressure.
    """

    cache_num_blocks: int

    seen_blocks: Set[int]
    active_window_blocks: Set[int]


class MissClassifier:
    """Classify misses into compulsory, conflict, and capacity.

    The classification logic is educational and deterministic. For each miss:
    1. If block not previously seen => compulsory.
    2. Else if active working set exceeds cache block capacity => capacity.
    3. Else => conflict.

    The working set proxy uses an adaptive active window set that records blocks
    touched in the current phase and shrinks periodically.
    """

    def __init__(self, cache_num_blocks: int) -> None:
        if cache_num_blocks <= 0:
            raise ValueError("cache_num_blocks must be positive")

        self.state = MissClassifierState(
            cache_num_blocks=cache_num_blocks,
            seen_blocks=set(),
            active_window_blocks=set(),
        )

        self._phase_counter = 0
        self._phase_reset_period = max(512, cache_num_blocks * 8)

    def classify(self, block_addr: int) -> MissType:
        if block_addr not in self.state.seen_blocks:
            self.state.seen_blocks.add(block_addr)
            self.state.active_window_blocks.add(block_addr)
            self._advance_phase()
            return MissType.COMPULSORY

        self.state.active_window_blocks.add(block_addr)
        self._advance_phase()

        if len(self.state.active_window_blocks) > self.state.cache_num_blocks:
            return MissType.CAPACITY

        return MissType.CONFLICT

    def observe_hit(self, block_addr: int) -> None:
        """Update phase tracker on hit to keep working-set estimate realistic."""

        self.state.active_window_blocks.add(block_addr)
        self._advance_phase()

    def _advance_phase(self) -> None:
        self._phase_counter += 1
        if self._phase_counter >= self._phase_reset_period:
            # Keep only a lightweight tail of active set to represent locality.
            # We intentionally keep half of cache capacity worth of blocks.
            self._shrink_active_set(max_keep=max(1, self.state.cache_num_blocks // 2))
            self._phase_counter = 0

    def _shrink_active_set(self, max_keep: int) -> None:
        if len(self.state.active_window_blocks) <= max_keep:
            return

        # Deterministic shrink for reproducible runs.
        sorted_blocks = sorted(self.state.active_window_blocks)
        tail = sorted_blocks[-max_keep:]
        self.state.active_window_blocks = set(tail)

    def reset(self) -> None:
        self.state.seen_blocks.clear()
        self.state.active_window_blocks.clear()
        self._phase_counter = 0

    def debug_state(self) -> str:
        return (
            f"MissClassifier(seen={len(self.state.seen_blocks)}, "
            f"active={len(self.state.active_window_blocks)}, "
            f"capacity={self.state.cache_num_blocks})"
        )
