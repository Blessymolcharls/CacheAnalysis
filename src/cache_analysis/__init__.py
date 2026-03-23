"""Cache analysis framework package.

This package provides a modular cache simulation and analysis toolkit inspired by
architectural simulation workflows used with gem5.
"""

from .config import (
    DEFAULT_ASSOCIATIVITIES,
    DEFAULT_BLOCK_SIZES_KB,
    DEFAULT_CACHE_SIZE_KB,
    ExperimentConfig,
)
from .experiments import ExperimentRunner
from .simulator import CacheSimulator

__all__ = [
    "DEFAULT_ASSOCIATIVITIES",
    "DEFAULT_BLOCK_SIZES_KB",
    "DEFAULT_CACHE_SIZE_KB",
    "ExperimentConfig",
    "ExperimentRunner",
    "CacheSimulator",
]
