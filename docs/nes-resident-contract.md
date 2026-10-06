# NES two-set residency contract — 004

SPDX-License-Identifier: MIT. 2026-10-05.

This preserves the historical [003 cache contract](nes-cache-contract.md) and
adds an original immutable-ROM supplier with advance knowledge of the next set.
It is not a general predictive cache or an NES fetch/mapper implementation.

## Layout and supply assumptions

BG CHR uses VRAM word ranges $4000..$4fff and $5000..$5fff (8KB each).
BG3 base $210c is 4 or 5. Within each set, window w uses 512 words/1KB.
OBJ CHR remains at $6000, so the two BG sets do not overlap it. Fixed BG3 maps,
patch CHR/map slots and palette split are unchanged from 003.

Logical sets 0..3 are respectively banks 0..7/gen0, 8..15/gen0, 0..7/gen1,
8..15/gen1. Set 0 is initially loaded; every eight frames the complete prepared
set becomes visible. After each commit one window of the *next* set is uploaded
into the now-inactive physical set. The first upload starts eight frames before
its use. All required future bytes exist in the synthetic ROM beforehand.
This is sufficient for this schedule; no real-game availability is inferred.

Each 32KB packet retains patch CHR $8000, patch maps $8800/$8a00, CGRAM $8c00,
OAM $9000, startup OBJ $9800, and 1KB preload data $a000. Descriptor at $8e00:

| Byte | Meaning |
| --- | --- |
| 0..1 | patch CHR length, u16 LE, nonzero, <=544, divisible by 32 |
| 2 | scroll |
| 3 | display physical set/page, 0..1 |
| 4 | required logical display set, 0..3 |
| 5 | preload physical set, must equal display page XOR 1 |
| 6 | preload window, 0..7 |
| 7 | next logical set, must equal (display set+1) modulo 4 |
| 8..9 | preload physical bank and generation, checked against next set/window |
| 10 | completion bit, must equal 1 shifted by window |
| 11 | expected prior mask, must equal completion bit minus 1 |
| 12..13 | preload length, exactly 1,024 LE |

For window 0, the destination mask and logical set are initialized during commit,
after switching visible CHR. Other windows require matching prior mask and set.
Before any DMA the display set must have mask FF and the requested logical ID.
E2 rejects patch length, E3 descriptor shape, E5 missing/incomplete display set,
E6 out-of-order/wrong-set preparation. Only E5 is injected in published header
fault cases; individual E2/E3/E6 guards are not claimed exhaustively tested.

## Metadata and phases

WRAM $1f40..$1f5f stores sixteen 2-byte (bank,generation) keys; $1f60/$1f61
completion masks; $1f62/$1f63 logical IDs; $1f64 active BG page; $1f65 preload
page. Initially page 0 keys represent set 0, mask FF; page 1 keys/ID are FF and
mask is zero. Both pages receive deterministic set-0 placeholder bytes at startup;
page 1 is still invalid until its own preparation mask and logical ID match. This
adds 8KB startup DMA (33,792 bytes total) and makes ownership-fault images repeatable.
Lower scratch $1f66..$1f6b is private to the host.
Frame, epoch, error, patch-slot and ready bytes remain as in 003.

Phases 7/8 mark read-only admission begin/end during active scanout; the packet
cannot change after validation in this ROM fixture. Phase 1 begins VBlank work,
2 completes inactive patch staging, 5 begins noncancelable palette/OAM and screen
commit, 6 marks the new BG page selected before preload, and 3 completes preload
and publication. Phase 4 cancels before commit. EE halts on a defined error.
Rejected admission waits for VBlank, emits phase 1 then EE with zero DMA.

DMA order is patch CHR 544B, patch map 64B, CGRAM 384B, OAM 60B, inactive BG CHR
1,024B. Completion bits/keys follow the final DMA. Normal display needs no repeated
forced blank or skipped source frames. An injected reset at frame 8 after phase 2
retains the screen and both caches, increments epoch, and retries frame 8. This
assumes the same immutable source; it is not real producer-reset invalidation.

## Reproduction and evidence

Use the [isolated Mesen runtime](../snes/video_probe/README.md). Build:
`python -X utf8 snes/video_probe/build_resident_probe.py --out <fresh-build>`.
Add `--diagnostic` or `--fault reset|unannounced|late|stale|owner` per case.
Run `python -X utf8 snes/video_probe/run_resident_probe.py --mesen <Mesen.exe>
--probe <build> --out <fresh-ASCII-output> --frames 128` as one shell command.

Final cases: off/on 128 each; reset 64; unannounced/late 32 each; stale/owner 64
each. Copy captures to `<runs>/<case>/` and generated inputs to its `build/`.
Audit with `python -X utf8 tools/verify_nes_resident.py --runs <runs>
--out <new-audit.json>`. Non-reset fault runners return 1 by design. The auditor
requires the exact fault class and affected-frame set, verifies raw RGB and
frame continuity, reparses raw DMA/phase/base traces and readiness at switches,
and checks active-scanout admission has no DMA. It also records admission time
separately from VBlank work. Callbacks only observe.

For the published reproducibility check, rerun the same owner ROM for 64 frames
into `<runs>/owner-repeat/` (no second build). If this directory exists the auditor
also requires all 64 raw RGB hashes to match the first ownership-fault run.

The 2,048 unique tile patterns and coordinate reference are original diagnostic
fixtures, not a NES PPU reference. Working-set counting covers all 240 source
rows, but actual SNES comparison covers only 239 visible rows. A full new set's
256 pixel-referenced tiles costs 4KB if transferred as 16-byte tiles; this is a
bound for this transfer representation, not a proof against other renderers.
