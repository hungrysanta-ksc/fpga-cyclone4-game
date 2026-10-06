# Actual archived NES trace to SNES replay020

SPDX-License-Identifier: MIT.

This is a bounded offline transport fixture, not a live bridge or game renderer.
NES implementation014 and original Mapper4 diagnostic bytes remain unchanged.

## Packet and CHR
Header little-endian struct <4sBBHHHI: magic NTR0, version1, source frame1..4,
width256,height240,map bytes1920,release NES master tick.
Body:960little-endian16bit physical tile indices, followed by4RGB555 colors(8B).
Total1944B; ROM storage stride2048B; no future observed-union preload.
The source16KiB CHR ROM is converted in full from NES plane-separated rows to SNES interleaved2bpp rows,
then DMA-loaded once in startup forced blank. VRAM words2000..3fff store the1024tiles.
BG1 Mode0 map pages occupy word0 and400;1920B DMA covers30rows. Palette0 uses4distinct colors.
RGB555 quantization is explicit in each build manifest; indexed source symbols remain distinct.

The encoder only accepts complete zero-scroll BG frames with one physical tile per8x8cell.
No sprite, fine scroll, CHR RAM generation, palette event, emphasis or arbitrary mid-frame tile change support.
The packet release tick is the last pixel-referenced captured fetch; it is metadata, not an emulated producer handshake.

## Runtime and observation
65816 code executes from WRAM, reads only the current packet, waits for VBlank, validates its first12header bytes,
fills the inactive map, updates8Bpalette and commits map selection.
The native SNES CPU performs DMA. Read-only Lua captures real framebuffer and phase/DMA/register writes.
Startup includes overscan settling. Four normal frames are consecutive; no normal repeat/forced blank is inserted.
Complete packets are already in immutable ROM. No packet creation, SRAM service, CDC or producer clock delay is modeled.
Observed VBlank margin is consumer-only. No queue depth is inferred from the2048B storage stride.

Two independent runs use vertical viewport offsets0/1, capturing source rows0..238 and1..239.
Their overlap and union are audited. All240source rows are represented, but only239are visible simultaneously.
This is not approval of a product crop, alternating viewport, slowed playback or color policy.

## Reproduce
Use the existing isolated runtime described in ../snes/video_probe/README.md.
Run from the checkout; use a fresh ASCII absolute capture path for each run:

~~~powershell
python -B tools/build_nes_trace_replay.py --run analysis/local-rdy-014/integrated-01 --reference analysis/local-mmc3-irq-phase-010/mesen-01 --rom analysis/local-mmc3-integrated-009/rom-02 --out <fresh-build> --viewport 0
python -B tools/run_nes_trace_replay.py --mesen analysis/local-mesen/Mesen.exe --probe <fresh-build> --out <fresh-ASCII-capture>
~~~

Repeat with viewport1; separately use --fault chr and --fault length at viewport0.
Runner keeps normal_pass false for intentional fault cases while expected_outcome_verified checks the exact failure.
chr flips tile2's firstrow bit, affecting only source frames1/3.
length changes packet2 map length; runtimeE2 must reject before any DMA or map switch.
PacketCRC, reset/epoch, asynchronous ownership, general descriptor bounds and release validation are not claimed.

Published evidence layout:
top/build-02 and top/capture; bottom/build and bottom/capture;
chr/build and chr/capture; length/build and length/capture.
Audit with python -B tools/verify_nes_trace_replay.py --runs analysis/local-trace-replay-020 --out <fresh-json>.
The auditor reparses raw traces via the runner audit, compares stored summaries, merges actual RGB captures back into
source-indexed240-row images, and tests malformed packet/plane data.
Bad initial header build/run and the initial ineffective width mutation are retained outside public sources.
No commercial ROM, emulator binaries, logs or generated ROMs are allowed in Git.
