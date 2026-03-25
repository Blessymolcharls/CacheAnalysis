# CacheAnalysis: gem5 Cache-Geometry Experimental Study

## Project Overview

This repository automates a gem5-based cache experiment that sweeps L1 D-cache geometry and compares behavior across multiple workloads.

### Study objective (as implemented)

The implemented objective is to measure how **L1 data-cache block size** and **associativity** affect:

- cache hits and misses
- hit/miss rates
- workload-dependent sensitivity to cache geometry

The code does **not** implement a single-cycle vs pipelined CPU comparison workflow. Instead, it runs cache-geometry sweeps through gem5 and reports cache-level outcomes.

### Simulation environment and tools

- Simulator backend: gem5 in SE mode via [scripts/gem5_cache_sweep.py](scripts/gem5_cache_sweep.py)
- Python orchestration package: [src/cache_analysis](src/cache_analysis)
- Entry point: [main.py](main.py) -> [src/cache_analysis/cli.py](src/cache_analysis/cli.py)
- Batch launcher for five workloads: [run_all.sh](run_all.sh)
- Plotting/data stack: `matplotlib`, `numpy`, `pandas` (from [requirements.txt](requirements.txt))
- C benchmarks and build rules: [benchmarks](benchmarks)

## Pipeline Workflow

This section describes the actual end-to-end flow from configuration to plots.

### 1. Configuration resolution

- CLI arguments are defined in [src/cache_analysis/cli.py](src/cache_analysis/cli.py).
- Experiment defaults are defined in [src/cache_analysis/config.py](src/cache_analysis/config.py):
  - cache size: 32 KB
  - block sizes (bytes): 64, 128, 256
  - associativities: 1, 2, 4, 8
  - replacement policy: LRU only
- A full factorial grid is generated (`3 x 4 = 12` configurations per workload).

### 2. Simulation execution

- For each geometry, the runner invokes gem5 from [src/cache_analysis/gem5_runner.py](src/cache_analysis/gem5_runner.py).
- gem5 is called with:
  - `--outdir=<run_dir>`
  - config script [scripts/gem5_cache_sweep.py](scripts/gem5_cache_sweep.py)
  - benchmark binary path and options
  - cache geometry parameters (`--cache-size-kb`, `--block-size-bytes`, `--assoc`)
- One run directory is created per configuration (for example `b64B_a1`).

### 3. Output generation per run

Inside each run directory, gem5 runner writes/uses:

- `stats.txt` (gem5 stats output)
- `stdout.log` and `stderr.log`
- `command.txt` (exact invocation)

If a non-empty `stats.txt` already exists, the runner reuses it (resume behavior).

### 4. Data extraction

- [src/cache_analysis/gem5_stats.py](src/cache_analysis/gem5_stats.py) parses `stats.txt` into key/value pairs.
- Hits and misses are extracted through fallback key candidates (or user-provided key overrides).
- `total_accesses = hits + misses` is computed.

### 5. Result structuring and export

- Structured results are represented in [src/cache_analysis/models.py](src/cache_analysis/models.py).
- Outputs are written by [src/cache_analysis/reporting.py](src/cache_analysis/reporting.py):
  - `cache_results.csv`
  - `cache_results.json`
  - `summary.txt`

### 6. Visualization

- [src/cache_analysis/visualization.py](src/cache_analysis/visualization.py) generates line and bar plots from successful results.
- Eight plots are generated per workload:
  - block vs hit rate (line/bar)
  - block vs miss rate (line/bar)
  - associativity vs hit rate (line/bar)
  - associativity vs miss rate (line/bar)

## Benchmark and File Structure

### Benchmarks used

| Benchmark binary | Source file(s) | Access pattern / variant | Runtime arguments used in this study | Role in experiment |
|---|---|---|---|---|
| `benchmarks/bin/matrix_mul` | [benchmarks/matrix_mul.c](benchmarks/matrix_mul.c) | Matrix multiplication kernels (`ijk`, `ikj`, `jki`, `blocked`) | `128 ijk`, `128 ikj`, `128 blocked` (from [run_all.sh](run_all.sh)) | Compares cache behavior across loop-ordering/kernel style |
| `benchmarks/bin/ptr_chase_seq` | [benchmarks/ptr_chase.c](benchmarks/ptr_chase.c), [benchmarks/common.h](benchmarks/common.h) | Dependent pointer-chasing, sequential chain (`CHAIN_MODE=0`) | none | Latency-sensitive dependent-load chain with higher locality than shuffled |
| `benchmarks/bin/ptr_chase_shuffle` | [benchmarks/ptr_chase.c](benchmarks/ptr_chase.c), [benchmarks/common.h](benchmarks/common.h) | Dependent pointer-chasing, shuffled chain (`CHAIN_MODE=1`) | none | Hostile/randomized dependent-load chain to stress cache behavior |

### Relevant scripts/configuration and relationships

| File path | Type | Purpose | Relationship in pipeline |
|---|---|---|---|
| [main.py](main.py) | Python launcher | Top-level launch stub | Calls CLI main |
| [run_all.sh](run_all.sh) | Shell script | Executes five workload sweeps | Calls `python3 main.py` five times with workload-specific options |
| [scripts/gem5_cache_sweep.py](scripts/gem5_cache_sweep.py) | gem5 config script | Builds gem5 SE system and L1 D-cache config | Receives geometry and workload args from Python runner |
| [src/cache_analysis/cli.py](src/cache_analysis/cli.py) | CLI | Parses args, builds configs, triggers run/export | Entry for framework execution |
| [src/cache_analysis/config.py](src/cache_analysis/config.py) | Config/data classes | Validates cache geometry and gem5 run config | Source of experiment defaults and checks |
| [src/cache_analysis/gem5_runner.py](src/cache_analysis/gem5_runner.py) | Runner | Parallel execution, retries, resume, exports | Core orchestrator between gem5 and outputs |
| [src/cache_analysis/gem5_stats.py](src/cache_analysis/gem5_stats.py) | Parser | Parses `stats.txt`, extracts hit/miss counters | Converts gem5 raw stats into numeric counters |
| [src/cache_analysis/models.py](src/cache_analysis/models.py) | Data model | Defines result schema and serialization fields | Shapes CSV/JSON output columns |
| [src/cache_analysis/reporting.py](src/cache_analysis/reporting.py) | Reporting | Writes CSV, JSON, and text summary | Final data artifacts |
| [src/cache_analysis/visualization.py](src/cache_analysis/visualization.py) | Plotting | Builds line/bar plots for hit/miss trends | Uses exported successful results |
| [benchmarks/Makefile](benchmarks/Makefile) | Build config | Compiles benchmark binaries | Produces benchmark executables used by gem5 runs |
| [requirements.txt](requirements.txt) | Python deps | Visualization/data dependencies | Required for plotting and tabular processing |

## Experiment Execution Methodology

## 1) Benchmark build

Binaries are expected at `benchmarks/bin/*`.

Example build:

```bash
cd benchmarks
make all
```

## 2) Full workload sweep execution

The canonical scripted execution in this repository is:

```bash
./run_all.sh
```

This script runs five sweeps:

1. `matrix_mul_ijk`
2. `matrix_mul_ikj`
3. `matrix_mul_blocked`
4. `ptr_chase_seq`
5. `ptr_chase_shuffle`

Each sweep executes 12 cache configurations:

- block sizes: 64, 128, 256 bytes
- associativities: 1, 2, 4, 8
- fixed cache size: 32 KB

Total configurations when running all sweeps: `5 x 12 = 60`.

## 3) Exact command style used

Example command pattern from [run_all.sh](run_all.sh):

```bash
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/matrix_mul \
  --gem5-benchmark-args='128 ijk' \
  --gem5-workload-name=matrix_mul_ijk \
  --gem5-output-subdir=gem5_runs_matrix_mul_ijk \
  --output-dir=results/matrix_mul_ijk
```

## 4) Reproducibility/consistency mechanisms present in code

- Fixed parameter grid generated by config classes.
- Deterministic benchmark modes (for example shuffled pointer chain uses fixed seed in source).
- Saved per-run command logs (`command.txt`).
- Resume behavior: existing non-empty `stats.txt` is reused.
- Runner retry attempts for failed gem5 invocations (up to 3 attempts in runner constant).

Notes:

- The framework performs one simulation per geometry in each sweep (not repeated statistical trials per same geometry).
- Benchmark code contains optional ROI macros under `GEM5`, but benchmark Makefile does not define `-DGEM5` by default.

## Data Collection and Storage

## How `stats.txt` is generated

- gem5 config runs simulation and calls stats dump in [scripts/gem5_cache_sweep.py](scripts/gem5_cache_sweep.py).
- gem5 writes stats to each run directory under `--outdir`.
- Python runner checks for existence and non-empty `stats.txt` before parsing.

## Metrics extracted from `stats.txt`

Extracted counters:

- `hits`
- `misses`
- `total_accesses = hits + misses`
- derived rates: `hit_rate`, `miss_rate`

Extraction logic uses candidate key fallbacks in [src/cache_analysis/gem5_stats.py](src/cache_analysis/gem5_stats.py), with optional explicit key overrides via CLI.

## Multi-run data organization

Per workload output folder layout:

- `results/<workload>/cache_results.csv`
- `results/<workload>/cache_results.json`
- `results/<workload>/summary.txt`
- `results/<workload>/<gem5_output_subdir>/b<Block>B_a<Assoc>/stats.txt` (+ logs)

Example:

- `results/matrix_mul_ikj/gem5_runs_matrix_mul_ikj/b128B_a4/stats.txt`

## CSV Data Description

CSV files are generated via result-model serialization in [src/cache_analysis/models.py](src/cache_analysis/models.py) and written in [src/cache_analysis/reporting.py](src/cache_analysis/reporting.py).

### Observed CSV schema

| Column | Meaning |
|---|---|
| `workload_name` | Logical workload label passed via CLI |
| `cache_size_kb` | Cache size in KB (32 in current sweeps) |
| `block_size_bytes` | Cache block size in bytes (64/128/256) |
| `block_size_kb` | Duplicate block-size field (stored numerically; currently same value as bytes field in records) |
| `associativity` | Number of ways |
| `replacement_policy` | Replacement policy label (LRU) |
| `status` | Run status (`success` or `failed`) |
| `hit_rate` | `hits / total_accesses` |
| `miss_rate` | `misses / total_accesses` |
| `hits` | Extracted cache hits counter |
| `misses` | Extracted cache misses counter |
| `total_accesses` | `hits + misses` |
| `runtime_seconds` | gem5 invocation runtime tracked by runner |
| `failure_reason` | Populated when status is failed |
| `notes` | Semicolon-delimited provenance/status notes |

### Raw stats -> CSV transformation flow

1. Parse key/value stats file lines.
2. Resolve hit/miss keys (preferred override or fallback candidates).
3. Build counters and derived rates.
4. Attach experiment key metadata (workload, geometry, policy).
5. Serialize each run record into CSV row.

## Graph Plotting Process

### Libraries used

- `matplotlib`
- `numpy`

Implemented in [src/cache_analysis/visualization.py](src/cache_analysis/visualization.py).

### Steps from CSV-equivalent records to plots

The plotting module consumes in-memory experiment result records (same content exported to CSV):

1. Group by associativity for block-size trend plots.
2. Group by block size for associativity trend plots.
3. Compute y-values from `hit_rate` or `miss_rate`.
4. Render line plots and grouped bar plots.
5. Save PNG files into each workload result directory.

### What each plot represents

- `plot_block_vs_hit_rate.png`: impact of block size on hit rate, curves by associativity.
- `plot_block_vs_miss_rate.png`: impact of block size on miss rate, curves by associativity.
- `plot_assoc_vs_hit_rate.png`: impact of associativity on hit rate, curves by block size.
- `plot_assoc_vs_miss_rate.png`: impact of associativity on miss rate, curves by block size.
- Bar plot counterparts provide grouped categorical views of the same relationships.

## Results Summary

The following summary is computed from existing `cache_results.csv` files under [results](results).

| Workload | Configurations | Best observed config (block, assoc) | Best hit rate | Worst observed config (block, assoc) | Worst hit rate | Mean hit rate |
|---|---:|---|---:|---|---:|---:|
| `matrix_mul_blocked` | 12 | 256B, 2-way | 0.994697 | 256B, 1-way | 0.968515 | 0.987041 |
| `matrix_mul_ijk` | 12 | 128B, 2-way | 0.973949 | 256B, 1-way | 0.495944 | 0.593560 |
| `matrix_mul_ikj` | 12 | 256B, 8-way | 0.992047 | 64B, 1-way | 0.948233 | 0.975456 |
| `ptr_chase_seq` | 12 | 256B, 8-way | 0.994390 | 64B, 1-way | 0.976425 | 0.986222 |
| `ptr_chase_shuffle` | 12 | 256B, 8-way | 0.694798 | 64B, 1-way | 0.690891 | 0.692714 |

### Key observations from current outputs

- `matrix_mul_blocked`, `matrix_mul_ikj`, and `ptr_chase_seq` achieve consistently high hit rates across many configurations.
- `matrix_mul_ijk` shows much larger sensitivity to geometry and includes low-hit configurations near 0.50.
- `ptr_chase_shuffle` remains around ~0.69 hit rate across all tested geometries, indicating this access mode is intentionally difficult for the tested cache.

## Conclusion

This codebase implements a reproducible gem5 workflow for analyzing cache behavior under controlled geometry sweeps.

From current results:

- block size and associativity materially affect outcomes, but sensitivity is strongly workload-dependent;
- some kernels are robustly cache-friendly (`ikj`, blocked, sequential chase), while others are much more sensitive (`ijk`, shuffled chase).

Current limitations visible in implementation:

- no repeated trials per identical configuration for variance estimation;
- default benchmark build does not define `GEM5` ROI macros;
- metrics focus on hit/miss counters (no direct IPC/CPI extraction in current pipeline).

---

## Quick Start (as implemented)

```bash
# 1) (Optional) build benchmarks
cd benchmarks && make all && cd ..

# 2) install Python dependencies
python3 -m pip install -r requirements.txt

# 3) run all five sweeps
./run_all.sh
```

Artifacts are written under [results](results).
