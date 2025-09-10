# -*- coding: utf-8 -*-
# Copyright (c) 2015 Jason Power
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" This file creates a single CPU and a two-level cache system.
This script takes a single parameter which specifies a binary to execute.
If none is provided it executes 'hello' by default (mostly used for testing)

See Part 1, Chapter 3: Adding cache to the configuration script in the
learning_gem5 book for more information about this script.
This file exports options for the L1 I/D and L2 cache sizes.

IMPORTANT: If you modify this file, it's likely that the Learning gem5 book
           also needs to be updated. For now, email Jason <power.jg@gmail.com>

"""

# import the m5 (gem5) library created when gem5 is built
import m5
import os
import argparse

# import all of the SimObjects
from m5.objects import *
from m5.objects.BranchPredictor import *

# import our cache definitions
from caches import *

# -----------------------------
# Argument parsing (replaces SimpleOpts)
# -----------------------------
parser = argparse.ArgumentParser(description="gem5 O3CPU with Branch Predictors")

# Binary to execute
thispath = os.path.dirname(os.path.realpath(__file__))
default_binary = os.path.join(thispath, "Binaries/", "mm")

parser.add_argument("binary", nargs="?", default=default_binary,
                    help="Path to workload binary (default: Binaries/mm)")

# CPU type
parser.add_argument("--cpu_type", default="O3CPU",
                    help="CPU type (default: O3CPU)")

# Branch Predictor Type
parser.add_argument("--bp_type", default="LocalBP",
                    help="Branch Prediction Type (default: LocalBP)")

# Max instructions (ROI control)
parser.add_argument("--maxinsts", type=int, default=None,
                    help="Maximum number of instructions to simulate")

# Cache sizes (optional, matches SimpleOpts style)
parser.add_argument("--l1i_size", default="16kB", help="L1 instruction cache size")
parser.add_argument("--l1d_size", default="64kB", help="L1 data cache size")
parser.add_argument("--l2_size", default="256kB", help="L2 cache size")

args = parser.parse_args()

# -----------------------------
# System configuration
# -----------------------------
system = System()

# Clock and voltage
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Memory
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("1024MB")]

# CPU
system.cpu = X86O3CPU()

# L1 caches
system.cpu.icache = L1ICache(args)
system.cpu.dcache = L1DCache(args)
system.cpu.icache.connectCPU(system.cpu)
system.cpu.dcache.connectCPU(system.cpu)

# L2 bus
system.l2bus = L2XBar()
system.cpu.icache.connectBus(system.l2bus)
system.cpu.dcache.connectBus(system.l2bus)

# L2 cache
system.l2cache = L2Cache(args)
system.l2cache.connectCPUSideBus(system.l2bus)

# Main memory bus
system.membus = SystemXBar()
system.l2cache.connectMemSideBus(system.membus)

# Interrupts
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# System port
system.system_port = system.membus.cpu_side_ports

# Memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# -----------------------------
# Branch Predictor Setup
# -----------------------------
if args.bp_type == "LocalBP":
    system.cpu.branchPred = LocalBP()
elif args.bp_type == "TournamentBP":
    system.cpu.branchPred = TournamentBP()
elif args.bp_type == "BiModeBP":
    system.cpu.branchPred = BiModeBP()
elif args.bp_type == "TAGE":
    system.cpu.branchPred = TAGE()
elif args.bp_type == "LTAGE":
    system.cpu.branchPred = LTAGE()
elif args.bp_type == "GShareBP":
    system.cpu.branchPred = GShareBP(historyBits=12, initCounter=1)
elif args.bp_type == "PerceptronBP":
    try:
        system.cpu.branchPred = PerceptronBP()
    except:
        print("Warning: PerceptronBP not available in this gem5 build.")
        system.cpu.branchPred = LocalBP()

# -----------------------------
# Workload setup
# -----------------------------
system.workload = SEWorkload.init_compatible(args.binary)
process = Process()
process.cmd = [args.binary]
system.cpu.workload = process
system.cpu.createThreads()

# Limit max instructions if specified
if args.maxinsts:
    system.cpu.max_insts_any_thread = args.maxinsts

# -----------------------------
# Root and Simulation
# -----------------------------
root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print("Exiting @ tick %i because %s" % (m5.curTick(), exit_event.getCause()))
