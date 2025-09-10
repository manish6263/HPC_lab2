#!/usr/bin/env python3
"""
collect_stats_bp.py (updated)

Scan Stats_BP/*/stats.txt and extract branch & performance stats that match
the naming used in your gem5 outputs (e.g. simSeconds, simInsts,
system.cpu.branchPred.* etc).

Outputs: summary_for_plots_bp.csv
"""
import argparse, os, re, csv, sys
parser = argparse.ArgumentParser()
parser.add_argument("--src", default="Stats_BP", help="Source directory with run subfolders")
parser.add_argument("--out", default="summary_for_plots_bp.csv", help="Output CSV")
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()

# regex that matches lines like:
# name    12345    # comment
LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.:/\-]+(::[A-Za-z0-9_]+)?)\s+([-+0-9.eE]+)")

# candidate names (covers the names seen in your stats.txt)
CANDIDATES = {
    "sim_seconds": ["simSeconds", "sim_seconds", "simSeconds_total"],
    "sim_ticks": ["simTicks", "sim_ticks"],
    "sim_insts": ["simInsts", "sim_insts", "instructions", "sim_insts"],
    "ipc": ["system.cpu.ipc", "ipc"],
    # branch buckets (common names observed)
    "branch_lookups": ["system.cpu.branchPred.lookups_0::total", "system.cpu.branchPred.lookups::total", "branchPred.lookups::total", "branchPredicted", "branchLookups"],
    "branch_committed": ["system.cpu.branchPred.committed_0::total", "system.cpu.branchPred.committed::total", "branchCommitted", "branchPred.committed"],
    "branch_mispredicted": ["system.cpu.branchPred.mispredicted_0::total", "system.cpu.branchPred.mispredicted::total", "branchMispredicted", "branch_mispredicted"],
    "branch_mispredict_due_predictor": ["system.cpu.branchPred.mispredictDueToPredictor_0::total", "branchPred.mispredictDueToPredictor", "mispredictDueToPredictor"]
}

def parse_stats_file(path):
    stats = {}
    try:
        with open(path, "r") as fh:
            for ln in fh:
                m = LINE_RE.match(ln)
                if m:
                    key = m.group(1).strip()
                    val = m.group(3) if m.group(3) else m.group(4)
                    try:
                        stats[key] = float(m.group(3))
                    except:
                        # skip non-numeric
                        pass
    except Exception as e:
        if args.verbose: print("Failed to read", path, e)
    return stats

def find_best(stats, candidates):
    # exact match
    for cand in candidates:
        if cand in stats:
            return cand
    # lowercase exact
    low = {k.lower(): k for k in stats}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    # substring match
    for cand in candidates:
        lc = cand.lower()
        for k in stats:
            if lc in k.lower():
                return k
    return None

rows = []
if not os.path.isdir(args.src):
    print("Source dir not found:", args.src); sys.exit(1)

for root, dirs, files in os.walk(args.src):
    if "stats.txt" not in files:
        continue
    stats_path = os.path.join(root, "stats.txt")
    stats = parse_stats_file(stats_path)
    rec = {"run_dir": root, "stats_path": stats_path}

    # detect keys
    for field, candlist in CANDIDATES.items():
        found = find_best(stats, candlist)
        rec[field + "_key"] = found if found else ""
        rec[field] = stats.get(found) if found and found in stats else None

    # some metadata from folder name
    run_folder = os.path.basename(root.rstrip("/"))
    rec["run_folder"] = run_folder
    toks = re.split(r'[_\-]', run_folder)
    rec["cpu"] = toks[0] if len(toks) > 0 else ""
    rec["predictor"] = toks[1] if len(toks) > 1 else ""
    rec["workload"] = "_".join(toks[2:]) if len(toks) > 2 else os.path.basename(os.path.dirname(root))

    # derived metrics
    try:
        if rec.get("ipc") is None and rec.get("sim_insts") and rec.get("sim_seconds"):
            rec["IPC_calc"] = float(rec["sim_insts"]) / (rec["sim_seconds"] * (rec.get("sim_ticks")/rec.get("sim_seconds") if rec.get("sim_seconds") else 1.0))
        else:
            rec["IPC_calc"] = rec.get("ipc")
    except Exception:
        rec["IPC_calc"] = rec.get("ipc")

    # misprediction rates
    try:
        committed = rec.get("branch_committed")
        mis = rec.get("branch_mispredicted")
        lookups = rec.get("branch_lookups")
        if mis is not None and committed:
            rec["mispred_rate_committed"] = float(mis) / float(committed) if committed else None
        else:
            rec["mispred_rate_committed"] = None
        if mis is not None and lookups:
            rec["mispred_rate_lookup"] = float(mis) / float(lookups) if lookups else None
        else:
            rec["mispred_rate_lookup"] = None
        if mis is not None and rec.get("sim_insts"):
            rec["mispred_per_kinst"] = float(mis) / (float(rec["sim_insts"]) / 1000.0)
        else:
            rec["mispred_per_kinst"] = None
    except Exception:
        rec["mispred_rate_committed"] = rec["mispred_rate_lookup"] = rec["mispred_per_kinst"] = None

    rows.append(rec)

# write CSV
outcols = [
    "run_dir","run_folder","cpu","predictor","workload","stats_path",
    "sim_seconds_key","sim_seconds","sim_ticks_key","sim_ticks","sim_insts_key","sim_insts",
    "ipc_key","ipc","IPC_calc",
    "branch_lookups_key","branch_lookups","branch_committed_key","branch_committed",
    "branch_mispredicted_key","branch_mispredicted","branch_mispredict_due_predictor_key","branch_mispredict_due_predictor",
    "mispred_rate_committed","mispred_rate_lookup","mispred_per_kinst"
]
with open(args.out, "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=outcols)
    writer.writeheader()
    for r in rows:
        out = {k: r.get(k, "") for k in outcols}
        writer.writerow(out)

print(f"Wrote {args.out} with {len(rows)} rows")
if args.verbose:
    for r in rows[:5]:
        print(r)
