# Immutable CHR residency025 contract

SPDX-License-Identifier: MIT.

Candidate NES-R2-CHR-RESIDENCY-025; unchanged core014.
Use021 banks32/fine_x capturedframes6..9. Builder invokes read_case admission on original ROM/trace/state first.
The low-level encoder is not an independent complete source validator.

## NCR1 packet and consumer

Layout022: header20, map1920, right column60, fixed palette8 =2008B.
Header format little endian <4sBBBBHHII>: NCR1,version1,frame1..4,fineX0..7,window0..1,width256,height240,release tick,mapbytes1980.
Only fineX0/1 observed. Window replaces022 flags. Tiles are source physical tile modulo1024.
All990 cells /15840 plane fetches must be present. Each cell must have one physical tile,
and the entire frame must use one16KiB source window. Source must be immutable16KiB or32KiB CHR, BG-only, no coarse/vertical/midframe PPU changes.
This path rejects mixed windows and in-cell changes;024 remains a separate experiment.

Whole converted32KiB atlas is copied from ROM bank2:8000 to VRAM word2000 at startup.
16KiB regression sources are zero padded. No future frame set or frequency selects preload contents.
A128KiB LoROM holds the atlas at file10000..17fff; executable body stays in WRAM7e2000.
Four packet slots remain ROM bank1:8000 with2048B stride.
At VBlank, specialized guards compare generated expected header bytes0..11 and16..19.
Then DMA1920/60/8B, HOFS, and BG1CHRbase=2+2*window; commit map base/display counter.
Runtime is a four-frame ROM-fed fixture, not a general packet parser or actual cartridge frontend.

VRAM: maps byte0000..1fff, CHR byte4000..bfff. Total40960B, remaining24576B.
Existing023 OBJ word4000 overlaps; relocation/joint rendering must be verified before integration.
No frame CHR refill for these immutable resident inputs. No promise for larger ROM, CHR RAM or cross-window rendering.

## Reproduce and audit

Fresh directories required. Existing private Mesen runtime, child-only DOTNET_ROOT, no settings saves, frame skipping disabled.
top/bottom: banks32,viewport0/1,faultnone. fine_x: fine_x,0,none.
bank: banks32,0,bank inverts valid CHR selection after header checks.
window: banks32,0,window corrupts packet2 to window2, expecting pre-DMA E2 rejection.

~~~powershell
python -B -X utf8 tools/build_nes_chr_residency.py --workloads analysis/local-video-workloads-021 --out <fresh-build> --case banks32 --viewport 0 --fault none
python -B -X utf8 tools/run_nes_chr_residency.py --mesen analysis/local-mesen/Mesen.exe --probe <fresh-build> --out <fresh-absolute-ASCII-capture>
python -B -X utf8 tools/verify_nes_chr_residency.py --runs <root> --workloads analysis/local-video-workloads-021 --out <fresh-json>
~~~

Arrange root/{top,bottom,fine_x,bank,window}/{build,capture}. Observer only reads state and logs callbacks, including210b.
Auditor validates exact DMA banks/source/destination/sizes, startup, CHRbase/scroll/map commits, VBlank deadlines,
four consecutive actual frames and fault outcomes. Verifier merges two239-row views, checks full source240 rows,
reconstructs packets from NES fetch, tests23 negatives and computes stored packet sizes from022..025 actual files.
Packet storage tables are arithmetic alternatives, not synthesized M9K or adopted FIFO sizes.
Cold streaming6084×8=48672clocks versus raw30008 blank is a lower bound, not an executed failed test.

Public report/JSON/manifest are sanitized; raw ROMs, captures, command logs and prior baseline status stay ignored
in analysis/local-chr-residency-025. No Questa/RTL/Quartus rerun needed here.
Live frame completion/arrival, external memory, queue/CDC/pacing, joint sprite/patch rendering and hardware remain open.
