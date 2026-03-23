"""Sequential locality-heavy workload."""

from __future__ import annotations

from typing import Iterable

from ..models import AccessType, MemoryAccess
from .base import WorkloadGenerator


class SequentialWorkload(WorkloadGenerator):
    """Generate mostly linear accesses to exploit spatial locality.

    The trace alternates load and store operations to exercise both access types.
    """

    def __init__(
        self,
        total_accesses: int,
        stride_bytes: int,
        address_limit_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        if total_accesses <= 0:
            raise ValueError("total_accesses must be positive")
        if stride_bytes <= 0:
            raise ValueError("stride_bytes must be positive")
        if address_limit_bytes <= 0:
            raise ValueError("address_limit_bytes must be positive")

        self.total_accesses = total_accesses
        self.stride_bytes = stride_bytes
        self.address_limit_bytes = address_limit_bytes
        self.name = "sequential"

    def generate(self) -> Iterable[MemoryAccess]:
        address = 0
        for i in range(self.total_accesses):
            access_type = AccessType.LOAD if i % 2 == 0 else AccessType.STORE
            yield MemoryAccess(
                address=address,
                access_type=access_type,
                sequence_id=i,
                workload_name=self.name,
            )

            address += self.stride_bytes
            if address >= self.address_limit_bytes:
                address = 0
