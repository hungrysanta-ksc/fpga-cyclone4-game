# Restricted streaming NCR1 encoder046

SPDX-License-Identifier: MIT.

`nes_ncr1_encoder.sv` converts chronological BG pattern fetch metadata into the existing2008-byte NCR1 packet in synthesizable RTL. It exposes the045 completed-source descriptor and memory-response interface;045 then copies the immutable packet into044 transport. No file, golden framebuffer or future event is visible inside this RTL.

## Required source contract

All inputs are synchronous to queue_clk. Pulse frame_start at least one clock before the first BG event, only when frame_ready is high. Input frame_id1..4 is the existing bounded NCR1 header label, not the16-bit queue sequence. fine_x0..7, chr_32k and converted64-bit SNES palette are latched at start. Only fineX0/1 is exercised. Do not infer support for arbitrary games or a universal display policy.

The upstream mode monitor must keep supported_mode true only for immutable16/32KiB CHR, BG-only rendering, the supported BG table/nametable, no coarse/vertical scrolling or active PPU/CHR/palette changes. bg_palette must carry the actual BG attribute palette and must be0. Palette conversion and physical-address resolution must come from the real PPU/mapper path. The live tap, BG-vs-sprite/dummy classifier and mode monitor have NOT been connected in046. These are required inputs, not checks that this block can perform on an unseen PPU. The replay supplies metadata from the original controlled021 workloads and verifies complete decoded frames against their recorded references.

Each bg_valid event carries signed line -1..239, dot, resolved CHR byte address, attribute palette and32-bit tick. Full BG pattern cadence is enforced:68 plane events per line,241 lines,16388 total. Expected dots are5/7 through253/255 then325/327 and333/335. Ticks strictly increase within a frame. Invalid or missing events fail instead of making a partial packet. A missing tail is detected by frame_end, so a live source must also supply a bounded frame-end event; a completely stalled source has no independent timeout in046.

Useful fetches map prefetch columns0/1 and current-line columns2..32 into240 rows. Every990 tile cell must have the same physical tile across8 rows and both planes; row/plane bits and one16KiB CHR window are checked. The result is15840 useful events. First-row/plane0 writes cell RAM; all other useful samples compare against it. Header release_tick is the last useful fetch timestamp, matching025; descriptor availability is later, after full raw cadence and frame_end, not retroactively at release_tick. Wait at least one empty cycle after final input pipeline work before frame_end; the test uses three.

## Ownership and memory

Only one source packet buffer exists. It is active during capture and frozen from frame_end through descriptor handshake and045 done. New frame_start during capture or ownership fails; the block never quietly overwrites, discards or stalls the NES. Actual arrival/consumer speed and any additional buffering must be validated before continuous live integration. The eight timed reference frames did not overrun under the tested clocks/service/consumer; this is not a general pacing guarantee.

Descriptor base0,length2008,epoch from common reset and sequence starting1 connect directly to045. Source sequence advances only after done;65535 exhausts until reset (wrap boundary not exercised here). Packet read requests are accepted only after descriptor ownership transfer. One request is pending at a time; address/epoch are echoed, wrong epoch/range yields service error. The registered response remains valid until ready. Memory is an on-chip tile table, not a physical SRAM/SDRAM controller.045/044 require common generation reset; capture/requests/responses gate off while reset is asserted. RAM is not cleared: a complete new frame overwrites all990 cells before publication.

Capture comparisons and packet reads cannot run together. Their read addresses share one port, with990×11bits in2M9K. The RTL never reads old data on a first-row write; captured cells are read on later clocks. Quartus still emits276027 for its inferred dual-port RAM representation. The warning is retained. Functional exported-netlist checks cover the exercised behavior without claiming physical read/write timing or SDF signoff.

Sticky errors until reset:01 frame-start/ownership overlap,02 unsupported mode/header frame ID,03 raw cadence,04 nonmonotonic tick,05 row/plane/CHR range,06 attribute palette,07 in-cell tile change,08 mixed window,09 incomplete/invalid frame-end,0A unexpected source completion,0B event outside a frame or simultaneous start/end/event. A failed frame never exposes a valid descriptor;045 may subsequently time out if an already owned source faults, requiring common reset.

## Reproduction and executed coverage

Use tools/run_nes_ncr1_encoder.ps1 with existing Python/QuestaBin/FloatWrapper and fresh ASCII Out. It reconstructs the eight historical025 golden packets from021 source traces and independently decodes full reference frames. Actual event gaps are replayed with46.560846ns queue clock and11.904762ns host clock; no new NES emulator/core execution is claimed.

Final16-case RTL run:131104 timed positive fetches, eight reference frames, unsupported metadata/cadence/tiles/window/ownership tests, reset partial-frame rebuild;18072 exact output bytes through045/044 MMIO. Capture replay is causal at this interface; the testbench's golden packets are used only by the consumer comparison.

Use tools/nes_ncr1_encoder_resource.py for fresh standalone map/fit. Final672LE/292registers/2M9K/10890payload bits/118totalLAB/338virtual pins. This excludes CPU/PPU/APU,045/044 joint placement, actual pins/clocking and STA. Do not add separate LAB costs to032 as proof of joint feasibility.

To export the functional encoder netlist, add the following to the fitted producer.qsf and run quartus_eda producer in that directory (ASCII path):

    set_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"
    set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR gate -section_id eda_simulation
    set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation
    set_global_assignment -name EDA_GENERATE_FUNCTIONAL_NETLIST ON -section_id eda_simulation

Then tools/run_nes_ncr1_encoder_gate.ps1 additionally takes RtlRun and Netlist. It uses three compressed-arrival frames, including window0/1, frame IDs1/2 and fineX1.6024 bytes match with the exported encoder plus behavioral045/044. No SDF is applied. Vendor vopt-13162 warning is preserved; this is functional evidence, not timing signoff.

Original044 hardware package,045 source and all prior failures stay frozen.046 has no SD image. Next: real PPU event/mode binding, full NES+046+045+044 joint resource measurement, clock/arrival/lifecycle and actual SNES NCR1 consumer/display integration.
