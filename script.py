import os

# Path to the gem5 binary (adjust if different on your system)
gem5_path = "build/X86/gem5.opt"

# CPU model(s) to test
cpu_types = ["O3CPU"]

# Branch predictors to test
bp_types = [
    "BiModeBP",
    "LocalBP",
    "TournamentBP",
    "TAGE",
    "LTAGE",
    "GShareBP",
    "PerceptronBP",
]

# Workloads to run (update paths as needed)
workloads = [
    "Binaries/mm",   # compute-heavy
    "Binaries/branchy_test",   # branch-heavy
    "Binaries/fft.1",            # another compute-heavy
]

# Max instructions per run (ROI)
max_insts = 100_000_000   # 100M

# Loop over configurations
for cpu_type in cpu_types:
    for bp_type in bp_types:
        for workload in workloads:
            # Extract workload name without path
            workload_name = os.path.basename(workload)

            # Create custom stats directory
            custom_stats_dir = f"./Stats_BP/{cpu_type}_{bp_type}_{workload_name}"
            os.makedirs(custom_stats_dir, exist_ok=True)

            # Construct the gem5 command
            cmd = [
                gem5_path,
                "-d", custom_stats_dir,
                "config.py",
                f"--cpu_type={cpu_type}",
                f"--bp_type={bp_type}",
                # f"--binary={workload}",
                workload,
                f"--maxinsts={max_insts}"
            ]

            # Print command for debugging
            print("Running:", " ".join(cmd))

            # Run the command
            os.system(" ".join(cmd))
