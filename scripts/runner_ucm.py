"""
UCM Load Sweep Runner
Runs UCM scheme across load range with multiple repetitions
"""

import argparse
import csv
import os
import sys
from Schemes.UCM_v1 import start_sumo, run_ucm


CSV_COLUMNS = [
    "scheme", "load", "run",
    "total_arrivals", "blocked", "dropped", "success",
    "total_mapped_vnfs", "migrated_vnfs",
    "total_state_mb", "migrated_state_mb",
    "energy_idle_j", "energy_load_j", "energy_mig_j", "energy_total_j",
    "avg_delay_steps",
]


def ensure_csv(path: str) -> None:
    """Create CSV with headers if it doesn't exist"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def append_row(path: str, row: dict) -> None:
    """Append single result row to CSV"""
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writerow({k: row.get(k) for k in CSV_COLUMNS})


def main():
    parser = argparse.ArgumentParser(description="UCM load sweep experiment")
    parser.add_argument("--min_load", type=int, default=0, 
                       help="Minimum load (number of requests)")
    parser.add_argument("--max_load", type=int, default=800,
                       help="Maximum load (number of requests)")
    parser.add_argument("--step", type=int, default=100,
                       help="Load increment step")
    parser.add_argument("--runs", type=int, default=3,
                       help="Number of repetitions per load point")
    parser.add_argument("--seed", type=int, default=1,
                       help="Base random seed")
    parser.add_argument("--output", type=str, default="results/ucm_logs.csv",
                       help="Output CSV file path")
    parser.add_argument("--gui", action="store_true",
                       help="Enable SUMO GUI (for debugging)")
    args = parser.parse_args()
    
    ensure_csv(args.output)
    
    loads = list(range(args.min_load, args.max_load + 1, args.step))
    run_idx = 1
    total_runs = len(loads) * args.runs
    
    print("=" * 60)
    print("UCM Load Sweep Experiment")
    print("=" * 60)
    print(f"Load range: {args.min_load} to {args.max_load} (step: {args.step})")
    print(f"Runs per load: {args.runs}")
    print(f"Total runs: {total_runs}")
    print(f"Output: {args.output}")
    print("=" * 60)
    
    for load in loads:
        for rep in range(args.runs):
            seed = args.seed + run_idx
            
            print(f"\n[{run_idx}/{total_runs}] Load={load}, Rep={rep+1}/{args.runs}, Seed={seed}")
            
            try:
                start_sumo(gui=args.gui)
                metrics = run_ucm(load=load, run_id=run_idx, seed=seed, gui=args.gui)
                append_row(args.output, metrics)
                
                # Print summary
                print(f"  Arrivals: {metrics['total_arrivals']}, "
                      f"Blocked: {metrics['blocked']}, "
                      f"Dropped: {metrics['dropped']}, "
                      f"Success: {metrics['success']}")
                
            except Exception as e:
                print(f"  ERROR: {e}")
                sys.exit(1)
            
            run_idx += 1
    
    print("\n" + "=" * 60)
    print("UCM Experiment Completed!")
    print(f"Results saved to: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()