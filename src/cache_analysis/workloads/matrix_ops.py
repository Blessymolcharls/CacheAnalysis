"""Matrix-operation-style workload.

This trace approximates accesses from naive matrix multiplication and sum-reduce
operations. It combines row-major and column-like traversal patterns to trigger
mixed locality behaviors and conflict pressure.
"""

from __future__ import annotations

from typing import Iterable, Iterator, Tuple

from ..models import AccessType, MemoryAccess
from .base import WorkloadGenerator


class MatrixWorkload(WorkloadGenerator):
    """Matrix operation access generator.

    The generated stream models C = A x B with naive loop ordering and then
    a post-pass over C, producing both regular and strided patterns.
    """

    def __init__(
        self,
        dimension: int,
        element_size_bytes: int = 8,
        base_a: int = 0,
        base_b: int = 256 * 1024 * 1024,
        base_c: int = 512 * 1024 * 1024,
    ) -> None:
        if dimension <= 1:
            raise ValueError("dimension must be > 1")
        if element_size_bytes <= 0:
            raise ValueError("element_size_bytes must be positive")

        self.dimension = dimension
        self.element_size_bytes = element_size_bytes
        self.base_a = base_a
        self.base_b = base_b
        self.base_c = base_c
        self.name = "matrix"

    def generate(self) -> Iterable[MemoryAccess]:
        sequence_id = 0
        for op_addr, op_type in self._matmul_accesses():
            yield MemoryAccess(
                address=op_addr,
                access_type=op_type,
                sequence_id=sequence_id,
                workload_name=self.name,
            )
            sequence_id += 1

        for i in range(self.dimension):
            for j in range(self.dimension):
                addr_c = self._elem_addr(self.base_c, i, j)
                yield MemoryAccess(
                    address=addr_c,
                    access_type=AccessType.LOAD,
                    sequence_id=sequence_id,
                    workload_name=self.name,
                )
                sequence_id += 1

    def _matmul_accesses(self) -> Iterator[Tuple[int, AccessType]]:
        n = self.dimension

        for i in range(n):
            for j in range(n):
                # Write initialize C[i][j]
                addr_c = self._elem_addr(self.base_c, i, j)
                yield addr_c, AccessType.STORE

                # Inner product accesses A row and B column.
                for k in range(n):
                    addr_a = self._elem_addr(self.base_a, i, k)
                    addr_b = self._elem_addr(self.base_b, k, j)
                    yield addr_a, AccessType.LOAD
                    yield addr_b, AccessType.LOAD
                    yield addr_c, AccessType.STORE

    def _elem_addr(self, base: int, row: int, col: int) -> int:
        offset = (row * self.dimension + col) * self.element_size_bytes
        return base + offset
