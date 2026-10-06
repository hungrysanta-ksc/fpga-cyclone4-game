# SNES pin frontend031 contract
SPDX-License-Identifier: MIT.

The original nes_transport integrates031 nes_packet_queue_ram/nes_packet_cdc_ram, unchanged029 nes_host_stage,
and new nes_snes_frontend. It has logical pin ports, not a full board shell.
No physical pin locations, board PLL, transceiver pad timing, renderer SRAM/MCU loader, SNES program or producer is included.

## Experimental address contract
Only bank00 offsets6000..6009 access029 registers. No80-bank mirror.
Bank00:600A reads031 sticky frontend flags (low4bits); writes do nothing.
Payload window40:8000..8BFF requires active-low ROMSEL and ascending one-byte accesses from8000.
This is provisional NES-image-local decoding, not an installed firmware ABI. GBC mapping is unchanged.
Caller sets epoch/sequence, starts acquire through6000=1, pollsREADY, reads declared length at6006/7,
reads the payload consecutively, then commits through6000=2 after all bytes.
No fixed-address DMA mode is supported. Packet reads increment across the payload window.
All reads must complete before their data is used; no SNES wait pin or retry mechanism is provided.

Writes: two sampled stages align address/data with /WR, last low bundle is retained, one029 write pulse after synchronized /WR end.
Reads: synchronized /RD falling edge creates one stage/register request, registered result is held until /RD ends.
Held /RD must never pop multiple bytes. Raw /RD deassertion, /WR assertion, reset, address mismatch or payload ROMSEL deassertion immediately disables read drive in RTL.
Databus DIR is output only while driving a qualified read. Selected writes enable the input transceiver direction.
A full pad wrapper must put SNES_DATA in high impedance whenever read drive is false.

Frontend flags:bit0 interrupted/address/ROMSEL-changed read,bit1 bad payload address/notREADY,bit2 read/write conflict,
bit3 stage supplied no response (e.g. read past declared packet length).
Flags latch until common reset. Payload drive is inhibited after a flag; status/register reads remain available.
Register writes are suppressed after a frontend flag. A partial read may already consume one staged byte;
do not retry blindly or commit it. Common reset of frontend/stage/CDC/queue with a fresh epoch is recovery.
Returning to the old address or reasserting ROMSEL after a sampled abort must not resurrect old payload drive.

## Tested timing model, not electrical specification
3 synthetic queue/host periods:46.560846/11.904762ns,20/10ns,46.560846/20ns.
Tests keep address/data20ns before strobe and20ns after, low read/write180ns (first held read600ns), idle gap100ns.
The model samples bus data after output enable and verifies stability until release.
All observed response assertions are bounded by5 host periods plus1ns observation granularity.
This does not establish SNES external setup/hold, minimum legal pulse widths, propagation delay, metastability MTBF or an exhaustive phase sweep.
Subminimum25ns pulse can be missed entirely; if it consumes a byte, it must latch abort. It must not drive after release.
Host clock must run throughout bus service. Board PLL unlock/clock loss must assert common reset and disable pads;
this frontend alone does not detect a stopped host clock. A too-short high gap can defeat edge detection.
No independent endpoint reset, asynchronous read-address re-timing proof orphysical CDC constraints are supplied.

## RAM variant
Original027 two-dimensional memory plus reset/default output logic did not infer a RAM in Quartus.
031 uses flattened6144x8 synchronous read/write ports and masks invalid output with c_data_valid.
Control/ownership/protocol are unchanged; original027 and028 source files remain preserved.
A cycle-by-cycle four-state output comparator ran every clock of original027's14-case test, including concurrent accesses and ring reuse.
This is bounded executable equivalence evidence, not formal equivalence for arbitrary inputs.
031 CDC variant changes only module/queue type to use the RAM variant.
Actual fit allocated8M9Ks to6144B queue and4M9Ks to3072B stage (12total), not the arithmetic9blocks.

## Reproduction
Run tools/run_nes_snes_frontend.ps1 using the approved FLOAT wrapper and a fresh ASCII output.
It runs queue equivalence plus3 frontend configurations. Preserve logs, require PASS and no Fatal/Error.
tools/nes_transport_resource.py --out FRESH --quartus-bin INSTALLED runs map/fit of the same nes_transport wrapper.
tools/verify_nes_snes_frontend.py --run RUN --resource RESOURCE --out RESULT checks sources, all accepted pin bytes and area.
Resource project uses133virtual pins and2unassigned clock pins, seed1,EP4CE15F17C8.
Only area/packing is measured; no STA was run and this project is not hardware eligible.
