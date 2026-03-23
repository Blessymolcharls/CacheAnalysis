"""Set-associative cache core implementation with LRU replacement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .addressing import AddressDecoder
from .models import AccessType, CacheCounters, MissType
from .replacement.lru import LRUEvent, SetLRUPool


@dataclass
class CacheLine:
    """Represents one resident cache line."""

    tag: int
    valid: bool = True
    dirty: bool = False
    last_access_id: int = -1


@dataclass
class SetState:
    """Holds cache lines for one set index.

    `lines` stores the currently resident tags mapped to line metadata.
    The LRU ordering is managed externally by `SetLRUPool`.
    """

    lines: Dict[int, CacheLine] = field(default_factory=dict)

    def is_full(self, associativity: int) -> bool:
        return len(self.lines) >= associativity


class CacheCore:
    """A modular set-associative cache with LRU replacement.

    This class handles only cache mechanics and accounting. Miss
    classification policy and workload generation are delegated to other modules.
    """

    def __init__(
        self,
        cache_size_bytes: int,
        block_size_bytes: int,
        associativity: int,
        address_space_bits: int = 32,
    ) -> None:
        if cache_size_bytes <= 0:
            raise ValueError("cache_size_bytes must be positive")
        if block_size_bytes <= 0:
            raise ValueError("block_size_bytes must be positive")
        if associativity <= 0:
            raise ValueError("associativity must be positive")

        if cache_size_bytes % block_size_bytes != 0:
            raise ValueError("cache_size_bytes must be divisible by block_size_bytes")

        self.cache_size_bytes = cache_size_bytes
        self.block_size_bytes = block_size_bytes
        self.associativity = associativity
        self.num_blocks = cache_size_bytes // block_size_bytes

        if self.num_blocks % associativity != 0:
            raise ValueError("num_blocks must be divisible by associativity")

        self.num_sets = self.num_blocks // associativity

        self.decoder = AddressDecoder(
            block_size_bytes=block_size_bytes,
            num_sets=self.num_sets,
            address_space_bits=address_space_bits,
        )

        self.sets: List[SetState] = [SetState() for _ in range(self.num_sets)]
        self.lru_pool = SetLRUPool(num_sets=self.num_sets, associativity=self.associativity)

        self.counters = CacheCounters()

        # Seen blocks are needed for compulsory miss detection.
        self.seen_blocks: Set[int] = set()

        # Recent actions make debugging easier for experiment logs.
        self.event_log: List[str] = []

    def reset(self) -> None:
        self.sets = [SetState() for _ in range(self.num_sets)]
        self.lru_pool.reset()
        self.counters = CacheCounters()
        self.seen_blocks.clear()
        self.event_log.clear()

    def access(
        self,
        address: int,
        access_type: AccessType,
        access_id: int,
    ) -> Tuple[bool, Optional[int], LRUEvent]:
        """Perform one cache access.

        Returns:
            (hit, evicted_tag, lru_event)
        """

        self.counters.record_access(access_type)

        fields = self.decoder.decode(address)
        set_state = self.sets[fields.index]
        tracker = self.lru_pool.tracker(fields.index)

        block_addr = self.decoder.block_address(address)
        is_first_touch = block_addr not in self.seen_blocks

        # Hit path
        if fields.tag in set_state.lines and set_state.lines[fields.tag].valid:
            line = set_state.lines[fields.tag]
            line.last_access_id = access_id
            if access_type == AccessType.STORE:
                line.dirty = True

            lru_event = tracker.touch(fields.tag)
            self.counters.record_hit()
            self.event_log.append(
                f"A#{access_id} HIT set={fields.index} tag={fields.tag}"
            )
            return True, None, lru_event

        # Miss path: choose miss kind later in simulator based on extra context.
        evicted_tag: Optional[int] = None
        if set_state.is_full(self.associativity):
            # Ask LRU tracker which tag should be replaced.
            lru_event = tracker.touch(fields.tag)
            evicted_tag = lru_event.evicted_tag
            if evicted_tag is not None:
                set_state.lines.pop(evicted_tag, None)
        else:
            lru_event = tracker.touch(fields.tag)

        set_state.lines[fields.tag] = CacheLine(
            tag=fields.tag,
            valid=True,
            dirty=(access_type == AccessType.STORE),
            last_access_id=access_id,
        )

        self.seen_blocks.add(block_addr)

        if is_first_touch:
            self.event_log.append(
                f"A#{access_id} MISS first-touch set={fields.index} tag={fields.tag}"
            )
        else:
            self.event_log.append(
                f"A#{access_id} MISS revisit set={fields.index} tag={fields.tag}"
            )

        return False, evicted_tag, lru_event

    def classify_compulsory(self, address: int) -> bool:
        """Check whether block has been seen before this access.

        This method is useful when simulator wants independent classification logic.
        """

        block_addr = self.decoder.block_address(address)
        return block_addr not in self.seen_blocks

    def resident_blocks(self) -> int:
        total = 0
        for set_state in self.sets:
            total += len(set_state.lines)
        return total

    def snapshot_set(self, set_index: int) -> Dict[str, object]:
        if set_index < 0 or set_index >= self.num_sets:
            raise IndexError("set_index out of range")

        set_state = self.sets[set_index]
        tracker = self.lru_pool.tracker(set_index)

        return {
            "set_index": set_index,
            "resident_tags": sorted(list(set_state.lines.keys())),
            "lru_to_mru": tracker.as_list_lru_to_mru(),
            "mru_to_lru": tracker.as_list_mru_to_lru(),
        }

    def recent_events(self, limit: int = 20) -> List[str]:
        if limit <= 0:
            return []
        return list(self.event_log[-limit:])

    def describe(self) -> str:
        return (
            "CacheCore("
            f"cache_size_bytes={self.cache_size_bytes}, "
            f"block_size_bytes={self.block_size_bytes}, "
            f"associativity={self.associativity}, "
            f"num_sets={self.num_sets})"
        )

    def register_miss_type(self, miss_type: MissType) -> None:
        self.counters.record_miss(miss_type)

    def counters_dict(self) -> Dict[str, object]:
        return self.counters.as_dict()
