# NES cache experiment contract — 003

SPDX-License-Identifier: MIT. 2026-10-05.

This original synthetic experiment extends [stream 002](nes-stream-contract.md).
Historical sources/results remain unchanged; new standalone sources freeze this candidate.

## Fixed cache and packet

VRAM word addresses $4000..$4fff contain eight 1KB BG CHR cache pages.
Page `w` starts at `$4000 + w*$200`. Fixed BG3 tilemaps still reference page slots.
Other VRAM layout is inherited from 002. The patch map updates only row 14:
word address `$09c0 + inactive_slot*$400`, 64 bytes. Patch CHR starts at
`$3010 + inactive_slot*$400`, at most 544 bytes. Tile 0 stays transparent.

Each of 32 original LoROM source banks holds one periodic state. Bank packets have
patch CHR $8000; patch row variants $8800/$8a00; CGRAM $8c00; descriptor $8e00;
OAM $9000 (60 bytes uploaded after full 544-byte startup initialization);
OBJ startup source $9800; replacement BG CHR page $a000 (1,024 bytes).

| Descriptor byte | Meaning |
| --- | --- |
| 0..1 | patch CHR bytes, u16 LE; nonzero, <=544, divisible by 32 |
| 2 | horizontal scroll |
| 3 | cache page/window 0..7 |
| 4 | replacement page count, must be 1 |
| 5..6 | expected old physical bank and generation |
| 7..8 | new physical bank 0..15 and generation 0..1 |
| 9..10 | cache upload length, must be 1,024 LE |

This is a fixed ROM supplier, not a production wire format. Eight 2-byte key records
live at WRAM $1f60..$1f6f. The frame/epoch/phase bytes remain as in 002. Before any
DMA, the host validates patch length (E2), cache request shape (E3), and exact old
key (E4). Header CRC, payload CRC, general packing and external bus readiness do
not exist in this fixture. Generation 0/1 is a deliberate alternating stimulus,
not a safe production generation-counter design.

## Ownership, cancellation and timing

Phase 1 begins VBlank processing. Stage patch CHR and map in the inactive slot,
then phase 2. A cooperative reset at frame 7 cancels here, increments epoch,
retains all displayed cache keys/pixels and retries the same frame next VBlank.
There is one deliberate repeated display frame due to this injected reset only.

Phase 5 starts a bounded, noncancelable commit: replace one *active* BG cache page,
store its new key, transfer palette and OAM, update scroll/map/displayed frame,
and emit phase 3. Old BG contents cannot be restored after this point. Actual
DMA must finish before visible scanout; requests arriving during commit must be
deferred by a future real producer. This is not asynchronous reset safety.

The admitted total is 2,076 bytes across five DMAs, including 1KB replacement CHR.
The model reserves 4,096 CPU/setup +768 diagnostic clocks; exact measured clocks
are in [the result](../analysis/CACHE-RESULT.ko.md). Eight-page requests reject
before DMA. No production policy drops frames or slows the producer to handle it.

## Reproduce and inspect

Use the isolated Mesen runtime from [host setup](../snes/video_probe/README.md).
Build with `python -X utf8 snes/video_probe/build_cache_probe.py --out <fresh-build>`.
Use `--diagnostic` for ON, or `--fault reset|burst|tag|stale|alias` for negative cases.
Run `python -X utf8 snes/video_probe/run_cache_probe.py --mesen <Mesen.exe>
--probe <build> --out <fresh-ASCII-output> --frames 128` as one command line.
Emulator frame skipping is disabled by the runner. Capture callbacks only observe.

Keep each capture under `<runs>/<case>/` and its ROM/manifest/expected RGB in
`<runs>/<case>/build/`. Cases/counts: off=128, on=128, reset=64, burst=32, tag=32,
stale=64, alias=64. Run `python -X utf8 tools/verify_nes_cache.py --runs <runs>
--out <new-audit.json>`. Fault runs return 1; the auditor requires the defined
failure, retained images for rejected headers, or exact affected-frame sets for
bad content. It reparses raw DMA order and ownership; results JSON alone is not proof.

Synthetic pattern generation encodes address/generation in six 2bpp pixels and
uses a deterministic SHA256 pattern for other pixels. All 2,048 source tiles are
unique and independently decoded to verify planar encoding. The coordinate
reference does not decode the generated SNES ROM or search for matching frames.
It shares the original source-pattern definition; no claim of an independent NES
PPU reference follows. Only displayed 239 rows are compared.
