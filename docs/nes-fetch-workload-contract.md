# R2 causal fetch analysis contract019

SPDX-License-Identifier: MIT.

Candidate NES-R2-FETCH-WORKLOAD-019. Core implementation014 unchanged.
Read-only input: original009 Mapper4 diagnostic rerun on014 plus pinned Mesen010 reference.
The input verifier is called as a function; historical verification files are not overwritten.

## Reproduce
From this independent checkout, run with Python3 and use a fresh output directory:

~~~powershell
python -B tools/analyze_nes_fetch_workload.py --run analysis/local-rdy-014/integrated-01 --reference analysis/local-mmc3-irq-phase-010/mesen-01 --rom analysis/local-mmc3-integrated-009/rom-02 --out <fresh-output>
python -B tools/test_nes_fetch_workload.py --run analysis/local-rdy-014/integrated-01 --out <test-result.json>
~~~

No Questa, license smoke test, Quartus or game ROM is needed. Existing raw evidence remains ignored.
The ROM is the project's original 64KiB PRG / 16KiB CHR diagnostic, SHA256
8b380949760320c993fd35a2a48af29a6afe2516f353d048f65f49fa1dd38ba9.

## Input and event boundary
fetch.tsv fields: frame,line,cycle,master_tick,virtual_addr,physical_addr,value,table.
Normalize line511 to -1 and RTL cycle to Mesen dot=cycle-1. CHR physical tag=0x200000.
Trace covers BG pattern latches only. Visible-pixel classification uses the existing audited zero-scroll coordinate rule.
All 65,552 BG latches and 61,440 pixel-referenced reads are audited against original ROM, oracle and Mesen.
The four 256x240 indexed frames contain245,760 unique source pixel observations.

## Demand model
Physical immutable CHR tile key=floor((physical_addr-0x200000)/16); generation remains0.
Start with an empty cache at the first captured event, not at ROM startup.
LRU fill requests occur only at the current fetch. A miss reads the whole16-byte immutable ROM tile.
Capacities128/256/512/1024tiles refer to logical source payload, not allocated FPGA M9Ks or proven SNES VRAM slots.
The observed union is retrospective, never a preload selection oracle.
The whole16KiB ROM is known at load time and could motivate a separate startup preload experiment.
A pixel-only trace changes replacement history and is NOT necessarily a lower bound for a fixed LRU policy.

Window summaries count requests in (right-width,right] NES master ticks.
1364ticks corresponds to341PPU dots in this captured4master/dot model;357368 is a rolling width, not every frame's exact period.
Per-line grouping and rolling windows are distinct. Do not convert burst size into FIFO depth without a service schedule.
Mapper R0/R1 declaration times are observed CPU writes, not guaranteed fetch deadlines or SNES blank timing.
NES master ticks and SNES DMA clocks must remain separate domains.

## Replay and validation
The replay inserts each demanded tile instantly, verifies each read byte and reconstructs every240-line source frame.
It is a zero-latency software integrity check. It does not execute SNES code, serialize compact packets, account for tile conversion/roles,
palette/map/OAM/headers, or prove tile residency at a physical display deadline.
An independent reuse-distance oracle checks9,837 short streams, plus rolling-window boundaries, actual-prefix causality and9 corruption cases.
Four capacities replay the same245,760 pixels each;983,040 comparisons are not983,040 different captured pixels.

## Exit limits and next evidence
R2 remains partial. Queue size, external memory service, source/consumer phase and display240 policy remain open.
Prior239-line raw blank30008SNESclocks at8clocks/byte is comparison evidence only; no crop is approved.
Broaden original Mapper4 workloads to more banks, scroll, sprites and intra-frame changes.
Next build an actual trace-to-packet/SNES replay with explicit buffering, deadline accounting and all240source rows accounted for.
