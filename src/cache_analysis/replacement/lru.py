"""LRU replacement policy implementation.

This module tracks recency ordering of tags inside a single cache set.
The structure is intentionally simple and deterministic for educational use.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class LRUEvent:
    """Debug record emitted by LRU operations."""

    operation: str
    tag: int
    evicted_tag: Optional[int]


class LRUTracker:
    """Per-set LRU tracker.

    Internally uses OrderedDict where insertion order is recency order:
    - leftmost: least recently used
    - rightmost: most recently used
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._order: OrderedDict[int, None] = OrderedDict()
        self._events: List[LRUEvent] = []

    def contains(self, tag: int) -> bool:
        return tag in self._order

    def touch(self, tag: int) -> LRUEvent:
        """Mark tag as most recently used.

        If absent and capacity is full, evict least recently used tag.
        Returns the operation metadata for external logging.
        """

        if tag in self._order:
            self._order.move_to_end(tag)
            event = LRUEvent(operation="hit-touch", tag=tag, evicted_tag=None)
            self._events.append(event)
            return event

        evicted: Optional[int] = None
        if len(self._order) >= self.capacity:
            evicted, _ = self._order.popitem(last=False)

        self._order[tag] = None
        event = LRUEvent(operation="miss-insert", tag=tag, evicted_tag=evicted)
        self._events.append(event)
        return event

    def remove(self, tag: int) -> None:
        self._order.pop(tag, None)

    def reset(self) -> None:
        self._order.clear()
        self._events.clear()

    def as_list_lru_to_mru(self) -> List[int]:
        return list(self._order.keys())

    def as_list_mru_to_lru(self) -> List[int]:
        values = list(self._order.keys())
        values.reverse()
        return values

    def recent_events(self, limit: int = 10) -> List[LRUEvent]:
        if limit <= 0:
            return []
        return list(self._events[-limit:])

    def __len__(self) -> int:
        return len(self._order)


class SetLRUPool:
    """Collection of LRU trackers, one per cache set."""

    def __init__(self, num_sets: int, associativity: int) -> None:
        if num_sets <= 0:
            raise ValueError("num_sets must be positive")
        if associativity <= 0:
            raise ValueError("associativity must be positive")

        self._trackers: Dict[int, LRUTracker] = {
            set_id: LRUTracker(capacity=associativity) for set_id in range(num_sets)
        }

    def tracker(self, set_index: int) -> LRUTracker:
        try:
            return self._trackers[set_index]
        except KeyError as exc:
            raise IndexError(f"Invalid set index {set_index}") from exc

    def reset(self) -> None:
        for tracker in self._trackers.values():
            tracker.reset()

    def iter_states(self) -> Iterable[Tuple[int, List[int]]]:
        for index, tracker in self._trackers.items():
            yield index, tracker.as_list_lru_to_mru()
