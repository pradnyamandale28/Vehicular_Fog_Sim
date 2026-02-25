import argparse
import csv
import os

from Schemes.RCM_v1 import start_sumo, run_rcm

CSV_COLUMNS = [
    "scheme", "load", "run",
    "total_arrivals", "blocked", "dropped", "success",
    "total_mapped_vnfs", "migrated_vnfs",
    "total_state_mb", "migrated_state_mb",
    "energy_idle_j", "energy_load_j", "energy_mig_j", "energy_total_j",
]

def ensure_csv(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if (not os.path.exists(path)) or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()

def append_row(path: str, row: dict) -> None:
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writerow({k: row.get(k) for k in CSV_COLUMNS})

def parse_args():
    p = argparse.ArgumentParser(description="Run RCM load sweep and log metrics.")
    p.add_argument("--min_load", type=int, default=0)
    p.add_argument("--max_load", type=int, default=800)
    p.add_argument("--step", type=int, default=100)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--output", type=str, default="results/rcm_logs.csv")
    p.add_argument("--gui", action="store_true")
    return p.parse_args()

def main():
    args = parse_args()
    ensure_csv(args.output)

    loads = list(range(args.min_load, args.max_load + 1, args.step))
    run_idx = 1

    for load in loads:
        for _ in range(args.runs):
            seed = args.seed + run_idx
            start_sumo(gui=args.gui)
            metrics = run_rcm(load=load, run_id=run_idx, seed=seed, gui=args.gui)
            append_row(args.output, metrics)
            run_idx += 1

if __name__ == "__main__":
    main()
