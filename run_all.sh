#!/bin/bash
set -e

echo "Starting Full Cache Simulation Sweep..."
export PYTHONPATH=src

echo "========================================="
echo "1/5: Running matrix_mul (ijk)"
echo "========================================="
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/matrix_mul \
  --gem5-benchmark-args='128 ijk' \
  --gem5-workload-name=matrix_mul_ijk \
  --gem5-output-subdir=gem5_runs_matrix_mul_ijk \
  --output-dir=results/matrix_mul_ijk

echo "========================================="
echo "2/5: Running matrix_mul (ikj)"
echo "========================================="
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/matrix_mul \
  --gem5-benchmark-args='128 ikj' \
  --gem5-workload-name=matrix_mul_ikj \
  --gem5-output-subdir=gem5_runs_matrix_mul_ikj \
  --output-dir=results/matrix_mul_ikj

echo "========================================="
echo "3/5: Running matrix_mul (blocked)"
echo "========================================="
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/matrix_mul \
  --gem5-benchmark-args='128 blocked' \
  --gem5-workload-name=matrix_mul_blocked \
  --gem5-output-subdir=gem5_runs_matrix_mul_blocked \
  --output-dir=results/matrix_mul_blocked

echo "========================================="
echo "4/5: Running ptr_chase_seq"
echo "========================================="
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/ptr_chase_seq \
  --gem5-workload-name=ptr_chase_seq \
  --gem5-output-subdir=gem5_runs_ptr_chase_seq \
  --output-dir=results/ptr_chase_seq

echo "========================================="
echo "5/5: Running ptr_chase_shuffle"
echo "========================================="
python3 main.py \
  --gem5-binary=../gem5/build/X86/gem5.opt \
  --gem5-benchmark=benchmarks/bin/ptr_chase_shuffle \
  --gem5-workload-name=ptr_chase_shuffle \
  --gem5-output-subdir=gem5_runs_ptr_chase_shuffle \
  --output-dir=results/ptr_chase_shuffle

echo "========================================="
echo "All 5 sweeps completed successfully!"
echo "Plots and summaries are available in the results/ folder."
