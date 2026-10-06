# Captured CHR bank patch replay024 contract

SPDX-License-Identifier: MIT.

Candidate NES-R2-BANK-PATCH-024; NES implementation014 is unchanged.
Input: pinned021 split and fine_x Mesen observations, frames6..9, immutable16KiB CHR.
Build calls021 read_case before the low-level encoder, validating source ROM/capture bytes, PPU state and fetch cadence.
Low-level encode/decode are not standalone source admission validators.

## NBP1 packet

All integer fields are little endian; layout extends022 without mutating its implementation.

| Offset | Bytes | Meaning |
| --- | ---: | --- |
|0|4|NBP1|
|4|1|version1|
|5|1|output frame1..4|
|6|1|fine-X0..7; actual reference0/1 only|
|7|1|patch count0..32|
|8|2|width256|
|10|2|source height240|
|12|4|maximum consumed source fetch tick; metadata only|
|16|4|map bytes1980|
|20|1920|32×30 u16 main tile indices|
|1940|60|33rd column30 u16 indices|
|2000|8|fixed four-symbol RGB555 palette|
|2008|16×count|SNES2bpp per-row low/high plane bytes|

Packet length2008+16×count; actual split2328B, fine_x2008B. ROM stride4096B.
No sprite fields. Allocation is deterministic over completed current-frame cells only.
A cell matching one of its actual source tiles uses that tile; otherwise it consumes one patch slot.
No later-frame fetches or union-of-future-bank choices are used.
Slot256..287 is reserved. An ordinary current-frame reference there rejects the packet.
Decoder rejects unwritten reserved indices and requires each supplied patch index to be referenced.
This reservation bounds one specimen, not a general allocator or maximal cache.

## Consumer

Reuse022 Mode0 BG1, 64×32 map, map word bases0000/0800; CHR base2000.
Preload whole16KiB atlas. Patch slot256 maps to word2800.
At VBlank check the generated packet's expected first12 and map-length4 header bytes.
Perform main1920/edge60/palette8 DMA, then count×16 contiguous CHR DMA, then HOFS/BG1SC commit.
This specialized four-frame ROM consumer uses build-time validated addresses/counts.
It does not implement a general runtime payload validator, CRC or rollback after partial DMA.
Rejecting count before all DMA retains prior display with errorE2.
Normal sampled20patch deadline22788clocks/minmargin7130. Unmeasured32patch deadline remains open.
BG atlas storage is shared across frames; reserved indices are never admitted as ordinary tiles, avoiding stale overwritten data.
Full-frame buffering and completion latency are not implemented or proven.

## Reproduction

Use fresh output directories; Python -B -X utf8. Existing Mesen runtime under ignored analysis/local-mesen.
For top/bottom set viewport0/1, case split, fault none. For regression use fine_x/0/none.
Fault runs use split/0/patch and split/0/count.

~~~powershell
python -B -X utf8 tools/build_nes_bank_patch.py --workloads analysis/local-video-workloads-021 --out <fresh-build> --case split --viewport 0 --fault none
python -B -X utf8 tools/run_nes_bank_patch.py --mesen analysis/local-mesen/Mesen.exe --probe <fresh-build> --out <fresh-absolute-ASCII-capture>
python -B -X utf8 tools/verify_nes_bank_patch.py --runs <root> --workloads analysis/local-video-workloads-021 --out <fresh-json>
~~~

Arrange root/{top,bottom,fine_x,patch,count}/{build,capture}. Existing observation-only capture_fine_scroll.lua is reused unchanged.
Keep Mesen settings disabled from saving, frame skipping disabled, child-only DOTNET_ROOT.
No new emulator downloads, Questa license attempts or RTL modifications are needed.
Raw commands/logs/ROMs stay ignored in analysis/local-bank-patch-024; public artifacts contain hashes and sanitized results.
Prior023 224hashes were verified and six status files preserved before update.
All actual outcomes and the 23 software negative assertions must pass. Top/bottom union proves source coverage only;
simultaneous240 display, live release/queue/CDC, combined sprite, largeCHR, hardware and SMB3 remain outside this result.
