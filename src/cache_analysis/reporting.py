"""Result export and textual reporting helpers."""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from typing import Dict, Iterable, List

from .models import ExperimentBatch, ExperimentResult


class ResultWriter:
    """Write experiment outputs to CSV, JSON, and summary text."""

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_csv(self, file_name: str, results: Iterable[ExperimentResult]) -> str:
        rows = [r.to_dict() for r in results]
        path = os.path.join(self.output_dir, file_name)

        if not rows:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("")
            return path

        fieldnames = sorted(rows[0].keys())
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return path

    def write_json(self, file_name: str, batch: ExperimentBatch) -> str:
        path = os.path.join(self.output_dir, file_name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(batch.to_dict(), handle, indent=2)
        return path

    def write_summary(self, file_name: str, results: Iterable[ExperimentResult]) -> str:
        path = os.path.join(self.output_dir, file_name)
        text = build_summary_text(list(results))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


def build_summary_text(results: List[ExperimentResult]) -> str:
    """Build human-readable report with key trends and spot checks."""

    lines: List[str] = []
    lines.append("Cache Simulation Summary")
    lines.append("=" * 80)
    lines.append("")

    if not results:
        lines.append("No results available.")
        return "\n".join(lines)

    by_workload: Dict[str, List[ExperimentResult]] = defaultdict(list)
    for result in results:
        by_workload[result.key.workload_name].append(result)

    for workload, group in sorted(by_workload.items()):
        lines.append(f"Workload: {workload}")
        lines.append("-" * 80)

        # Sort by block then associativity for stable comparisons.
        group = sorted(group, key=lambda r: (r.key.block_size_kb, r.key.associativity))

        for result in group:
            lines.append(
                " | ".join(
                    [
                        f"Block={result.key.block_size_kb}KB",
                        f"Assoc={result.key.associativity}-way",
                        f"Accesses={result.counters.total_accesses}",
                        f"Hits={result.counters.hits}",
                        f"Misses={result.counters.misses}",
                        f"HitRate={result.counters.hit_rate:.6f}",
                        f"MissRate={result.counters.miss_rate:.6f}",
                    ]
                )
            )

        lines.append("")

    lines.append("Key Insight Targets")
    lines.append("-" * 80)
    lines.append("1. Hit rate often increases with block size initially, then may saturate.")
    lines.append("2. Miss rate often decreases initially, but may rise if conflicts dominate.")
    lines.append("3. Associativity tends to show diminishing returns beyond 4-way.")

    return "\n".join(lines)
