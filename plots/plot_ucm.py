import os
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "results/ucm_logs.csv"
OUT_DIR = "results/figs"

os.makedirs(OUT_DIR, exist_ok=True)

# load data
df = pd.read_csv(CSV_PATH)

# average over runs for each load
g = df.groupby("load", as_index=False).mean(numeric_only=True)

# metrics
g["blocking_rate"] = g["blocked"] / g["total_arrivals"].clip(lower=1)
g["success_rate"] = g["success"] / g["total_arrivals"].clip(lower=1)
g["migration_overhead"] = g["migrated_vnfs"] / g["total_mapped_vnfs"].clip(lower=1)

# --------- plotting helper ----------
def plot(x, y, ylabel, fname):
    plt.figure()
    plt.plot(x, y, marker="o")
    plt.xlabel("Traffic Load")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, fname), dpi=300)
    plt.close()

# --------- 4 REQUIRED GRAPHS ----------
plot(g["load"], g["blocking_rate"],
     "Blocking Rate", "ucm_blocking.png")

plot(g["load"], g["success_rate"],
     "Success Rate", "ucm_success.png")

plot(g["load"], g["migration_overhead"],
     "Migration Overhead (migrated VNFs / mapped VNFs)",
     "ucm_migration_overhead.png")

plot(g["load"], g["energy_total_j"],
     "Total Energy Consumption (J)",
     "ucm_energy.png")

print("UCM graphs generated in results/figs/")
