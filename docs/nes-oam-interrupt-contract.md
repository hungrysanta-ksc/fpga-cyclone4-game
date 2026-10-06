# Actual OAM DMA interrupt retention contract

SPDX-License-Identifier: MIT.

Candidate NES-P2-OAM-INTERRUPT-016 reuses the unchanged NES-P2-RDY-014 implementation.
The original NROM diagnostic disables rendering and APU/DMC, initializes two RAM pages,
and issues24 actual $4014 writes. The source pages alternate02/03; OAM starts00/01/FC/FF
are assigned to none/IRQ/NMI/both modes. These are deliberately coupled parameters,
not a full Cartesian product of page/start/mode. Each mode and arrival position covers
both 513/514-cycle DMA halt phases. Padding is part of the generated ROM and manifest.

The bench forces only mapper_irq and nmi. It never forces pause_cpu, DmaController state,
bus grant, or DMA data. IRQ remains high until the handler writes RAM2. NMI is high for
one cpu_ce sample, at cycle1/256/512 after the trigger. Cycle512 is near the end, not the
last halted cycle. The first sample is set before cpu_ce on the preceding falling edge.

Observation contracts:
- dma-bus.tsv: cart_ce samples tick/effective address/read/data/case/CPU address/read/pause/DMA/put.
- pins.tsv: cpu_ce samples tick/case/step/IRQ/NMI/pause/CPU address/read/data/put.
- cart_ce and cpu_ce differ by2 master ticks; consecutive CPU samples differ by12.
- oam.tsv: E records completion and OAMADDR, I records handler counts, O records256 physical OAM bytes.
- A case ends at its CPU write to RAM$20. RAM0 may still identify that case during the next setup;
  observations after completion must not be counted as its handler activity.

The verifier requires exactly256 source reads and256 $2004 writes in order, correct
CPU read hold and513/514-cycle pause, independent deterministic source bytes, physical
OAM wrapping and attribute maskE3, one post-DMA INC$10, and sequential completion1..24.
It checks injected pin waveforms against case metadata, IRQ acknowledgements, no service
during DMA, one vector per requested interrupt, NMI-before-IRQ for simultaneous inputs,
vector high bytes, stacked return PC/status/A, RTI pops, and handler increments.
The INC completes before interrupt service in these cases; its following PC is stacked.
Exact observed interrupt cycles are retained but are not an independently calibrated
cycle-accurate IRQ/NMI latency oracle. No Mesen runtime injected-pin comparison is claimed.

Twelve corruption probes must reject modified data, address, tick, pause, OAM, IRQ, NMI,
vector, stack, handler snapshot, resumed INC, and truncated observations. A simulator exit0
is insufficient: require the explicit PASS marker, no Fatal/Error, zero period/unknown counts,
and verifier PASS. Existing full-core Questa warnings42 remain.

Reproduce with fresh absolute ASCII output paths and the existing FLOAT workflow:

```powershell
& $PY -B -X utf8 tools/build_nes_oam_interrupt.py --out $ROM
& ./tools/run_nes_rdy.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out $RTL -Diagnostic $ROM -Testbench tests/nes-functional/oam_interrupt_tb.sv
& $PY -B -X utf8 tools/verify_nes_oam_interrupt.py --rom $ROM --rtl $RTL --out $REPORT
```

Use the absolute existing FLOAT wrapper and installed Questa paths in AGENTS.md;
see questa-execution.md. No new license, recurring smoke test, global service/environment
change, or inherited uncounted license is needed. Do not copy license-route.local.json,
server logs or licensed runtime directories into evidence. Generated adapted upstream HDL
and diagnostic ROMs remain local ignored evidence; upstream source and individual license
holds are unchanged. Main GBC and shared MCU/FPGA source are not modified.

Initial ROM/RTL01 and final02, initial builder/verifier, failed verifier report, and the
initial-run coverage rejection are retained under analysis/local-oam-interrupt-016.
The predecessor manifest was verified before snapshotting its mutable status files.
Full-core regression results from014 and runtime Mesen comparison from015 are historical
preserved evidence, not fresh tests in016. DMC/OAM contention is the next bounded gate;
this does not establish full NES, SMB3, NES-to-SNES integration, fit/STA or hardware readiness.
