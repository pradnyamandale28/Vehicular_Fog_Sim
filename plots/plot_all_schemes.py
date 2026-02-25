"""
Plot comparison graphs for UCM, RCM, SCM, and PCM schemes.

- Loads results/*_logs_new.csv (or *_logs.csv fallback)
- Averages numeric metrics per load
- Generates figures 1–8
- If delay column is missing in CSVs, it will:
    - skip Figure 7 (Avg Delay)
    - compute Figure 8 (Overall Cost) WITHOUT delay (energy+blocking+migration)
"""

from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==================== COLOR SCHEME ====================
COLORS = {
    "UCM": "#E74C3C",  # Red
    "RCM": "#3498DB",  # Blue
    "SCM": "#2ECC71",  # Green
    "PCM": "#9B59B6",  # Purple
}

MARKERS = {"UCM": "o", "RCM": "s", "SCM": "^", "PCM": "D"}
LINESTYLES = {"UCM": "-", "RCM": "-", "SCM": "-", "PCM": "-"}

# Font settings (Times New Roman, 11pt)
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"]
plt.rcParams["font.size"] = 11
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11
plt.rcParams["legend.fontsize"] = 10

# Figure settings
FIGURE_WIDTH = 6
FIGURE_HEIGHT = 4
DPI = 300
LINEWIDTH = 1.5
MARKERSIZE = 6

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
OUT_DIR = RESULTS_DIR / "figures"


# -------------------- helpers --------------------
def pick_csv(scheme: str) -> Path:
    """Prefer *_logs_new.csv; fallback to *_logs.csv; error if neither exists."""
    candidates = [
        RESULTS_DIR / f"{scheme.lower()}_logs_new.csv",
        RESULTS_DIR / f"{scheme.lower()}_logs.csv",
    ]
    for p in candidates:
        if p.exists():
            print(f"[OK] {scheme}: using {p.relative_to(ROOT)}")
            return p
    msg = f"[MISSING] {scheme}: expected one of:\n" + "\n".join(
        f"  - {c.relative_to(ROOT)}" for c in candidates
    )
    raise FileNotFoundError(msg)


def setup_plot():
    """Setup plot with consistent styling."""
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # Remove top and right spines (box)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Light grid
    ax.grid(True, alpha=0.2, linestyle="--", linewidth=0.5)
    ax.set_axisbelow(True)

    return fig, ax


def finalize_plot(ax, xlabel, ylabel, filename, y_range=None):
    """Finalize plot with labels and save."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if y_range is not None:
        ax.set_ylim(y_range)

    ax.legend(loc="best", frameon=True, framealpha=0.9, edgecolor="gray")
    plt.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUT_DIR / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches="tight")
    print(f"  ✓ Saved: {filepath.relative_to(ROOT)}")
    plt.close()


def plot_four(ax, ucm, rcm, scm, pcm, y_col, label, y_range=None):
    ax.plot(
        ucm["load"],
        ucm[y_col],
        color=COLORS["UCM"],
        marker=MARKERS["UCM"],
        linestyle=LINESTYLES["UCM"],
        linewidth=LINEWIDTH,
        markersize=MARKERSIZE,
        label="UCM",
    )
    ax.plot(
        rcm["load"],
        rcm[y_col],
        color=COLORS["RCM"],
        marker=MARKERS["RCM"],
        linestyle=LINESTYLES["RCM"],
        linewidth=LINEWIDTH,
        markersize=MARKERSIZE,
        label="RCM",
    )
    ax.plot(
        scm["load"],
        scm[y_col],
        color=COLORS["SCM"],
        marker=MARKERS["SCM"],
        linestyle=LINESTYLES["SCM"],
        linewidth=LINEWIDTH,
        markersize=MARKERSIZE,
        label="SCM",
    )
    ax.plot(
        pcm["load"],
        pcm[y_col],
        color=COLORS["PCM"],
        marker=MARKERS["PCM"],
        linestyle=LINESTYLES["PCM"],
        linewidth=LINEWIDTH,
        markersize=MARKERSIZE,
        label="PCM",
    )


def find_delay_column(df: pd.DataFrame) -> str | None:
    """Try common delay column names. Return name if found, else None."""
    candidates = [
        "avg_delay_steps",
        "avg_delay_step",
        "avg_e2e_delay_steps",
        "avg_delay_ms",
        "avg_e2e_delay_ms",
        "avg_e2e_delay",
        "avg_delay",
        "mean_delay_ms",
        "mean_delay",
        "latency_ms",
        "avg_latency_ms",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def delay_series_ms(df: pd.DataFrame, col: str) -> pd.Series:
    """Convert delay to ms if steps-based; otherwise assume already ms."""
    if "step" in col:
        return df[col] * 20  # 20 ms per step in your sim
    # If it’s seconds (rare), you can adapt later; for now assume ms.
    return df[col]


# -------------------- data loading --------------------
def load_data(ucm_path, rcm_path, scm_path, pcm_path):
    """Load CSV files for all schemes and average numeric metrics per load."""
    print("\nLoading data from:")
    print(f"  UCM: {ucm_path}")
    print(f"  RCM: {rcm_path}")
    print(f"  SCM: {scm_path}")
    print(f"  PCM: {pcm_path}")

    ucm = pd.read_csv(ucm_path)
    rcm = pd.read_csv(rcm_path)
    scm = pd.read_csv(scm_path)
    pcm = pd.read_csv(pcm_path)

    print("\nData loaded:")
    print(f"  UCM: {len(ucm)} rows")
    print(f"  RCM: {len(rcm)} rows")
    print(f"  SCM: {len(scm)} rows")
    print(f"  PCM: {len(pcm)} rows")

    # Average over runs for each load (numeric-only to avoid string columns)
    ucm_avg = ucm.groupby("load", as_index=False).mean(numeric_only=True)
    rcm_avg = rcm.groupby("load", as_index=False).mean(numeric_only=True)
    scm_avg = scm.groupby("load", as_index=False).mean(numeric_only=True)
    pcm_avg = pcm.groupby("load", as_index=False).mean(numeric_only=True)

    print("\nAveraged data:")
    print(f"  UCM: {len(ucm_avg)} load points")
    print(f"  RCM: {len(rcm_avg)} load points")
    print(f"  SCM: {len(scm_avg)} load points")
    print(f"  PCM: {len(pcm_avg)} load points")

    return ucm_avg, rcm_avg, scm_avg, pcm_avg


# -------------------- plotting functions --------------------
def plot_migration_overhead_vnfs(ucm, rcm, scm, pcm):
    """Figure 1: Migration overhead (VNFs) vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["mig_overhead"] = (
            df["migrated_vnfs"] / df["total_mapped_vnfs"].replace(0, np.nan)
        ).fillna(0)

    plot_four(ax, ucm, rcm, scm, pcm, "mig_overhead", "Migration Overhead", y_range=[0, 1])

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Migration Overhead (VNFs)",
        "fig1_migration_overhead_vnfs.png",
        y_range=[0, 1],
    )


def plot_migration_overhead_state(ucm, rcm, scm, pcm):
    """Figure 2: Migration overhead (state) vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["state_overhead"] = (
            df["migrated_state_mb"] / df["total_state_mb"].replace(0, np.nan)
        ).fillna(0)

    plot_four(ax, ucm, rcm, scm, pcm, "state_overhead", "State Overhead", y_range=[0, 1])

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Migration Overhead (State)",
        "fig2_migration_overhead_state.png",
        y_range=[0, 1],
    )


def plot_energy(ucm, rcm, scm, pcm):
    """Figure 3: Total energy consumption vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["energy_kj"] = df["energy_total_j"] / 1000.0

    plot_four(ax, ucm, rcm, scm, pcm, "energy_kj", "Energy (kJ)")

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Energy Consumption (kJ)",
        "fig3_energy_consumption.png",
    )


def plot_success_rate(ucm, rcm, scm, pcm):
    """Figure 4: Success rate vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["success_rate"] = (df["success"] / df["total_arrivals"].replace(0, np.nan)).fillna(0)

    plot_four(ax, ucm, rcm, scm, pcm, "success_rate", "Success Rate", y_range=[0, 1])

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Success Rate",
        "fig4_success_rate.png",
        y_range=[0, 1],
    )


def plot_blocking_rate(ucm, rcm, scm, pcm):
    """Figure 5: Blocking rate vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["blocking_rate"] = (df["blocked"] / df["total_arrivals"].replace(0, np.nan)).fillna(0)

    plot_four(ax, ucm, rcm, scm, pcm, "blocking_rate", "Blocking Rate", y_range=[0, 1])

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Blocking Rate",
        "fig5_blocking_rate.png",
        y_range=[0, 1],
    )


def plot_drop_rate(ucm, rcm, scm, pcm):
    """Figure 6: Drop rate vs Load"""
    fig, ax = setup_plot()

    for df in (ucm, rcm, scm, pcm):
        df["drop_rate"] = (df["dropped"] / df["total_arrivals"].replace(0, np.nan)).fillna(0)

    plot_four(ax, ucm, rcm, scm, pcm, "drop_rate", "Drop Rate", y_range=[0, 1])

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Drop Rate",
        "fig6_drop_rate.png",
        y_range=[0, 1],
    )


def plot_avg_delay_if_available(ucm, rcm, scm, pcm) -> bool:
    """
    Figure 7: Average delay vs Load.
    Returns True if plotted, False if skipped because delay column is missing.
    """
    u_col = find_delay_column(ucm)
    r_col = find_delay_column(rcm)
    s_col = find_delay_column(scm)
    p_col = find_delay_column(pcm)

    if any(c is None for c in [u_col, r_col, s_col, p_col]):
        print("  ! Skipping Fig 7: No delay column found in one or more CSVs.")
        return False

    fig, ax = setup_plot()

    ucm["avg_delay_ms"] = delay_series_ms(ucm, u_col)
    rcm["avg_delay_ms"] = delay_series_ms(rcm, r_col)
    scm["avg_delay_ms"] = delay_series_ms(scm, s_col)
    pcm["avg_delay_ms"] = delay_series_ms(pcm, p_col)

    plot_four(ax, ucm, rcm, scm, pcm, "avg_delay_ms", "Average Delay (ms)")

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Average End-to-End Delay (ms)",
        "fig7_avg_delay.png",
    )
    return True


def plot_overall_cost(ucm, rcm, scm, pcm):
    """
    Figure 8: Overall network cost vs Load.

    If delay exists in all CSVs, uses 4 metrics with equal weights (0.25).
    Otherwise uses 3 metrics (energy + blocking + migration) with equal weights (1/3).
    """
    fig, ax = setup_plot()

    # Helper normalize across all schemes globally
    def normalize_global(series_list):
        combined = pd.concat(series_list, ignore_index=True)
        min_val = combined.min()
        max_val = combined.max()
        if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
            return [s * 0 for s in series_list]
        return [(s - min_val) / (max_val - min_val) for s in series_list]

    # Blocking and migration series (always available in your CSVs)
    for df in (ucm, rcm, scm, pcm):
        df["blocking_rate"] = df["blocked"] / df["total_arrivals"].replace(0, 1)
        df["mig_overhead"] = df["migrated_vnfs"] / df["total_mapped_vnfs"].replace(0, 1)

    all_energy = [ucm["energy_total_j"], rcm["energy_total_j"], scm["energy_total_j"], pcm["energy_total_j"]]
    all_blocking = [ucm["blocking_rate"], rcm["blocking_rate"], scm["blocking_rate"], pcm["blocking_rate"]]
    all_migration = [ucm["mig_overhead"], rcm["mig_overhead"], scm["mig_overhead"], pcm["mig_overhead"]]

    norm_energy = normalize_global(all_energy)
    norm_blocking = normalize_global(all_blocking)
    norm_migration = normalize_global(all_migration)

    # Delay optional
    u_col = find_delay_column(ucm)
    r_col = find_delay_column(rcm)
    s_col = find_delay_column(scm)
    p_col = find_delay_column(pcm)

    has_delay = all(c is not None for c in [u_col, r_col, s_col, p_col])

    if has_delay:
        print("  i Fig 8: delay column found — using 4-metric cost (delay+energy+blocking+migration).")
        u_delay = delay_series_ms(ucm, u_col)
        r_delay = delay_series_ms(rcm, r_col)
        s_delay = delay_series_ms(scm, s_col)
        p_delay = delay_series_ms(pcm, p_col)

        norm_delays = normalize_global([u_delay, r_delay, s_delay, p_delay])

        w_delay = 0.25
        w_energy = 0.25
        w_blocking = 0.25
        w_migration = 0.25

        ucm["overall_cost"] = (w_delay * norm_delays[0] +
                              w_energy * norm_energy[0] +
                              w_blocking * norm_blocking[0] +
                              w_migration * norm_migration[0])
        rcm["overall_cost"] = (w_delay * norm_delays[1] +
                              w_energy * norm_energy[1] +
                              w_blocking * norm_blocking[1] +
                              w_migration * norm_migration[1])
        scm["overall_cost"] = (w_delay * norm_delays[2] +
                              w_energy * norm_energy[2] +
                              w_blocking * norm_blocking[2] +
                              w_migration * norm_migration[2])
        pcm["overall_cost"] = (w_delay * norm_delays[3] +
                              w_energy * norm_energy[3] +
                              w_blocking * norm_blocking[3] +
                              w_migration * norm_migration[3])
    else:
        print("  ! Fig 8: delay column missing — using 3-metric cost (energy+blocking+migration).")
        w_energy = 1 / 3
        w_blocking = 1 / 3
        w_migration = 1 / 3

        ucm["overall_cost"] = (w_energy * norm_energy[0] +
                              w_blocking * norm_blocking[0] +
                              w_migration * norm_migration[0])
        rcm["overall_cost"] = (w_energy * norm_energy[1] +
                              w_blocking * norm_blocking[1] +
                              w_migration * norm_migration[1])
        scm["overall_cost"] = (w_energy * norm_energy[2] +
                              w_blocking * norm_blocking[2] +
                              w_migration * norm_migration[2])
        pcm["overall_cost"] = (w_energy * norm_energy[3] +
                              w_blocking * norm_blocking[3] +
                              w_migration * norm_migration[3])

    ax.plot(
        ucm["load"], ucm["overall_cost"],
        color=COLORS["UCM"], marker=MARKERS["UCM"],
        linestyle=LINESTYLES["UCM"], linewidth=LINEWIDTH,
        markersize=MARKERSIZE, label="UCM"
    )
    ax.plot(
        rcm["load"], rcm["overall_cost"],
        color=COLORS["RCM"], marker=MARKERS["RCM"],
        linestyle=LINESTYLES["RCM"], linewidth=LINEWIDTH,
        markersize=MARKERSIZE, label="RCM"
    )
    ax.plot(
        scm["load"], scm["overall_cost"],
        color=COLORS["SCM"], marker=MARKERS["SCM"],
        linestyle=LINESTYLES["SCM"], linewidth=LINEWIDTH,
        markersize=MARKERSIZE, label="SCM"
    )
    ax.plot(
        pcm["load"], pcm["overall_cost"],
        color=COLORS["PCM"], marker=MARKERS["PCM"],
        linestyle=LINESTYLES["PCM"], linewidth=LINEWIDTH,
        markersize=MARKERSIZE, label="PCM"
    )

    finalize_plot(
        ax,
        "Number of Incoming Requests",
        "Overall Network Cost",
        "fig8_overall_cost.png",
        y_range=[0, 1],
    )


# -------------------- main --------------------
def main():
    print("=" * 60)
    print("Generating Comparison Plots (UCM vs RCM vs SCM vs PCM)")
    print("=" * 60)

    # Pick CSVs (new preferred, old fallback)
    ucm_csv = pick_csv("UCM")
    rcm_csv = pick_csv("RCM")
    scm_csv = pick_csv("SCM")
    pcm_csv = pick_csv("PCM")

    # Load averaged data
    ucm, rcm, scm, pcm = load_data(str(ucm_csv), str(rcm_csv), str(scm_csv), str(pcm_csv))

    print("\n" + "=" * 60)
    print("Generating figures...")
    print("=" * 60)

    print("\n[1] Migration Overhead (VNFs)...")
    plot_migration_overhead_vnfs(ucm, rcm, scm, pcm)

    print("[2] Migration Overhead (State)...")
    plot_migration_overhead_state(ucm, rcm, scm, pcm)

    print("[3] Energy Consumption...")
    plot_energy(ucm, rcm, scm, pcm)

    print("[4] Success Rate...")
    plot_success_rate(ucm, rcm, scm, pcm)

    print("[5] Blocking Rate...")
    plot_blocking_rate(ucm, rcm, scm, pcm)

    print("[6] Drop Rate...")
    plot_drop_rate(ucm, rcm, scm, pcm)

    print("[7] Average Delay...")
    plotted_delay = plot_avg_delay_if_available(ucm, rcm, scm, pcm)

    print("[8] Overall Cost...")
    plot_overall_cost(ucm, rcm, scm, pcm)

    print("\n" + "=" * 60)
    print("✓ Done!")
    print("=" * 60)
    print(f"Location: {OUT_DIR.relative_to(ROOT)}")
    print("Generated:")
    print("  - fig1_migration_overhead_vnfs.png")
    print("  - fig2_migration_overhead_state.png")
    print("  - fig3_energy_consumption.png")
    print("  - fig4_success_rate.png")
    print("  - fig5_blocking_rate.png")
    print("  - fig6_drop_rate.png")
    if plotted_delay:
        print("  - fig7_avg_delay.png")
    else:
        print("  - (skipped) fig7_avg_delay.png  [no delay column in CSV]")
    print("  - fig8_overall_cost.png")
    print("=" * 60)


if __name__ == "__main__":
    main()
