# gem5 Cache Analysis Experimental Study (Repository Documentation)

This document describes the current repository implementation exactly as it exists today.
No assumptions are made beyond the code and files present in the project.

## 1. Project Overview

### Study Objective
This project automates cache-performance experiments in gem5 by sweeping cache geometry parameters and measuring hit/miss behavior for memory-intensive C benchmarks.

Primary investigation dimensions implemented in the codebase:
- Block size sweep (configured in Python defaults)
- Associativity sweep
- Fixed L1 data-cache capacity per experiment run

Primary benchmark classes implemented:
- Matrix multiplication kernels with different traversal orders
- Pointer-chasing dependent-load kernels (sequential and shuffled chain)

### Simulation Environment and Tools
| Component | Current Implementation |
|---|---|
| Simulator backend | gem5 only |
| gem5 invocation style | gem5 binary + Python config script |
| gem5 config script | scripts/gem5_cache_sweep.py |
| CPU models in gem5 script | TimingSimpleCPU, AtomicSimpleCPU, MinorCPU |
| Memory model | DDR3_1600_8x8 via MemCtrl |
| Interconnect | SystemXBar |
| Orchestration language | Python |
| Visualization stack | matplotlib + numpy |
| Output formats | CSV, JSON, TXT summary, PNG plots |

## 2. Pipeline Workflow

The implemented pipeline is:

1. Configuration stage
- main.py calls cache_analysis.cli.main()
- CLI reads cache geometry sweep arguments and gem5 runtime settings
- ExperimentConfig and Gem5RunConfig are validated

2. Simulation dispatch stage
- Gem5ExperimentRunner enumerates all geometry combinations
- Runs are launched in parallel with ThreadPoolExecutor
- Each run gets its own output directory

3. Simulation execution stage
- Runner invokes gem5 with scripts/gem5_cache_sweep.py
- The gem5 script builds system objects (CPU, cache, bus, DRAM, process)
- Benchmark executable is run in SE mode

4. Output generation stage
- gem5 generates stats.txt and logs in per-run folders
- command.txt, stdout.log, stderr.log are written by the runner

5. Data extraction stage
- gem5_stats.parse_stats_file() parses stats.txt key/value lines
- extract_hits_and_misses() resolves hit/miss keys with fallbacks
- total_accesses is computed as hits + misses

6. Aggregation and export stage
- Results are assembled into ExperimentResult rows
- reporting.py writes:
  - cache_results.csv
  - cache_results.json
  - summary.txt

7. Visualization stage
- visualization.py generates line and bar plots for hit/miss rates versus:
  - Block size
  - Associativity

Practical behavior implemented:
- Retry support for failed gem5 runs
- Resume/reuse behavior when stats.txt already exists and is non-empty
- Failed configurations are included with status markers instead of crashing the batch

## 3. Benchmark and File Structure

### Benchmarks
| Binary target | Source file | Role in experiment | Notes |
|---|---|---|---|
| benchmarks/bin/matrix_mul | benchmarks/matrix_mul.c | Matrix workload with selectable access patterns | Supports ijk, ikj, jki, blocked; includes warmup and ROI wrappers |
| benchmarks/bin/ptr_chase_seq | benchmarks/ptr_chase.c | Pointer-chase sequential chain | Built with -DCHAIN_MODE=0 |
| benchmarks/bin/ptr_chase_shuffle | benchmarks/ptr_chase.c | Pointer-chase shuffled chain | Built with -DCHAIN_MODE=1 and fixed-seed deterministic shuffle |

### Supporting benchmark files
| File | Purpose |
|---|---|
| benchmarks/common.h | Shared constants/macros for pointer-chase (ARRAY_SIZE, PTR_ITERS, ROI macros, sinks) |
| benchmarks/Makefile | Builds benchmark binaries with gcc -O2 -march=x86-64 -g -std=c11 |

### Orchestration and analysis files
| File | Purpose | Relationship |
|---|---|---|
| main.py | Top-level launch point | Calls cli.main() |
| src/cache_analysis/cli.py | CLI argument handling and run kick-off | Builds configs, starts runner |
| src/cache_analysis/config.py | Dataclasses/defaults/validation | Defines geometry sweep defaults |
| src/cache_analysis/gem5_runner.py | Parallel run execution + export pipeline | Calls gem5 script, parser, reporting, plotting |
| src/cache_analysis/gem5_stats.py | stats.txt parser and hit/miss extraction | Used by gem5_runner |
| src/cache_analysis/models.py | Result/counter data models | Used by runner/reporting/plotting |
| src/cache_analysis/reporting.py | CSV/JSON/summary writing | Used after run completion |
| src/cache_analysis/visualization.py | Plot generation | Used on successful rows |
| scripts/gem5_cache_sweep.py | gem5 system construction script | Called by gem5 binary per run |

### Output layout
| Path pattern | Contents |
|---|---|
| results/<workload>/cache_results.csv | Flattened tabular results |
| results/<workload>/cache_results.json | Structured config + result rows |
| results/<workload>/summary.txt | Text summary report |
| results/<workload>/*.png | Plot artifacts (line + bar charts) |
| results/<workload>/gem5_runs/b<block>B_a<assoc>/ | Per-run logs and raw stats |

## 4. Experiment Execution Methodology

### Procedure implemented in code
1. Choose benchmark binary and output directory
2. Launch main.py with gem5 binary/script and sweep parameters
3. Runner creates full-factorial combinations of:
   - block_sizes_bytes
   - associativities
4. One gem5 process is launched per combination
5. stats.txt is parsed and transformed into counters and rates
6. Batch outputs and plots are generated

### Canonical execution command template
Use this structure (values are examples):

```bash
export PYTHONPATH=src

python3 main.py \
  --gem5-binary /path/to/gem5.opt \
  --gem5-config-script scripts/gem5_cache_sweep.py \
  --gem5-benchmark benchmarks/bin/matrix_mul \
  --gem5-benchmark-args "1024 blocked" \
  --gem5-workload-name matrix_mul \
  --cache-size-kb 32 \
  --block-sizes-bytes 64 128 256 \
  --associativities 1 2 4 8 \
  --output-dir results/matrix_mul \
  --gem5-output-subdir gem5_runs \
  --gem5-cpu-type TimingSimpleCPU
```

### Reproducibility controls implemented
- Deterministic shuffled pointer chain (fixed seed in ptr_chase.c)
- Fixed compile-time array size and iteration counts for pointer chase
- Per-run command logging in command.txt
- Retry logic for transient failures
- Resume behavior when valid stats.txt already exists

### Current codebase consistency note
The repository currently has a mixed naming state:
- config.py uses block_size_bytes and block_sizes_bytes
- models.py and gem5_runner.py still include legacy block_size_kb fields in ExperimentKey/result serialization paths

This should be considered during interpretation of exported schema and when extending the code.

## 5. Data Collection and Storage

### How stats.txt is produced
- gem5 executes workload in SE mode
- At simulation end, m5.stats.dump() is called in scripts/gem5_cache_sweep.py
- stats.txt is written under the run outdir

### Metrics extracted in the code
From gem5 stats keys (with fallback candidates):
- hits
- misses
- total_accesses = hits + misses
- hit_rate = hits / total_accesses
- miss_rate = misses / total_accesses

### Storage model
Per-run artifacts:
- stats.txt
- stdout.log
- stderr.log
- command.txt

Per-workload aggregated artifacts:
- cache_results.csv
- cache_results.json
- summary.txt
- 8 PNG plot files

## 6. CSV Data Description

The CSV writer builds columns as the union of result-row keys and writes one row per experiment configuration.

### Current CSV columns produced by model serialization
| Column | Meaning |
|---|---|
| workload_name | Benchmark/workload label |
| cache_size_kb | Cache capacity in KB |
| block_size_bytes | Block size in bytes |
| block_size_kb | Legacy field retained in ExperimentKey serialization |
| associativity | Cache associativity |
| replacement_policy | Replacement policy label |
| status | success or failed |
| failure_reason | Failure message for failed runs |
| total_accesses | hits + misses |
| hits | Cache hits |
| misses | Cache misses |
| hit_rate | hits / total_accesses |
| miss_rate | misses / total_accesses |
| runtime_seconds | Wall-clock runtime of subprocess |
| notes | Joined metadata strings |

### Raw stats to CSV transformation
1. Parse stats.txt into a dictionary of key/value floats
2. Resolve hit and miss keys via fallback lists
3. Compute total_accesses and rates
4. Serialize ExperimentResult.to_dict()
5. Write rows to CSV

## 7. Graph Plotting Process

### Libraries used
- matplotlib
- numpy

### Plot generation flow
1. Gather successful results
2. Group rows by associativity for block-size plots
3. Group rows by block-size for associativity plots
4. Sort x-axis points per series
5. Render and save figures

### Plot outputs created by code
Line plots:
- plot_block_vs_hit_rate.png
- plot_block_vs_miss_rate.png
- plot_assoc_vs_hit_rate.png
- plot_assoc_vs_miss_rate.png

Bar plots:
- bar_block_vs_hit_rate.png
- bar_block_vs_miss_rate.png
- bar_assoc_vs_hit_rate.png
- bar_assoc_vs_miss_rate.png

### What each graph represents
- Block-size graphs: rate trend as block size changes, with one series per associativity
- Associativity graphs: rate trend as associativity changes, with one series per block size

## 8. Results Summary

### Current repository result state
The result files currently present in:
- results/matrix_mul
- results/ptr_chase_shuffle

exist but are empty in this workspace snapshot (empty CSV/JSON/TXT).

Because no populated dataset is currently present, a numerical comparison table cannot be reconstructed from repository artifacts alone.

### Comparison table (current state)
| Workload | Data file present | Populated rows available | Status |
|---|---|---|---|
| matrix_mul | Yes | No | Re-run required for numeric summary |
| ptr_chase_shuffle | Yes | No | Re-run required for numeric summary |
| ptr_chase_seq | Not present in current results/ tree | N/A | Run not archived in current snapshot |

### Expected interpretation framework (once data is regenerated)
- Compare hit_rate and miss_rate across associativity at fixed block size
- Compare hit_rate and miss_rate across block size at fixed associativity
- Compare pointer_chase sequential vs shuffled for locality sensitivity
- Compare matrix patterns (ijk/ikj/jki/blocked) for cache-friendly traversal effects

## 9. Conclusion

This repository implements a full gem5 automation pipeline for cache-geometry studies, including benchmark execution, stat extraction, reporting, and plotting.

Key strengths of current implementation:
- End-to-end automation from CLI to figures
- Fault-tolerant run execution with retries and failure capture
- Deterministic pointer-chasing workload generation
- Flexible gem5 stat-key fallback parsing

Current limitations visible in codebase snapshot:
- Mixed legacy/new schema naming (block_size_bytes vs block_size_kb fields)
- gem5 script currently still accepts AtomicSimpleCPU in addition to timing-oriented models
- Existing result artifacts are empty, so this repository snapshot is documentation-ready but not result-complete

For academic submission, regenerate results in this environment and include populated CSV/JSON/summary tables and plots produced from the exact committed code.
