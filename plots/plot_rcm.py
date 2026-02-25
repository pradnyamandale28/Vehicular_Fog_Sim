import pandas as pd
import matplotlib.pyplot as plt
import os

CSV = "results/rcm_logs.csv"
OUT_DIR = "results/figs"
os.makedirs(OUT_DIR, exist_ok=True)

# load + average over runs
df = pd.read_csv(CSV)
g = df.groupby("load").mean(numeric_only=True).reset_index()

# derived metrics
g["blocking_rate"] = g["blocked"] / g["total_arrivals"]
g["success_rate"] = g["success"] / g["total_arrivals"]
g["migration_cost"] = g["migrated_state_mb"]
g["energy_total"] = g["energy_idle_j"] + g["energy_load_j"]

def plot(x, y, ylabel, fname):
    plt.figure()
    plt.plot(x, y, marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, fname), dpi=300)
    plt.close()

# ---- 4 REQUIRED GRAPHS ----
plot(g["load"], g["blocking_rate"],
     "Blocking Rate", "rcm_blocking.png")

plot(g["load"], g["success_rate"],
     "Success Rate", "rcm_success.png")

plot(g["load"], g["migration_cost"],
     "Migrated State (MB)", "rcm_migration.png")

plot(g["load"], g["energy_total"],
     "Total Energy (J)", "rcm_energy.png")

print("RCM graphs generated in results/figs/")
