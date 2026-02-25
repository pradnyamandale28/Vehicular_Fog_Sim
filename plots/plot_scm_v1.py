"""
SCM Individual Plots
Generates 6 plots for SCM scheme only:
  1. Dropped Requests vs Load
  2. Accepted Requests vs Load
  3. Successful Requests vs Load
  4. Delay vs Load (ms)
  5. Blocked Requests vs Load
  6. Total Arrivals vs Load
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

# ==================== STYLE ====================
COLOR = '#2ECC71'       # SCM green
MARKER = '^'
LINEWIDTH = 2.0
MARKERSIZE = 7

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 13
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11

FIGURE_WIDTH = 7
FIGURE_HEIGHT = 4.5
DPI = 300
OUTPUT_DIR = 'results/figures/scm'

# ==================== LOAD DATA ====================
def load_data(csv_path: str) -> pd.DataFrame:
    """Load CSV and average over runs per load point."""
    print(f"\nLoading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  Raw rows   : {len(df)}")
    print(f"  Columns    : {list(df.columns)}")

    avg = df.groupby('load').mean(numeric_only=True).reset_index()
    print(f"  Load points: {len(avg)}")
    print(f"  Load range : {int(avg['load'].min())} – {int(avg['load'].max())}")

    if 'avg_delay_steps' not in avg.columns:
        print("\n  [WARNING] 'avg_delay_steps' not found in CSV.")
        print("            Delay plot will be skipped.\n")

    return avg


# ==================== PLOT HELPERS ====================
def setup_ax():
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.6)
    ax.set_axisbelow(True)
    return fig, ax


def draw_line(ax, x, y, label):
    ax.plot(x, y,
            color=COLOR, marker=MARKER, linewidth=LINEWIDTH,
            markersize=MARKERSIZE, label=label, zorder=3)


def save_fig(ax, xlabel, ylabel, title, filename):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    ax.legend(loc='best', frameon=True, framealpha=0.9, edgecolor='gray')
    plt.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(path, dpi=DPI, bbox_inches='tight')
    print(f"  ✓ Saved: {path}")
    plt.close()


# ==================== 6 PLOT FUNCTIONS ====================
def plot_dropped(df):
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['dropped'], 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Dropped Requests',
             title='SCM – Dropped Requests vs Load',
             filename='scm_dropped_vs_load.png')


def plot_accepted(df):
    fig, ax = setup_ax()
    accepted = df['total_arrivals'] - df['blocked']
    draw_line(ax, df['load'], accepted, 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Accepted Requests',
             title='SCM – Accepted Requests vs Load',
             filename='scm_accepted_vs_load.png')


def plot_success(df):
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['success'], 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Successful Requests',
             title='SCM – Successful Requests vs Load',
             filename='scm_success_vs_load.png')


def plot_delay(df):
    if 'avg_delay_steps' not in df.columns:
        print("  ⚠ Skipped (no avg_delay_steps column)")
        return
    fig, ax = setup_ax()
    # SLOT_LEN_S = 0.02 s = 20 ms  (from SCM_v1.py)
    delay_ms = df['avg_delay_steps'] * 20.0
    draw_line(ax, df['load'], delay_ms, 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Average End-to-End Delay (ms)',
             title='SCM – Average Delay vs Load',
             filename='scm_delay_vs_load.png')


def plot_blocked(df):
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['blocked'], 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Blocked Requests',
             title='SCM – Blocked Requests vs Load',
             filename='scm_blocked_vs_load.png')


def plot_arrivals(df):
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['total_arrivals'], 'SCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Total Arrivals',
             title='SCM – Total Arrivals vs Load',
             filename='scm_arrivals_vs_load.png')


# ==================== MAIN ====================
def main():
    print("=" * 60)
    print(" SCM – Individual Scheme Plots")
    print("=" * 60)

    # ── locate CSV ────────────────────────────────────────
    candidates = [
        'results/scm_logs_new.csv',
        'results/scm_logs.csv',
    ]
    csv_path = None
    for c in candidates:
        if os.path.exists(c):
            csv_path = c
            break
    if csv_path is None:
        print("\n[ERROR] SCM CSV not found. Tried:")
        for c in candidates:
            print(f"        {c}")
        return

    df = load_data(csv_path)

    # ── generate plots ────────────────────────────────────
    print("\n" + "-" * 60)
    print(" Generating plots …")
    print("-" * 60)

    print("\n[1/6] Dropped Requests vs Load")
    plot_dropped(df)

    print("[2/6] Accepted Requests vs Load")
    plot_accepted(df)

    print("[3/6] Successful Requests vs Load")
    plot_success(df)

    print("[4/6] Average Delay vs Load")
    plot_delay(df)

    print("[5/6] Blocked Requests vs Load")
    plot_blocked(df)

    print("[6/6] Total Arrivals vs Load")
    plot_arrivals(df)

    # ── summary ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" ✓ All SCM plots generated!")
    print("=" * 60)
    print(f" Output folder : {OUTPUT_DIR}/")
    print("   scm_dropped_vs_load.png")
    print("   scm_accepted_vs_load.png")
    print("   scm_success_vs_load.png")
    print("   scm_delay_vs_load.png")
    print("   scm_blocked_vs_load.png")
    print("   scm_arrivals_vs_load.png")
    print("=" * 60)


if __name__ == "__main__":
    main()