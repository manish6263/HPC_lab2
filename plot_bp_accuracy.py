#!/usr/bin/env python3
"""
plot_bp_accuracy.py

Creates a line/marker plot of branch predictor accuracy per predictor (per-workload or global).

Outputs:
  bp_accuracy_overall.png          # global (all workloads combined median per predictor)
  bp_accuracy_{workload}.png       # per-workload plot (if workload column found)

Usage:
  python3 plot_bp_accuracy.py
  python3 plot_bp_accuracy.py --csv branch_analysis/accuracy_summary.csv
"""
import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("--csv", default="branch_analysis/accuracy_summary.csv", help="Path to accuracy CSV (accuracy_summary.csv) or summary_for_plots_bp.csv")
parser.add_argument("--outdir", default="branch_analysis/plots", help="Output folder for plots")
args = parser.parse_args()

candidates = []
if args.csv:
    candidates.append(args.csv)
candidates += [
    "branch_analysis/accuracy_summary.csv",
    "branch_analysis/accuracy_summary.csv",
    "branch_analysis/summary_median_bp.csv",
    "branch_analysis/summary_for_plots_bp.csv",
    "summary_for_plots_bp.csv",
    "summary_for_plots.csv",
    "summary_median.csv"
]

csv_path = None
for p in candidates:
    if p and os.path.exists(p):
        csv_path = p
        break

if csv_path is None:
    raise SystemExit("No CSV found. Run compute/median scripts first and place the CSV in branch_analysis/ or pass --csv")

print("Using CSV:", csv_path)
df = pd.read_csv(csv_path)

# If accuracy already computed, prefer that
if 'accuracy_committed' in df.columns:
    acc_df = df[['workload','predictor','accuracy_committed']].copy()
else:
    # try to compute accuracy from available columns
    # common column names in your pipeline:
    committed_col = None
    mispred_col = None
    for c in df.columns:
        low = c.lower()
        if ('committed' in low and 'branch' in low) or 'branch_committed' in low:
            committed_col = c
        if ('mispred' in low and 'predict' in low) or 'branch_mispredicted' in low or 'mispredicted' in low:
            mispred_col = c
    if committed_col is None or mispred_col is None:
        raise SystemExit(f"Couldn't find branch_committed or branch_mispredicted columns in {csv_path}. Columns: {list(df.columns)}")
    df[committed_col] = pd.to_numeric(df[committed_col], errors='coerce')
    df[mispred_col] = pd.to_numeric(df[mispred_col], errors='coerce')
    df['accuracy_committed'] = 1.0 - (df[mispred_col] / df[committed_col])
    # normalize workload/predictor columns
    if 'workload' not in df.columns:
        df['workload'] = df.get('workload', 'ALL')
    if 'predictor' not in df.columns:
        # try to infer from run name
        if 'run' in df.columns:
            df['predictor'] = df['run'].astype(str).apply(lambda s: s.split('_')[1] if '_' in s else s)
        else:
            df['predictor'] = df.get('predictor', 'unknown')
    acc_df = df[['workload','predictor','accuracy_committed']].copy()

# ensure strings
acc_df['predictor'] = acc_df['predictor'].astype(str)
acc_df['workload']  = acc_df['workload'].astype(str)

os.makedirs(args.outdir, exist_ok=True)

# helper to plot one series
def plot_series(labels, values, title, outpath, ylim_min=None, ylim_max=1.0):
    fig, ax = plt.subplots(figsize=(8,4.5))
    x = np.arange(len(labels))
    ax.plot(x, values, marker='o', linewidth=1.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right')
    ax.set_title(title)
    ax.set_ylabel("Prediction Accuracy (in %)")
    # convert to percentage for annotation and y-axis
    values_pct = np.array(values) * 100.0
    # annotate
    for xi, yi, yp in zip(x, values, values_pct):
        txt = f"{yp:.2f}"
        ax.annotate(txt, (xi, yi), textcoords="offset points", xytext=(0,8), ha='center', color='red', fontsize=9)
    # y limits
    if ylim_min is None:
        ymin = min(values) - 0.05
    else:
        ymin = ylim_min
    ymax = ylim_max
    ax.set_ylim(ymin, ymax)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)
    print("Saved", outpath)

# 1) Global aggregation (median accuracy per predictor across workloads)
global_grp = acc_df.groupby('predictor')['accuracy_committed'].median().reset_index()
global_grp = global_grp.sort_values('accuracy_committed', ascending=True)  # ascending or descending depending on preference
labels = global_grp['predictor'].tolist()
values = global_grp['accuracy_committed'].tolist()

# choose nice ymin: if best accuracy near 0.99 and worst 0.8, set ymin=0.8
min_val = min(values) if values else 0.0
ymin = max(0.0, min_val - 0.03)
plot_series(labels, values,
            title="BP Accuracy under different BP Schemes",
            outpath=os.path.join(args.outdir, "bp_accuracy_overall.png"),
            ylim_min=ymin, ylim_max=1.0)

# 2) Per-workload plots
for wl, g in acc_df.groupby('workload'):
    g2 = g.groupby('predictor')['accuracy_committed'].median().reset_index().sort_values('accuracy_committed')
    labels = g2['predictor'].tolist()
    values = g2['accuracy_committed'].tolist()
    if not values:
        continue
    min_val = min(values)
    ymin = max(0.0, min_val - 0.03)
    fname = f"bp_accuracy_{wl}.png".replace('/','_')
    plot_series(labels, values,
                title=f"BP Accuracy — workload: {wl}",
                outpath=os.path.join(args.outdir, fname),
                ylim_min=ymin, ylim_max=1.0)

print("All done. Plots in", args.outdir)