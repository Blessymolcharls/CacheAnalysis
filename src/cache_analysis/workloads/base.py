"""Base workload generator abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List

from ..models import MemoryAccess


class WorkloadGenerator(ABC):
    """Abstract base class for synthetic workload generation."""

    name: str

    @abstractmethod
    def generate(self) -> Iterable[MemoryAccess]:
        """Yield memory accesses for this workload."""

    def materialize(self) -> List[MemoryAccess]:
        """Build full in-memory list, useful for small traces or debugging."""

        return list(self.generate())

    def iter_chunked(self, chunk_size: int) -> Iterator[List[MemoryAccess]]:
        """Yield accesses in chunks to reduce peak memory usage."""

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        chunk: List[MemoryAccess] = []
        for item in self.generate():
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
