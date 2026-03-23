"""Core domain models for access traces, stats, and experiment records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List


class AccessType(str, Enum):
    """Type of memory operation."""

    LOAD = "load"
    STORE = "store"


class MissType(str, Enum):
    """Classification of cache misses.

    Compulsory: The block has never been seen before.
    Conflict: The block is evicted due to limited associativity while total
        working set can still fit cache capacity in principle.
    Capacity: The working set effectively exceeds cache capacity.
    """

    COMPULSORY = "compulsory"
    CONFLICT = "conflict"
    CAPACITY = "capacity"


@dataclass(frozen=True)
class MemoryAccess:
    """One memory access entry in a synthetic workload."""

    address: int
    access_type: AccessType
    sequence_id: int
    workload_name: str


@dataclass
class CacheCounters:
    """Counters for cache performance metrics and invariants."""

    total_accesses: int = 0
    hits: int = 0
    misses: int = 0

    compulsory_misses: int = 0
    conflict_misses: int = 0
    capacity_misses: int = 0

    load_accesses: int = 0
    store_accesses: int = 0

    def record_access(self, access_type: AccessType) -> None:
        self.total_accesses += 1
        if access_type == AccessType.LOAD:
            self.load_accesses += 1
        elif access_type == AccessType.STORE:
            self.store_accesses += 1

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self, miss_type: MissType) -> None:
        self.misses += 1
        if miss_type == MissType.COMPULSORY:
            self.compulsory_misses += 1
        elif miss_type == MissType.CONFLICT:
            self.conflict_misses += 1
        elif miss_type == MissType.CAPACITY:
            self.capacity_misses += 1

    @property
    def hit_rate(self) -> float:
        if self.total_accesses == 0:
            return 0.0
        return self.hits / self.total_accesses

    @property
    def miss_rate(self) -> float:
        if self.total_accesses == 0:
            return 0.0
        return self.misses / self.total_accesses

    def validate(self) -> None:
        if self.total_accesses != self.hits + self.misses:
            raise ValueError(
                "Invariant violation: total_accesses != hits + misses"
            )

        if abs((self.hit_rate + self.miss_rate) - 1.0) > 1e-9 and self.total_accesses > 0:
            raise ValueError(
                "Invariant violation: hit_rate + miss_rate must equal 1"
            )

        if self.misses != (
            self.compulsory_misses + self.conflict_misses + self.capacity_misses
        ):
            raise ValueError(
                "Invariant violation: misses != compulsory + conflict + capacity"
            )

    def as_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "total_accesses": self.total_accesses,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "compulsory_misses": self.compulsory_misses,
            "conflict_misses": self.conflict_misses,
            "capacity_misses": self.capacity_misses,
            "load_accesses": self.load_accesses,
            "store_accesses": self.store_accesses,
        }


@dataclass(frozen=True)
class ExperimentKey:
    """Unique key for one experiment condition and workload."""

    cache_size_kb: int
    block_size_kb: int
    associativity: int
    replacement_policy: str
    workload_name: str


@dataclass
class ExperimentResult:
    """Result record for a single experiment run."""

    key: ExperimentKey
    counters: CacheCounters

    runtime_seconds: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "cache_size_kb": self.key.cache_size_kb,
            "block_size_kb": self.key.block_size_kb,
            "associativity": self.key.associativity,
            "replacement_policy": self.key.replacement_policy,
            "workload_name": self.key.workload_name,
            "runtime_seconds": self.runtime_seconds,
            "notes": list(self.notes),
        }
        data.update(self.counters.as_dict())
        return data


@dataclass
class ExperimentBatch:
    """Container for all experiment outputs."""

    config_snapshot: Dict[str, Any]
    results: List[ExperimentResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config_snapshot,
            "results": [result.to_dict() for result in self.results],
        }

    def to_rows(self) -> List[Dict[str, Any]]:
        return [result.to_dict() for result in self.results]


def dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Safe dataclass serialization helper.

    This wrapper exists so callers can convert nested dataclasses in one place
    without importing `asdict` from `dataclasses` in every module.
    """

    return asdict(instance)
