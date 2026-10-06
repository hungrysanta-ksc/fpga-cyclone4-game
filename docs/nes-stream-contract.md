# NES stream experiment contract — 002

SPDX-License-Identifier: MIT. 2026-10-05.

This extends the historical [P0/P1 contract](interfaces.md) without changing its
source lock or GBC baseline. Only original synthetic inputs are accepted.

## Layout and transaction

All VRAM addresses below are word addresses. BG3 maps: $0000 and $1000, 4096 bytes
each. BG1 maps: $0800/$0c00, 2048 bytes each. BG1 CHR slots: $3000/$3400, 2048 bytes
each, transparent tile 0 retained. BG3 CHR at $4000, 8192 bytes. OBJ CHR at $6000,
480 bytes. Source packets are fixed LoROM banks 1..16; this is a test supplier,
not an FPGA bus or proposed cartridge file format.

Each source bank has patch CHR at $8000, map rows 10..14 at $8800/$8a00 for the two
VRAM slots, CGRAM at $8c00, length/scroll descriptor at $8e00, OAM at $9000.
The descriptor is 3 bytes (u16 little-endian CHR length, u8 scroll). CRC, external
producer admission, mailbox CDC, reset synchronization and byte-stream packing
are not implemented here. Runtime rejects zero, >1024 or non-32-aligned CHR length.
The ROM supplier stores the two map variants; the host selects by inactive slot,
never by frame-id parity after a reset cancel.

WRAM $1fe0 displayed frame, $1fe1 attempted frame, $1fe2 epoch, $1fe3 active slot,
$1fe4 pending slot, $1fe5 error, $1fe6 phase, $1ff0 ready. Counters are 8bit in this
short experiment and not a production protocol. Phases 1=begin, 2=staged,
3=committed, 4=reset-cancel, $ee=halt. Errors E2=invalid length, E1=VBlank ended
before the shared palette/OAM commit. No normal queue or frame-dropping policy.

The host executes from WRAM $7e:2000. Poll VBlank, disable HDMA for MDMA, fill the
inactive CHR and map, check for injected reset cancel, then update CGRAM, OAM,
scroll and visible map within the admitted VBlank interval. Shared palette/OAM
commit cannot be canceled halfway; a real reset request must wait for that
bounded phase. Physical asynchronous reset is outside this software test.

## Sprite and color scope

Original 8x16 sprites split into two SNES 8x8 OBJ. The first-eight-per-line source
selection masks excluded opaque rows before SNES rendering; transparent-first
selection and BG priority are retained for this stimulus. Only 15 SNES OBJ are
used, below SNES limits. BG3 tile priority is high, Mode1 BG3 global priority boost
is off; OBJ priority 0 is behind this BG3 and priority 1 is in front. The palette
patch occupies a disjoint vertical region in this test, so arbitrary OBJ/patch
layer overlap is not proven.

An injective 64-color diagnostic RGB555 LUT distinguishes all symbolic color IDs.
It is not an NES analog or emphasis LUT. No sprite CHR update occurs after startup;
only OAM positions and the per-frame patch/map/palette change.

## Reproduce

Use the isolated Mesen setup in [the static host README](../snes/video_probe/README.md).
Build `python -X utf8 snes/video_probe/build_stream_probe.py --sprites --out <fresh-probe>`.
Add `--diagnostic`, or `--fault reset|length|overrun|selection` for each separate case.
Run `python -X utf8 snes/video_probe/run_stream_probe.py --mesen <isolated-Mesen.exe>
--probe <probe> --out <fresh-ASCII-directory> --frames 128` (one shell line).

The runner always disables emulator frame skipping. Lua callbacks observe only;
no PPU/memory/screen writes are injected. Raw RGB is captured every displayed
frame after ready. The fixed reference is selected by frame_id; normal sequence
and emulator frame continuity must also hold. No matching-frame search is used.
DMA timing uses actual emulated master clocks and register writes, not Python
wall-clock time. Callback cost does not change emulated master-clock timing.

For the published six-run audit, use 128 frames for off/on, 64 for reset, and 32
for length/overrun/selection. Keep captures as `<runs>/<case>/`, with its generated
ROM, expected RGB and manifest under `<case>/build/`, then run
`python -X utf8 tools/verify_nes_stream.py --runs <runs> --out <new-audit.json>`.
Fault runs intentionally return nonzero; the final audit checks why they failed.

All C comparisons cover 239 visible rows only. No complete P1, board, physical
reset, hardware cache, or SMB3 support claim follows from this experiment.
