"""Command-line interface for cache simulation framework."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import List

from .config import (
    DEFAULT_ASSOCIATIVITIES,
    DEFAULT_BLOCK_SIZES_KB,
    DEFAULT_CACHE_SIZE_KB,
    ExperimentConfig,
    OutputConfig,
    WorkloadConfig,
)
from .experiments import ExperimentRunner, print_experiment_examples
from .logging_config import configure_logging, get_logger


def _int_list(values: List[str]) -> List[int]:
    result: List[int] = []
    for value in values:
        result.append(int(value))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cache-analysis",
        description=(
            "Comprehensive cache simulation and analysis framework for studying "
            "block size and associativity impacts using LRU replacement."
        ),
    )

    parser.add_argument("--cache-size-kb", type=int, default=DEFAULT_CACHE_SIZE_KB)
    parser.add_argument(
        "--block-sizes-kb",
        nargs="+",
        type=int,
        default=DEFAULT_BLOCK_SIZES_KB,
        help="Space-separated list, e.g. --block-sizes-kb 16 32 64 128 256",
    )
    parser.add_argument(
        "--associativities",
        nargs="+",
        type=int,
        default=DEFAULT_ASSOCIATIVITIES,
        help="Space-separated list, e.g. --associativities 1 2 4 8",
    )

    parser.add_argument("--replacement-policy", default="LRU")
    parser.add_argument("--address-bits", type=int, default=32)

    parser.add_argument("--seq-accesses", type=int, default=100_000)
    parser.add_argument("--seq-stride", type=int, default=64)

    parser.add_argument("--rand-accesses", type=int, default=100_000)
    parser.add_argument("--rand-limit", type=int, default=32 * 1024 * 1024)
    parser.add_argument("--rand-seed", type=int, default=7)

    parser.add_argument("--matrix-dim", type=int, default=64)
    parser.add_argument("--matrix-elem-size", type=int, default=8)

    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--csv-name", default="cache_results.csv")
    parser.add_argument("--json-name", default="cache_results.json")
    parser.add_argument("--summary-name", default="summary.txt")

    parser.add_argument("--plot-hit-block", default="plot_block_vs_hit_rate.png")
    parser.add_argument("--plot-miss-block", default="plot_block_vs_miss_rate.png")
    parser.add_argument("--plot-hit-assoc", default="plot_assoc_vs_hit_rate.png")
    parser.add_argument("--plot-miss-assoc", default="plot_assoc_vs_miss_rate.png")

    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=None)

    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved configuration as JSON before run",
    )
    parser.add_argument(
        "--print-examples",
        action="store_true",
        help="Print a small sample of per-experiment output blocks",
    )

    return parser


def parse_config(argv: List[str] | None = None) -> ExperimentConfig:
    parser = build_parser()
    args = parser.parse_args(argv)

    workloads = WorkloadConfig(
        sequential_accesses=args.seq_accesses,
        sequential_stride=args.seq_stride,
        random_accesses=args.rand_accesses,
        random_address_limit_bytes=args.rand_limit,
        random_seed=args.rand_seed,
        matrix_dimension=args.matrix_dim,
        matrix_element_size_bytes=args.matrix_elem_size,
    )

    output = OutputConfig(
        output_dir=args.output_dir,
        csv_name=args.csv_name,
        json_name=args.json_name,
        summary_name=args.summary_name,
        plot_hit_vs_block=args.plot_hit_block,
        plot_miss_vs_block=args.plot_miss_block,
        plot_hit_vs_assoc=args.plot_hit_assoc,
        plot_miss_vs_assoc=args.plot_miss_assoc,
    )

    config = ExperimentConfig(
        cache_size_kb=args.cache_size_kb,
        block_sizes_kb=list(args.block_sizes_kb),
        associativities=list(args.associativities),
        replacement_policy=args.replacement_policy,
        address_space_bits=args.address_bits,
        workloads=workloads,
        output=output,
    )
    config.validate()

    configure_logging(level=args.log_level, log_file=args.log_file)
    logger = get_logger("cache-analysis")

    if args.print_config:
        print(json.dumps(asdict(config), indent=2))

    batch, outputs = ExperimentRunner(config).run_and_export()

    logger.info("Artifacts generated:")
    for key, path in outputs.items():
        logger.info("  %s: %s", key, path)

    if args.print_examples:
        print(print_experiment_examples(batch.results, limit=6))

    return config


def main(argv: List[str] | None = None) -> int:
    parse_config(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
