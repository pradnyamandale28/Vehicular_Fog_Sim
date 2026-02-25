"""
Master Comparison Plots - All 4 Schemes
Uses extended CSV files (load 0-1000, 5 runs)
Generates 8 comparison plots
X-axis starts from 0 on all plots (professor requirement)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ==================== COLOR SCHEME ====================
COLORS = {
    'UCM': '#E74C3C',
    'RCM': '#3498DB',
    'SCM': '#2ECC71',
    'PCM': '#9B59B6',
}

MARKERS = {
    'UCM': 'o',
    'RCM': 's',
    'SCM': '^',
    'PCM': 'D',
}

LINESTYLES = {
    'UCM': '-',
    'RCM': '-',
    'SCM': '-',
    'PCM': '-',
}

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 10

FIGURE_WIDTH = 6
FIGURE_HEIGHT = 4
DPI = 300
LINEWIDTH = 1.5
MARKERSIZE = 6


def load_data(ucm_path, rcm_path, scm_path, pcm_path):
    """Load CSV files for all schemes"""
    print(f"\nLoading data from:")
    print(f"  UCM: {ucm_path}")
    print(f"  RCM: {rcm_path}")
    print(f"  SCM: {scm_path}")
    print(f"  PCM: {pcm_path}")

    ucm = pd.read_csv(ucm_path)
    rcm = pd.read_csv(rcm_path)
    scm = pd.read_csv(scm_path)
    pcm = pd.read_csv(pcm_path)

    ucm_avg = ucm.groupby('load').mean(numeric_only=True).reset_index()
    rcm_avg = rcm.groupby('load').mean(numeric_only=True).reset_index()
    scm_avg = scm.groupby('load').mean(numeric_only=True).reset_index()
    pcm_avg = pcm.groupby('load').mean(numeric_only=True).reset_index()

    return ucm_avg, rcm_avg, scm_avg, pcm_avg


def setup_plot():
    """Setup plot with consistent styling"""
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    return fig, ax


def finalize_plot(ax, xlabel, ylabel, filename, y_range=None):
    """Finalize plot with labels and save"""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # ── X-AXIS ALWAYS STARTS FROM 0 ──────────────────────────────
    ax.set_xlim(left=0)
    ax.set_xticks([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
    # ─────────────────────────────────────────────────────────────

    if y_range:
        ax.set_ylim(y_range)

    ax.legend(loc='best', frameon=True, framealpha=0.9, edgecolor='gray')
    plt.tight_layout()

    os.makedirs('../results/figures', exist_ok=True)
    filepath = f'../results/figures/{filename}'
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    print(f"  ✓ Saved: {filepath}")
    plt.close()


def plot_migration_overhead_vnfs(ucm, rcm, scm, pcm):
    """Migration Overhead (VNFs)"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        overhead = df['migrated_vnfs'] / df['total_mapped_vnfs']
        ax.plot(df['load'], overhead, color=COLORS[name], marker=MARKERS[name],
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Migration Overhead (Normalized)',
                  'fig1_migration_overhead_vnfs.png', y_range=(0, 1.05))


def plot_migration_overhead_state(ucm, rcm, scm, pcm):
    """Migration Overhead (State MB)"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        overhead = df['migrated_state_mb'] / df['total_state_mb']
        ax.plot(df['load'], overhead, color=COLORS[name], marker=MARKERS[name],
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Migration Overhead (State, Normalized)',
                  'fig2_migration_overhead_state.png', y_range=(0, 1.05))


def plot_energy(ucm, rcm, scm, pcm):
    """Energy Consumption (Joules)"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        ax.plot(df['load'], df['energy_total_j'], color=COLORS[name],
                marker=MARKERS[name], linestyle=LINESTYLES[name],
                linewidth=LINEWIDTH, markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Energy Consumption (J)',
                  'fig3_energy_consumption.png')


def plot_success_rate(ucm, rcm, scm, pcm):
    """Success Rate"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        success_rate = df['success'] / df['total_arrivals']
        ax.plot(df['load'], success_rate, color=COLORS[name],
                marker=MARKERS[name], linestyle=LINESTYLES[name],
                linewidth=LINEWIDTH, markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Success Rate',
                  'fig4_success_rate.png', y_range=(0, 1.05))


def plot_blocking_rate(ucm, rcm, scm, pcm):
    """Blocking Rate"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        blocking_rate = df['blocked'] / df['total_arrivals']
        ax.plot(df['load'], blocking_rate, color=COLORS[name],
                marker=MARKERS[name], linestyle=LINESTYLES[name],
                linewidth=LINEWIDTH, markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Blocking Rate',
                  'fig5_blocking_rate.png', y_range=(0, 1.05))


def plot_drop_rate(ucm, rcm, scm, pcm):
    """Drop Rate"""
    fig, ax = setup_plot()
    for name, df in [('UCM', ucm), ('RCM', rcm), ('SCM', scm), ('PCM', pcm)]:
        drop_rate = df['dropped'] / df['total_arrivals']
        ax.plot(df['load'], drop_rate, color=COLORS[name],
                marker=MARKERS[name], linestyle=LINESTYLES[name],
                linewidth=LINEWIDTH, markersize=MARKERSIZE, label=name)
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Drop Rate',
                  'fig6_drop_rate.png', y_range=(0, 1.05))


def plot_avg_delay(ucm, rcm, scm, pcm):
    """Average Delay (ms)"""
    fig, ax = setup_plot()
    if 'avg_delay_steps' in ucm.columns:
        ax.plot(ucm['load'], ucm['avg_delay_steps'] * 100,
                color=COLORS['UCM'], marker=MARKERS['UCM'],
                linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='UCM')
    # RCM skipped — no delay data
    if 'avg_delay_steps' in scm.columns:
        ax.plot(scm['load'], scm['avg_delay_steps'] * 20,
                color=COLORS['SCM'], marker=MARKERS['SCM'],
                linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='SCM')
    if 'avg_delay_steps' in pcm.columns:
        ax.plot(pcm['load'], pcm['avg_delay_steps'] * 20,
                color=COLORS['PCM'], marker=MARKERS['PCM'],
                linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='PCM')
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Average End-to-End Delay (ms)',
                  'fig7_avg_delay.png')


def plot_overall_cost(ucm, rcm, scm, pcm):
    """Overall Cost (normalized composite metric)"""
    fig, ax = setup_plot()

    all_names = ['UCM', 'RCM', 'SCM', 'PCM']
    all_dfs   = [ucm,   rcm,   scm,   pcm]
    costs = {}

    for name, df in zip(all_names, all_dfs):
        if 'avg_delay_steps' in df.columns:
            delay = df['avg_delay_steps'] * (100 if name == 'UCM' else 20)
        else:
            delay = pd.Series([0] * len(df))
        costs[name] = {
            'delay':     delay,
            'energy':    df['energy_total_j'],
            'blocking':  df['blocked'] / df['total_arrivals'],
            'migration': df['migrated_vnfs'] / df['total_mapped_vnfs'],
            'load':      df['load'],
        }

    # Global max for normalization
    delay_max     = max(costs[n]['delay'].max()     for n in all_names if n != 'RCM')
    energy_max    = max(costs[n]['energy'].max()    for n in all_names)
    blocking_max  = max(costs[n]['blocking'].max()  for n in all_names)
    migration_max = max(costs[n]['migration'].max() for n in all_names)

    for name in all_names:
        norm_delay     = costs[name]['delay']     / max(delay_max,     1e-6) if name != 'RCM' else 0
        norm_energy    = costs[name]['energy']    / max(energy_max,    1e-6)
        norm_blocking  = costs[name]['blocking']  / max(blocking_max,  1e-6)
        norm_migration = costs[name]['migration'] / max(migration_max, 1e-6)
        overall = 0.25 * (norm_delay + norm_energy + norm_blocking + norm_migration)
        ax.plot(costs[name]['load'], overall,
                color=COLORS[name], marker=MARKERS[name],
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)

    finalize_plot(ax, 'Number of Incoming Requests',
                  'Overall Cost (Normalized)',
                  'fig8_overall_cost.png', y_range=(0, 1.05))


def main():
    print("=" * 60)
    print("Generating Comparison Plots (8 figures) — x-axis from 0")
    print("=" * 60)

    ucm, rcm, scm, pcm = load_data(
        '../results/ucm_logs_extended.csv',
        '../results/rcm_logs_extended.csv',
        '../results/scm_logs_extended.csv',
        '../results/pcm_logs_extended.csv'
    )

    print("\nGenerating plots...")
    plot_migration_overhead_vnfs(ucm, rcm, scm, pcm);  print("[1/8] done")
    plot_migration_overhead_state(ucm, rcm, scm, pcm); print("[2/8] done")
    plot_energy(ucm, rcm, scm, pcm);                   print("[3/8] done")
    plot_success_rate(ucm, rcm, scm, pcm);             print("[4/8] done")
    plot_blocking_rate(ucm, rcm, scm, pcm);            print("[5/8] done")
    plot_drop_rate(ucm, rcm, scm, pcm);                print("[6/8] done")
    plot_avg_delay(ucm, rcm, scm, pcm);                print("[7/8] done")
    plot_overall_cost(ucm, rcm, scm, pcm);             print("[8/8] done")

    print("\n✓ All 8 plots saved to ../results/figures/")


if __name__ == "__main__":
    main()