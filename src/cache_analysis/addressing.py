"""Address decomposition helpers for cache mapping.

The cache simulator splits each address into:
- offset bits based on block size
- index bits based on number of sets
- remaining tag bits
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AddressFields:
    """Decoded fields of an address for cache lookup."""

    tag: int
    index: int
    offset: int


class AddressDecoder:
    """Utility class that performs tag/index/offset extraction.

    The decoder is immutable and specific to a cache geometry.
    """

    def __init__(
        self,
        block_size_bytes: int,
        num_sets: int,
        address_space_bits: int = 32,
    ) -> None:
        if block_size_bytes <= 0:
            raise ValueError("block_size_bytes must be positive")
        if num_sets <= 0:
            raise ValueError("num_sets must be positive")
        if address_space_bits <= 0:
            raise ValueError("address_space_bits must be positive")

        self.block_size_bytes = block_size_bytes
        self.num_sets = num_sets
        self.address_space_bits = address_space_bits

        self.offset_bits = _log2_exact(block_size_bytes)
        self.index_bits = _log2_exact(num_sets)
        self.tag_bits = address_space_bits - (self.index_bits + self.offset_bits)

        if self.tag_bits <= 0:
            raise ValueError(
                "Address field split invalid; tag_bits must remain positive"
            )

        self.offset_mask = (1 << self.offset_bits) - 1
        self.index_mask = (1 << self.index_bits) - 1

    def decode(self, address: int) -> AddressFields:
        if address < 0:
            raise ValueError("address must be non-negative")

        offset = address & self.offset_mask
        index = (address >> self.offset_bits) & self.index_mask
        tag = address >> (self.offset_bits + self.index_bits)

        return AddressFields(tag=tag, index=index, offset=offset)

    def block_address(self, address: int) -> int:
        """Return address aligned to block boundary."""

        return address >> self.offset_bits

    def cache_line_identity(self, address: int) -> Tuple[int, int]:
        """Return (index, tag) tuple used by set-associative cache."""

        fields = self.decode(address)
        return fields.index, fields.tag

    def human_summary(self) -> str:
        return (
            f"AddressDecoder(block_size={self.block_size_bytes}, sets={self.num_sets}, "
            f"offset_bits={self.offset_bits}, index_bits={self.index_bits}, tag_bits={self.tag_bits})"
        )


def _log2_exact(value: int) -> int:
    """Return log2(value) when value is a power of two.

    Cache indexing logic relies on exact binary partitioning. This helper keeps
    invalid geometry from silently producing wrong field extraction.
    """

    if value <= 0:
        raise ValueError("value must be positive")
    if value & (value - 1) != 0:
        raise ValueError(f"value must be power of two, got {value}")
    return value.bit_length() - 1
