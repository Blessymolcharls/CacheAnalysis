"""Simulation engine that executes workloads on the cache core."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .cache_core import CacheCore
from .config import CacheGeometry
from .miss_classifier import MissClassifier
from .models import CacheCounters, ExperimentKey, ExperimentResult, MemoryAccess, MissType


@dataclass
class SimulationOptions:
    """Options controlling runtime behavior and diagnostics."""

    collect_notes: bool = True
    event_log_sample: int = 10


class CacheSimulator:
    """Coordinates cache execution and metric collection."""

    def __init__(
        self,
        geometry: CacheGeometry,
        replacement_policy: str = "LRU",
        options: Optional[SimulationOptions] = None,
    ) -> None:
        geometry.validate()
        if replacement_policy.upper() != "LRU":
            raise ValueError("Only LRU replacement policy is supported")

        self.geometry = geometry
        self.replacement_policy = replacement_policy.upper()
        self.options = options or SimulationOptions()

        self.cache = CacheCore(
            cache_size_bytes=geometry.cache_size_bytes,
            block_size_bytes=geometry.block_size_bytes,
            associativity=geometry.associativity,
            address_space_bits=geometry.address_space_bits,
        )
        self.classifier = MissClassifier(cache_num_blocks=geometry.num_blocks)

    def run(
        self,
        accesses: Iterable[MemoryAccess],
        workload_name: str,
    ) -> ExperimentResult:
        self.cache.reset()
        self.classifier.reset()

        start = time.perf_counter()

        for access in accesses:
            self._process_access(access)

        runtime = time.perf_counter() - start
        counters = self.cache.counters
        counters.validate()

        key = ExperimentKey(
            cache_size_kb=self.geometry.cache_size_kb,
            block_size_kb=self.geometry.block_size_kb,
            associativity=self.geometry.associativity,
            replacement_policy=self.replacement_policy,
            workload_name=workload_name,
        )

        notes: List[str] = []
        if self.options.collect_notes:
            notes.extend(self._build_notes(counters))

        return ExperimentResult(
            key=key,
            counters=counters,
            runtime_seconds=runtime,
            notes=notes,
        )

    def _process_access(self, access: MemoryAccess) -> None:
        # Determine compulsory status before cache mutates seen block set.
        is_compulsory = self.cache.classify_compulsory(access.address)

        hit, _evicted, _lru_event = self.cache.access(
            address=access.address,
            access_type=access.access_type,
            access_id=access.sequence_id,
        )

        block_addr = self.cache.decoder.block_address(access.address)

        if hit:
            self.classifier.observe_hit(block_addr)
            return

        if is_compulsory:
            miss_type = self.classifier.classify(block_addr)
            if miss_type != MissType.COMPULSORY:
                # Ensure exact compulsory labeling on first touch.
                miss_type = MissType.COMPULSORY
        else:
            miss_type = self.classifier.classify(block_addr)
            if miss_type == MissType.COMPULSORY:
                # Defensive fallback in case history was externally reset.
                miss_type = MissType.CONFLICT

        self.cache.register_miss_type(miss_type)

    def _build_notes(self, counters: CacheCounters) -> List[str]:
        notes: List[str] = []

        notes.append(
            f"Validated rates: hit+miss={counters.hit_rate + counters.miss_rate:.6f}"
        )
        notes.append(
            "Miss breakdown (C/C/Cp): "
            f"{counters.compulsory_misses}/{counters.conflict_misses}/{counters.capacity_misses}"
        )

        if counters.total_accesses > 0:
            notes.append(
                f"Load/store split: {counters.load_accesses}/{counters.store_accesses}"
            )

        event_tail = self.cache.recent_events(limit=self.options.event_log_sample)
        if event_tail:
            notes.append("Recent cache events:")
            notes.extend(event_tail)

        return notes
