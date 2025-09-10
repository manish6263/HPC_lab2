#!/usr/bin/env python3
"""
compute_and_plot_accuracy.py

Reads: summary_for_plots_bp.csv (or branch_analysis/summary_median_bp.csv)
Outputs:
  - branch_analysis/plots/<workload>_accuracy_bar.png
  - branch_analysis/plots/<workload>_predictor_accuracy_bar.png
  - branch_analysis/plots/<workload>_mispredict_breakdown.png
  - branch_analysis/accuracy_section.md  (markdown fragment with plot links + a small table)
  - branch_analysis/accuracy_summary.csv (per-workload, per-predictor accuracy numbers)
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

CSV_CANDIDATES = [
    "branch_analysis/summary_median_bp.csv",
    "summary_median_bp.csv",
    "branch_analysis/summary_median.csv",
    "summary_for_plots_bp.csv",
    "summary_for_plots.csv"
]

csv_path = None
for p in CSV_CANDIDATES:
    if os.path.exists(p):
        csv_path = p
        break

if csv_path is None:
    raise SystemExit("No summary CSV found. Run collect/median scripts first.")

outdir = "branch_analysis"
plots = os.path.join(outdir, "plots")
os.makedirs(plots, exist_ok=True)

print("Reading:", csv_path)
df = pd.read_csv(csv_path)

# Try to use median columns if present, otherwise raw columns
# Try common column names produced by earlier scripts
def try_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

# Keys we expect or fallback names
branch_committed_col = try_col(df, ["branch_committed", "branch_committed_median", "system.cpu.branchPred.committed_0::total", "branch_committed_median"])
branch_mispred_col = try_col(df, ["branch_mispredicted", "branch_mispredicted_median", "system.cpu.branchPred.mispredicted_0::total", "branch_mispredicted_median"])
branch_pred_by_pred_col = try_col(df, ["branch_mispredict_due_predictor", "branch_mispredictDueToPredictor", "branch_mispredict_due_predictor_median","branch_mispredictDueToPredictor_0::total"])
ipc_col = try_col(df, ["ipc","ipc_median","system.cpu.ipc","IPC_calc","IPC"])

# If we only have the raw CSV of runs (not medians), compute medians grouped by workload,predictor
if not ("_median" in (branch_committed_col or "") or "median" in (branch_committed_col or "")):
    # We'll compute medians for the grouping of workload/predictor
    need_group = True
else:
    need_group = False

if need_group:
    # normalize column names if present in raw CSV
    # map common raw names to new names
    mapping = {}
    if "branch_committed_key" in df.columns and "branch_committed" in df.columns:
        mapping["branch_committed"] = "branch_committed"
    # fallback: find columns with committed pattern
    for c in df.columns:
        if "committed" in c.lower() and "branch" in c.lower():
            branch_committed_col = c
        if "mispred" in c.lower() and "due" in c.lower():
            branch_pred_by_pred_col = c
        if "mispred" in c.lower() and "mispredicted" in c.lower():
            branch_mispred_col = c
    # required: branch_mispred_col and branch_committed_col
    if branch_committed_col is None or branch_mispred_col is None:
        print("Warning: couldn't autodefine branch_committed or branch_mispred columns. Available cols:", df.columns.tolist())

    # group and compute median
    grouped = df.groupby(['workload','predictor']).agg({
        branch_committed_col: 'median' if branch_committed_col else 'count',
        branch_mispred_col: 'median' if branch_mispred_col else 'count'
    }).reset_index()
    # try include predictor-caused if present
    if branch_pred_by_pred_col:
        gp2 = df.groupby(['workload','predictor']).agg({branch_pred_by_pred_col:'median'}).reset_index()
        grouped = grouped.merge(gp2, on=['workload','predictor'], how='left')
    # rename to consistent names
    rename_map = {branch_committed_col: 'branch_committed_median', branch_mispred_col: 'branch_mispredicted_median'}
    if branch_pred_by_pred_col:
        rename_map[branch_pred_by_pred_col] = 'branch_mispredict_due_predictor_median'
    grouped = grouped.rename(columns=rename_map)
    # also extract median IPC if present in original df
    if ipc_col in df.columns:
        ipcm = df.groupby(['workload','predictor']).agg({ipc_col:'median'}).reset_index().rename(columns={ipc_col:'ipc_median'})
        grouped = grouped.merge(ipcm, on=['workload','predictor'], how='left')
    summary = grouped.copy()
else:
    # Already median table
    # normalize column names to our canonical names
    summary = df.copy()
    # rename if needed
    for c in df.columns:
        if 'committed' in c and 'median' in c:
            branch_committed_col = c
        if 'mispred' in c and 'median' in c:
            branch_mispred_col = c
        if 'predictor' in c and 'predictor' != c:
            pass  # keep predictor

    # make sure required cols exist
    # if branch_pred_by_pred_col exists, fine, else will be NaN
    # unify column names to canonical names for later code
    # create canonical columns if needed
    if branch_committed_col and branch_committed_col != 'branch_committed_median':
        summary = summary.rename(columns={branch_committed_col:'branch_committed_median'})
    if branch_mispred_col and branch_mispred_col != 'branch_mispredicted_median':
        summary = summary.rename(columns={branch_mispred_col:'branch_mispredicted_median'})
    if branch_pred_by_pred_col and branch_pred_by_pred_col != 'branch_mispredict_due_predictor_median':
        summary = summary.rename(columns={branch_pred_by_pred_col:'branch_mispredict_due_predictor_median'})
    if ipc_col and ipc_col != 'ipc_median':
        summary = summary.rename(columns={ipc_col:'ipc_median'})

# Ensure numeric
for col in ['branch_committed_median','branch_mispredicted_median','branch_mispredict_due_predictor_median','ipc_median']:
    if col in summary.columns:
        summary[col] = pd.to_numeric(summary[col], errors='coerce')

# Compute accuracy metrics
def safe_div(a,b):
    try:
        a = float(a); b = float(b)
        return a/b if b != 0 else np.nan
    except:
        return np.nan

rows = []
for _, r in summary.iterrows():
    wl = r['workload']
    pred = r['predictor']
    committed = r.get('branch_committed_median', np.nan)
    mispred = r.get('branch_mispredicted_median', np.nan)
    mispred_by_pred = r.get('branch_mispredict_due_predictor_median', np.nan)
    ipc = r.get('ipc_median', np.nan)
    acc_committed = 1.0 - safe_div(mispred, committed)
    acc_predictor = 1.0 - safe_div(mispred_by_pred, committed)
    mpki = None
    if 'simInsts' in r.index and not pd.isna(r['simInsts']):
        mpki = safe_div(mispred, r['simInsts']) * 1000.0
    rows.append({
        'workload': wl,
        'predictor': pred,
        'branch_committed_median': committed,
        'branch_mispredicted_median': mispred,
        'branch_mispredict_due_predictor_median': mispred_by_pred,
        'ipc_median': ipc,
        'accuracy_committed': acc_committed,
        'accuracy_predictor': acc_predictor,
        'mpki_est': mpki
    })

acc_df = pd.DataFrame(rows)
acc_csv = os.path.join(outdir, "accuracy_summary.csv")
acc_df.to_csv(acc_csv, index=False)
print("Saved accuracy CSV:", acc_csv)

# Plot per-workload accuracy bars
workloads = sorted(acc_df['workload'].unique())
for wl in workloads:
    sub = acc_df[acc_df['workload']==wl].sort_values('accuracy_committed', ascending=False)
    if sub.empty:
        continue
    preds = sub['predictor'].tolist()
    x = range(len(preds))

    # accuracy_committed bar
    fig, ax = plt.subplots(figsize=(8,4.5))
    y = sub['accuracy_committed'].values
    ax.bar(x, y)
    ax.set_xticks(x); ax.set_xticklabels(preds, rotation=30, ha='right')
    ax.set_ylim(0,1.0)
    ax.set_ylabel("Committed-branch accuracy")
    ax.set_title(f"{wl}: committed-branch accuracy (median)")
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    fname = os.path.join(plots, f"{wl}_accuracy_bar.png")
    fig.savefig(fname, bbox_inches='tight', dpi=200)
    plt.close(fig)
    print("Saved", fname)

    # predictor-attributed accuracy bar
    if not sub['accuracy_predictor'].isna().all():
        fig, ax = plt.subplots(figsize=(8,4.5))
        y2 = sub['accuracy_predictor'].fillna(0).values
        ax.bar(x, y2)
        ax.set_xticks(x); ax.set_xticklabels(preds, rotation=30, ha='right')
        ax.set_ylim(0,1.0)
        ax.set_ylabel("Predictor-attributed accuracy (1 - mispred_by_predictor/committed)")
        ax.set_title(f"{wl}: predictor-attributed accuracy (median)")
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        fname2 = os.path.join(plots, f"{wl}_predictor_accuracy_bar.png")
        fig.savefig(fname2, bbox_inches='tight', dpi=200)
        plt.close(fig)
        print("Saved", fname2)

    # stacked breakdown of mispred_by_predictor vs others (median)
    if 'branch_mispredict_due_predictor_median' in sub.columns and not sub['branch_mispredict_due_predictor_median'].isna().all():
        pred_m = sub['branch_mispredict_due_predictor_median'].fillna(0).values
        total_m = sub['branch_mispredicted_median'].fillna(0).values
        other = np.maximum(total_m - pred_m, 0)
        fig, ax = plt.subplots(figsize=(8,4.5))
        ax.bar(x, pred_m, label='predictor-caused (median)')
        ax.bar(x, other, bottom=pred_m, label='other-causes (median)')
        ax.set_xticks(x); ax.set_xticklabels(preds, rotation=30, ha='right')
        ax.set_ylabel("Number of mispredicted branches (median)")
        ax.set_title(f"{wl}: mispredict breakdown (median)")
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        fname3 = os.path.join(plots, f"{wl}_mispred_breakdown_median.png")
        fig.savefig(fname3, bbox_inches='tight', dpi=200)
        plt.close(fig)
        print("Saved", fname3)

# write a small markdown fragment summarizing accuracy
md_lines = []
md_lines.append("# Accuracy summary and plots")
for wl in workloads:
    md_lines.append(f"## Workload: `{wl}`")
    md_lines.append(f"![Accuracy]({os.path.join('plots', f'{wl}_accuracy_bar.png')})")
    pred_img = os.path.join('plots', f'{wl}_predictor_accuracy_bar.png')
    bd_img = os.path.join('plots', f'{wl}_mispred_breakdown_median.png')
    if os.path.exists(os.path.join(outdir,pred_img)):
        md_lines.append(f"![Predictor accuracy]({pred_img})")
    if os.path.exists(os.path.join(outdir,bd_img)):
        md_lines.append(f"![Breakdown]({bd_img})")
    md_lines.append("")

md_path = os.path.join(outdir, "accuracy_section.md")
with open(md_path, "w") as fh:
    fh.write("\n".join(md_lines))
print("Wrote markdown fragment:", md_path)
print("All done. Plots in", plots)
