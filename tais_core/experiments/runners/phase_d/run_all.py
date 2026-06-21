#!/usr/bin/env python3
"""Phase D — Run all experiments.

Smoke:  --smoke  (5 seeds, short horizon)
Full:   --full --seeds 200
"""
import argparse
import subprocess
import sys
import time

BASE = "experiments/phase_d"
SEEDS_SMOKE = 5
SEEDS_FULL = 200


def run_script(name: str, seeds: int, output_base: str, eval_ticks: int = 10, pretrain_ticks: int = 5):
    if name == "reverse_transfer":
        cmd = [sys.executable, f"{BASE}/reverse_transfer.py", "--seeds", str(seeds)]
    else:
        cmd = [
            sys.executable, f"{BASE}/{name}.py",
            "--seeds", str(seeds),
            "--eval", str(eval_ticks),
            "--pretrain", str(pretrain_ticks),
        ]
    if output_base:
        suffix = "smoke" if seeds <= 5 else ""
        output_dir = f"{output_base}/{name}{'_' + suffix if suffix else ''}" if output_base else None
        if output_dir:
            cmd.extend(["--output", output_dir])
    cmd.append("--verbose")
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Running {name} ({seeds} seeds)...", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    t0 = time.time()
    result = subprocess.run(cmd)
    print(f"{name} finished in {time.time()-t0:.1f}s (exit={result.returncode})", file=sys.stderr)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Phase D — Run all experiments")
    parser.add_argument("--smoke", action="store_true", help="Smoke run (5 seeds)")
    parser.add_argument("--full", action="store_true", help="Full run")
    parser.add_argument("--seeds", type=int, default=None, help="Override seed count")
    parser.add_argument("--output", type=str, default="results/phase_d", dest="output_base")
    args = parser.parse_args()

    if args.seeds:
        seeds = args.seeds
    elif args.full:
        seeds = SEEDS_FULL
    else:
        seeds = SEEDS_SMOKE

    experiments = ["composition", "scaling_law", "reverse_transfer", "curriculum", "cognitive_contribution"]

    exit_codes = []
    for name in experiments:
        ec = run_script(name, seeds, args.output_base)
        exit_codes.append((name, ec))

    print(f"\n{'='*60}", file=sys.stderr)
    print("Summary:", file=sys.stderr)
    for name, ec in exit_codes:
        status = "OK" if ec == 0 else f"FAIL(exit={ec})"
        print(f"  {name}: {status}", file=sys.stderr)

    if any(ec != 0 for _, ec in exit_codes):
        sys.exit(1)


if __name__ == "__main__":
    main()
