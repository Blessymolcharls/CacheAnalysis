"""Random access workload with low spatial locality."""

from __future__ import annotations

import random
from typing import Iterable

from ..models import AccessType, MemoryAccess
from .base import WorkloadGenerator


class RandomWorkload(WorkloadGenerator):
    """Generate pseudo-random accesses over a bounded address range."""

    def __init__(
        self,
        total_accesses: int,
        address_limit_bytes: int,
        seed: int = 7,
    ) -> None:
        if total_accesses <= 0:
            raise ValueError("total_accesses must be positive")
        if address_limit_bytes <= 0:
            raise ValueError("address_limit_bytes must be positive")

        self.total_accesses = total_accesses
        self.address_limit_bytes = address_limit_bytes
        self.seed = seed
        self.name = "random"

    def generate(self) -> Iterable[MemoryAccess]:
        rng = random.Random(self.seed)

        for i in range(self.total_accesses):
            address = rng.randrange(0, self.address_limit_bytes)
            access_type = AccessType.LOAD if rng.random() < 0.65 else AccessType.STORE
            yield MemoryAccess(
                address=address,
                access_type=access_type,
                sequence_id=i,
                workload_name=self.name,
            )
