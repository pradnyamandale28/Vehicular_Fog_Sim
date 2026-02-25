"""
UCM Individual Plots
Generates 6 plots for UCM scheme only:
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
COLOR = '#E74C3C'       # UCM red
MARKER = 'o'
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
OUTPUT_DIR = 'results/figures/ucm'

# ==================== LOAD DATA ====================
def load_data(csv_path: str) -> pd.DataFrame:
    """Load CSV and average over runs per load point."""
    print(f"\nLoading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  Raw rows: {len(df)}")
    print(f"  Columns:  {list(df.columns)}")

    # Average across runs for each load value (numeric columns only)
    avg = df.groupby('load').mean(numeric_only=True).reset_index()
    print(f"  Load points after averaging: {len(avg)}")
    print(f"  Load range: {int(avg['load'].min())} – {int(avg['load'].max())}")
    return avg


# ==================== PLOT HELPERS ====================
def setup_ax():
    """Create figure + axis with consistent style."""
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.6)
    ax.set_axisbelow(True)
    return fig, ax


def draw_line(ax, x, y, label):
    """Draw the UCM line on the given axis."""
    ax.plot(x, y,
            color=COLOR, marker=MARKER, linewidth=LINEWIDTH,
            markersize=MARKERSIZE, label=label, zorder=3)


def save_fig(ax, xlabel, ylabel, title, filename):
    """Set labels, title, legend, tight-layout and save."""
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
    """1. Dropped Requests vs Load"""
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['dropped'], 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Dropped Requests',
             title='UCM – Dropped Requests vs Load',
             filename='ucm_dropped_vs_load.png')


def plot_accepted(df):
    """2. Accepted Requests vs Load  (Accepted = total_arrivals − blocked)"""
    fig, ax = setup_ax()
    accepted = df['total_arrivals'] - df['blocked']
    draw_line(ax, df['load'], accepted, 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Accepted Requests',
             title='UCM – Accepted Requests vs Load',
             filename='ucm_accepted_vs_load.png')


def plot_success(df):
    """3. Successful Requests vs Load"""
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['success'], 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Successful Requests',
             title='UCM – Successful Requests vs Load',
             filename='ucm_success_vs_load.png')


def plot_delay(df):
    """4. Average Delay vs Load  (convert steps → ms using SLOT_LEN_S = 0.1 s)"""
    fig, ax = setup_ax()
    # SLOT_LEN_S = 0.1 s = 100 ms  (from UCM_v1.py)
    delay_ms = df['avg_delay_steps'] * 100.0
    draw_line(ax, df['load'], delay_ms, 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Average End-to-End Delay (ms)',
             title='UCM – Average Delay vs Load',
             filename='ucm_delay_vs_load.png')


def plot_blocked(df):
    """5. Blocked Requests vs Load"""
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['blocked'], 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Blocked Requests',
             title='UCM – Blocked Requests vs Load',
             filename='ucm_blocked_vs_load.png')


def plot_arrivals(df):
    """6. Total Arrivals vs Load"""
    fig, ax = setup_ax()
    draw_line(ax, df['load'], df['total_arrivals'], 'UCM')
    save_fig(ax,
             xlabel='Number of Incoming Requests',
             ylabel='Total Arrivals',
             title='UCM – Total Arrivals vs Load',
             filename='ucm_arrivals_vs_load.png')


# ==================== MAIN ====================
def main():
    print("=" * 60)
    print(" UCM – Individual Scheme Plots")
    print("=" * 60)

    # ── locate CSV ────────────────────────────────────────
    candidates = [
        'results/ucm_logs_new.csv',
        'results/ucm_logs.csv',
    ]
    csv_path = None
    for c in candidates:
        if os.path.exists(c):
            csv_path = c
            break
    if csv_path is None:
        print("\n[ERROR] UCM CSV not found. Tried:")
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
    print(" ✓ All 6 UCM plots generated!")
    print("=" * 60)
    print(f" Output folder : {OUTPUT_DIR}/")
    print("   ucm_dropped_vs_load.png")
    print("   ucm_accepted_vs_load.png")
    print("   ucm_success_vs_load.png")
    print("   ucm_delay_vs_load.png")
    print("   ucm_blocked_vs_load.png")
    print("   ucm_arrivals_vs_load.png")
    print("=" * 60)


if __name__ == "__main__":
    main()