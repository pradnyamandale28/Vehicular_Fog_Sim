"""
Master Comparison Plots - All 4 Schemes
Uses extended CSV files (load 0-1000, 5 runs)
Generates 8 comparison plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ==================== COLOR SCHEME ====================
COLORS = {
    'UCM': '#E74C3C',    # Red
    'RCM': '#3498DB',    # Blue
    'SCM': '#2ECC71',    # Green
    'PCM': '#9B59B6',    # Purple
}

MARKERS = {
    'UCM': 'o',          # Circle
    'RCM': 's',          # Square
    'SCM': '^',          # Triangle
    'PCM': 'D',          # Diamond
}

LINESTYLES = {
    'UCM': '-',
    'RCM': '-',
    'SCM': '-',
    'PCM': '-',
}

# Font settings
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
    
    print(f"\nData loaded:")
    print(f"  UCM: {len(ucm)} rows")
    print(f"  RCM: {len(rcm)} rows")
    print(f"  SCM: {len(scm)} rows")
    print(f"  PCM: {len(pcm)} rows")
    
    # Average over runs for each load (numeric columns only)
    ucm_avg = ucm.groupby('load').mean(numeric_only=True).reset_index()
    rcm_avg = rcm.groupby('load').mean(numeric_only=True).reset_index()
    scm_avg = scm.groupby('load').mean(numeric_only=True).reset_index()
    pcm_avg = pcm.groupby('load').mean(numeric_only=True).reset_index()
    
    print(f"\nAveraged data:")
    print(f"  UCM: {len(ucm_avg)} load points")
    print(f"  RCM: {len(rcm_avg)} load points")
    print(f"  SCM: {len(scm_avg)} load points")
    print(f"  PCM: {len(pcm_avg)} load points")
    
    # Check for avg_delay_steps
    for name, df in [('UCM', ucm_avg), ('RCM', rcm_avg), ('SCM', scm_avg), ('PCM', pcm_avg)]:
        if 'avg_delay_steps' not in df.columns:
            print(f"  WARNING: {name} missing avg_delay_steps column")
    
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
    
    if y_range:
        ax.set_ylim(y_range)
    
    ax.legend(loc='best', frameon=True, framealpha=0.9, edgecolor='gray')
    plt.tight_layout()
    
    os.makedirs('results/figures', exist_ok=True)
    filepath = f'results/figures/{filename}'
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    print(f"  ✓ Saved: {filepath}")
    plt.close()


def plot_migration_overhead_vnfs(ucm, rcm, scm, pcm):
    """Migration Overhead (VNFs)"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        overhead = df['migrated_vnfs'] / df['total_mapped_vnfs']
        ax.plot(df['load'], overhead, color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Migration Overhead (VNFs)',
                  'fig1_migration_overhead_vnfs.png', y_range=(0, 1.05))


def plot_migration_overhead_state(ucm, rcm, scm, pcm):
    """Migration Overhead (State MB)"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        overhead = df['migrated_state_mb'] / df['total_state_mb']
        ax.plot(df['load'], overhead, color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Migration Overhead (State)',
                  'fig2_migration_overhead_state.png', y_range=(0, 1.05))


def plot_energy(ucm, rcm, scm, pcm):
    """Energy Consumption (Joules)"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        ax.plot(df['load'], df['energy_total_j'], color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Energy Consumption (J)',
                  'fig3_energy_consumption.png')


def plot_success_rate(ucm, rcm, scm, pcm):
    """Success Rate"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        success_rate = df['success'] / df['total_arrivals']
        ax.plot(df['load'], success_rate, color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Success Rate',
                  'fig4_success_rate.png', y_range=(0, 1.05))


def plot_blocking_rate(ucm, rcm, scm, pcm):
    """Blocking Rate"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        blocking_rate = df['blocked'] / df['total_arrivals']
        ax.plot(df['load'], blocking_rate, color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Blocking Rate',
                  'fig5_blocking_rate.png', y_range=(0, 1.05))


def plot_drop_rate(ucm, rcm, scm, pcm):
    """Drop Rate"""
    fig, ax = setup_plot()
    
    for name, df, color, marker in [
        ('UCM', ucm, COLORS['UCM'], MARKERS['UCM']),
        ('RCM', rcm, COLORS['RCM'], MARKERS['RCM']),
        ('SCM', scm, COLORS['SCM'], MARKERS['SCM']),
        ('PCM', pcm, COLORS['PCM'], MARKERS['PCM'])
    ]:
        drop_rate = df['dropped'] / df['total_arrivals']
        ax.plot(df['load'], drop_rate, color=color, marker=marker,
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Drop Rate',
                  'fig6_drop_rate.png', y_range=(0, 1.05))


def plot_avg_delay(ucm, rcm, scm, pcm):
    """Average Delay (ms) - Handle RCM missing delay column"""
    fig, ax = setup_plot()
    
    # UCM, SCM, PCM use SLOT_LEN_S = different values
    # UCM: 0.1s = 100ms, SCM/PCM: 0.02s = 20ms
    # RCM: missing avg_delay_steps
    
    if 'avg_delay_steps' in ucm.columns:
        delay_ucm = ucm['avg_delay_steps'] * 100  # UCM uses 100ms slots
        ax.plot(ucm['load'], delay_ucm, color=COLORS['UCM'], marker=MARKERS['UCM'],
                linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='UCM')
    
    # Skip RCM - no delay data
    
    if 'avg_delay_steps' in scm.columns:
        delay_scm = scm['avg_delay_steps'] * 20  # SCM uses 20ms slots
        ax.plot(scm['load'], delay_scm, color=COLORS['SCM'], marker=MARKERS['SCM'],
                linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='SCM')
    
    if 'avg_delay_steps' in pcm.columns:
        delay_pcm = pcm['avg_delay_steps'] * 20  # PCM uses 20ms slots
        ax.plot(pcm['load'], delay_pcm, color=COLORS['PCM'], marker=MARKERS['PCM'],
                linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Average End-to-End Delay (ms)',
                  'fig7_avg_delay.png')


def plot_overall_cost(ucm, rcm, scm, pcm):
    """Overall Cost (normalized composite metric)"""
    fig, ax = setup_plot()
    
    # Collect all data for normalization
    all_dfs = [ucm, rcm, scm, pcm]
    all_names = ['UCM', 'RCM', 'SCM', 'PCM']
    
    # Calculate metrics for all schemes
    costs = {}
    
    for name, df in zip(all_names, all_dfs):
        if 'avg_delay_steps' in df.columns:
            # Use appropriate time conversion
            if name == 'UCM':
                delay = df['avg_delay_steps'] * 100
            else:
                delay = df['avg_delay_steps'] * 20
        else:
            delay = pd.Series([0] * len(df))  # RCM fallback
        
        energy = df['energy_total_j']
        blocking = df['blocked'] / df['total_arrivals']
        migration_vnfs = df['migrated_vnfs'] / df['total_mapped_vnfs']
        
        costs[name] = {
            'delay': delay,
            'energy': energy,
            'blocking': blocking,
            'migration': migration_vnfs,
            'load': df['load']
        }
    
    # Global normalization across all schemes
    all_delays = pd.concat([costs[n]['delay'] for n in all_names if n != 'RCM'])
    all_energies = pd.concat([costs[n]['energy'] for n in all_names])
    all_blockings = pd.concat([costs[n]['blocking'] for n in all_names])
    all_migrations = pd.concat([costs[n]['migration'] for n in all_names])
    
    delay_max = all_delays.max()
    energy_max = all_energies.max()
    blocking_max = all_blockings.max()
    migration_max = all_migrations.max()
    
    # Calculate normalized cost for each scheme
    for name in all_names:
        if name != 'RCM':  # RCM has no delay
            norm_delay = costs[name]['delay'] / max(delay_max, 1e-6)
        else:
            norm_delay = 0
        
        norm_energy = costs[name]['energy'] / max(energy_max, 1e-6)
        norm_blocking = costs[name]['blocking'] / max(blocking_max, 1e-6)
        norm_migration = costs[name]['migration'] / max(migration_max, 1e-6)
        
        # Weighted sum (equal weights)
        overall = 0.25 * (norm_delay + norm_energy + norm_blocking + norm_migration)
        
        ax.plot(costs[name]['load'], overall,
                color=COLORS[name], marker=MARKERS[name],
                linestyle=LINESTYLES[name], linewidth=LINEWIDTH,
                markersize=MARKERSIZE, label=name)
    
    finalize_plot(ax, 'Number of Incoming Requests',
                  'Overall Cost (Normalized)',
                  'fig8_overall_cost.png', y_range=(0, 1.05))


def main():
    """Generate all 8 comparison plots"""
    print("=" * 60)
    print("Generating Comparison Plots (8 figures)")
    print("=" * 60)
    
    # Load data
    ucm, rcm, scm, pcm = load_data(
        'results/ucm_logs_extended.csv',
        'results/rcm_logs_extended.csv',
        'results/scm_logs_extended.csv',
        'results/pcm_logs_extended.csv'
    )
    
    # Generate plots
    print("\n" + "=" * 60)
    print("Generating plots...")
    print("=" * 60)
    
    print("\n[1/8] Migration Overhead (VNFs)...")
    plot_migration_overhead_vnfs(ucm, rcm, scm, pcm)
    
    print("[2/8] Migration Overhead (State)...")
    plot_migration_overhead_state(ucm, rcm, scm, pcm)
    
    print("[3/8] Energy Consumption...")
    plot_energy(ucm, rcm, scm, pcm)
    
    print("[4/8] Success Rate...")
    plot_success_rate(ucm, rcm, scm, pcm)
    
    print("[5/8] Blocking Rate...")
    plot_blocking_rate(ucm, rcm, scm, pcm)
    
    print("[6/8] Drop Rate...")
    plot_drop_rate(ucm, rcm, scm, pcm)
    
    print("[7/8] Average Delay...")
    plot_avg_delay(ucm, rcm, scm, pcm)
    
    print("[8/8] Overall Cost...")
    plot_overall_cost(ucm, rcm, scm, pcm)
    
    print("\n" + "=" * 60)
    print("✓ All 8 comparison plots generated!")
    print("=" * 60)
    print("Location: results/figures/")
    print("=" * 60)


if __name__ == "__main__":
    main()