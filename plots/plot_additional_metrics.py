"""
Additional Comparison Plots: Dropped, Accepted, and Delay vs Load
For UCM, RCM, SCM, and PCM schemes
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
    'UCM': '-',          # Solid
    'RCM': '-',          # Solid
    'SCM': '-',          # Solid
    'PCM': '-',          # Solid
}

# Font settings (Times New Roman, 11pt)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 10

# Figure settings
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
    
    return ucm_avg, rcm_avg, scm_avg, pcm_avg


def setup_plot():
    """Setup plot with consistent styling"""
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    
    # Remove top and right spines (box)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Light grid
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    
    return fig, ax


def finalize_plot(ax, xlabel, ylabel, filename, y_range=None):
    """Finalize plot with labels and save"""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    if y_range:
        ax.set_ylim(y_range)
    
    # Legend inside plot (best position)
    ax.legend(loc='best', frameon=True, framealpha=0.9, edgecolor='gray')
    
    plt.tight_layout()
    
    # Save with high DPI
    os.makedirs('results/figures', exist_ok=True)
    filepath = f'results/figures/{filename}'
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    print(f"  ✓ Saved: {filepath}")
    plt.close()


def plot_dropped_requests(ucm, rcm, scm, pcm):
    """Plot: Absolute number of dropped requests vs Load"""
    fig, ax = setup_plot()
    
    ax.plot(ucm['load'], ucm['dropped'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['dropped'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['dropped'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['dropped'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Dropped Requests (Count)', 
                  'dropped_requests_vs_load.png')


def plot_accepted_requests(ucm, rcm, scm, pcm):
    """Plot: Absolute number of accepted requests vs Load"""
    fig, ax = setup_plot()
    
    # Accepted = Arrivals - Blocked
    ucm['accepted'] = ucm['total_arrivals'] - ucm['blocked']
    rcm['accepted'] = rcm['total_arrivals'] - rcm['blocked']
    scm['accepted'] = scm['total_arrivals'] - scm['blocked']
    pcm['accepted'] = pcm['total_arrivals'] - pcm['blocked']
    
    ax.plot(ucm['load'], ucm['accepted'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['accepted'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['accepted'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['accepted'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Accepted Requests (Count)', 
                  'accepted_requests_vs_load.png')


def plot_successful_requests(ucm, rcm, scm, pcm):
    """Plot: Absolute number of successful requests vs Load"""
    fig, ax = setup_plot()
    
    ax.plot(ucm['load'], ucm['success'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['success'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['success'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['success'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Successful Requests (Count)', 
                  'successful_requests_vs_load.png')


def plot_delay_vs_load(ucm, rcm, scm, pcm):
    """Plot: Average delay vs Load (in milliseconds)"""
    fig, ax = setup_plot()
    
    # Convert steps to milliseconds (SLOT_LEN_S = 0.02s = 20ms)
    ucm['avg_delay_ms'] = ucm['avg_delay_steps'] * 20
    rcm['avg_delay_ms'] = rcm['avg_delay_steps'] * 20
    scm['avg_delay_ms'] = scm['avg_delay_steps'] * 20
    pcm['avg_delay_ms'] = pcm['avg_delay_steps'] * 20
    
    ax.plot(ucm['load'], ucm['avg_delay_ms'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['avg_delay_ms'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['avg_delay_ms'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['avg_delay_ms'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Average End-to-End Delay (ms)', 
                  'delay_vs_load.png')


def plot_blocked_requests(ucm, rcm, scm, pcm):
    """Plot: Absolute number of blocked requests vs Load"""
    fig, ax = setup_plot()
    
    ax.plot(ucm['load'], ucm['blocked'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['blocked'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['blocked'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['blocked'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Blocked Requests (Count)', 
                  'blocked_requests_vs_load.png')


def plot_arrivals_vs_load(ucm, rcm, scm, pcm):
    """Plot: Total arrivals vs Load (should be similar for all schemes)"""
    fig, ax = setup_plot()
    
    ax.plot(ucm['load'], ucm['total_arrivals'], 
            color=COLORS['UCM'], marker=MARKERS['UCM'], 
            linestyle=LINESTYLES['UCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='UCM')
    
    ax.plot(rcm['load'], rcm['total_arrivals'], 
            color=COLORS['RCM'], marker=MARKERS['RCM'], 
            linestyle=LINESTYLES['RCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='RCM')
    
    ax.plot(scm['load'], scm['total_arrivals'], 
            color=COLORS['SCM'], marker=MARKERS['SCM'], 
            linestyle=LINESTYLES['SCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='SCM')
    
    ax.plot(pcm['load'], pcm['total_arrivals'], 
            color=COLORS['PCM'], marker=MARKERS['PCM'], 
            linestyle=LINESTYLES['PCM'], linewidth=LINEWIDTH, 
            markersize=MARKERSIZE, label='PCM')
    
    finalize_plot(ax, 
                  'Number of Incoming Requests', 
                  'Total Arrivals (Count)', 
                  'arrivals_vs_load.png')


def plot_request_breakdown(ucm, rcm, scm, pcm):
    """Plot: Stacked bar chart showing request breakdown at each load point"""
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # We'll create 4 subplots side by side (one per scheme)
    fig, axes = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
    
    schemes = [
        ('UCM', ucm, COLORS['UCM']),
        ('RCM', rcm, COLORS['RCM']),
        ('SCM', scm, COLORS['SCM']),
        ('PCM', pcm, COLORS['PCM'])
    ]
    
    for idx, (name, data, color) in enumerate(schemes):
        ax = axes[idx]
        
        loads = data['load']
        blocked = data['blocked']
        dropped = data['dropped']
        success = data['success']
        
        # Stacked bar
        ax.bar(loads, success, label='Success', color='#27AE60', alpha=0.8)
        ax.bar(loads, dropped, bottom=success, label='Dropped', color='#E67E22', alpha=0.8)
        ax.bar(loads, blocked, bottom=success+dropped, label='Blocked', color='#E74C3C', alpha=0.8)
        
        ax.set_xlabel('Load (Requests)')
        if idx == 0:
            ax.set_ylabel('Number of Requests')
        ax.set_title(f'{name}')
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5, axis='y')
        ax.set_axisbelow(True)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save
    os.makedirs('results/figures', exist_ok=True)
    filepath = 'results/figures/request_breakdown_comparison.png'
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    print(f"  ✓ Saved: {filepath}")
    plt.close()


def main():
    """Generate all additional plots"""
    print("=" * 60)
    print("Generating Additional Plots")
    print("(Dropped, Accepted, Delay vs Load)")
    print("=" * 60)
    
    # Load data
    ucm, rcm, scm, pcm = load_data(
        'results/ucm_logs_new.csv',
        'results/rcm_logs_new.csv',
        'results/scm_logs_new.csv',
        'results/pcm_logs_new.csv'
    )
    
    # Generate plots
    print("\n" + "=" * 60)
    print("Generating plots...")
    print("=" * 60)
    
    print("\n[1/7] Dropped Requests vs Load...")
    plot_dropped_requests(ucm, rcm, scm, pcm)
    
    print("[2/7] Accepted Requests vs Load...")
    plot_accepted_requests(ucm, rcm, scm, pcm)
    
    print("[3/7] Successful Requests vs Load...")
    plot_successful_requests(ucm, rcm, scm, pcm)
    
    print("[4/7] Delay vs Load...")
    plot_delay_vs_load(ucm, rcm, scm, pcm)
    
    print("[5/7] Blocked Requests vs Load...")
    plot_blocked_requests(ucm, rcm, scm, pcm)
    
    print("[6/7] Total Arrivals vs Load...")
    plot_arrivals_vs_load(ucm, rcm, scm, pcm)
    
    print("[7/7] Request Breakdown Comparison...")
    plot_request_breakdown(ucm, rcm, scm, pcm)
    
    print("\n" + "=" * 60)
    print("✓ All additional plots generated successfully!")
    print("=" * 60)
    print("Location: results/figures/")
    print("Files:")
    print("  - dropped_requests_vs_load.png")
    print("  - accepted_requests_vs_load.png")
    print("  - successful_requests_vs_load.png")
    print("  - delay_vs_load.png")
    print("  - blocked_requests_vs_load.png")
    print("  - arrivals_vs_load.png")
    print("  - request_breakdown_comparison.png")
    print("=" * 60)


if __name__ == "__main__":
    main()