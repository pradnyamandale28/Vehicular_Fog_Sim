# plots/plot_scm.py
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def safe_rate(num, den):
    return 0.0 if den == 0 else (num / den)

def main():
    p = argparse.ArgumentParser(description="Plot SCM results (blocking, success, migration, energy)")
    p.add_argument("--csv", type=str, default="results/scm_logs_new.csv", help="Input CSV path")
    p.add_argument("--outdir", type=str, default="results/figs", help="Output directory for PNGs")
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.csv)

    # Ensure numeric
    num_cols = [
        "load","total_arrivals","blocked","dropped","success",
        "total_mapped_vnfs","migrated_vnfs","total_state_mb","migrated_state_mb",
        "energy_idle_j","energy_load_j","energy_mig_j","energy_total_j","split_count"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Aggregate across runs at each load
    g = df.groupby("load", as_index=False).mean(numeric_only=True).sort_values("load")

    # Rates
    g["blocking_rate"] = g.apply(lambda r: safe_rate(r["blocked"], r["total_arrivals"]), axis=1)
    g["success_rate"]  = g.apply(lambda r: safe_rate(r["success"], r["total_arrivals"]), axis=1)

    # Migration metric (choose ONE; default = migrated_state_mb)
    # If you prefer normalized migration overhead, uncomment migration_overhead line and use it instead.
    g["migration_mb"] = g["migrated_state_mb"]
    # g["migration_overhead"] = g.apply(lambda r: safe_rate(r["migrated_vnfs"], r["total_mapped_vnfs"]), axis=1)

    # ---------- Plot 1: Blocking ----------
    plt.figure()
    plt.plot(g["load"], g["blocking_rate"], marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel("Blocking Rate")
    plt.title("SCM: Blocking Rate vs Traffic Load")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(args.outdir, "scm_blocking.png"), dpi=200, bbox_inches="tight")
    plt.close()

    # ---------- Plot 2: Success ----------
    plt.figure()
    plt.plot(g["load"], g["success_rate"], marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel("Success Rate")
    plt.title("SCM: Success Rate vs Traffic Load")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(args.outdir, "scm_success.png"), dpi=200, bbox_inches="tight")
    plt.close()

    # ---------- Plot 3: Migration ----------
    plt.figure()
    plt.plot(g["load"], g["migration_mb"], marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel("Migrated State (MB)")
    plt.title("SCM: Migration Cost vs Traffic Load")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(args.outdir, "scm_migration.png"), dpi=200, bbox_inches="tight")
    plt.close()

    # ---------- Plot 4: Energy ----------
    plt.figure()
    plt.plot(g["load"], g["energy_total_j"], marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel("Total Energy (J)")
    plt.title("SCM: Energy Consumption vs Traffic Load")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(args.outdir, "scm_energy.png"), dpi=200, bbox_inches="tight")
    plt.close()

    # Optional extra plot (NOT required): split_count vs load
    if "split_count" in g.columns:
        plt.figure()
        plt.plot(g["load"], g["split_count"], marker="o")
        plt.xlabel("Traffic Load")
        plt.ylabel("Split Count (avg)")
        plt.title("SCM: Split Count vs Traffic Load")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(args.outdir, "scm_splits.png"), dpi=200, bbox_inches="tight")
        plt.close()

    print("Saved plots to:", args.outdir)
    print(" - scm_blocking.png")
    print(" - scm_success.png")
    print(" - scm_migration.png")
    print(" - scm_energy.png")
    print(" (+ scm_splits.png optional)")

if __name__ == "__main__":
    main()
