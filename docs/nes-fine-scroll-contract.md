# Fine-X map-column transport022

SPDX-License-Identifier: MIT.

Input: preserved021 baseline/fine_x original NES Mesen captures. Actual reference fine-X values0 and1 only.
The packet field supports0..7; that range is not a claim of eight independently emulated NES cases.
No coarse/vertical/mid-frame scroll, sprite, CHR RAM, alternative palette events or largeCHR support.

## Packet and encoder
NFX1 header, little-endian <4sBBBBHHII,20bytes:
magic,version1,output frame1..4,fine-X0..7,flags0,width256,height240,releaseNESmastertick,map bytes1980.
Payload:960tile words for32columns/30rows(1920B),30right-column tile words(60B),4RGB555colors(8B).
Total2008B; storage stride2048B. Each tile index must be<1024.
The encoder consumes the complete audited021 BG trace. Fine-X coordinates extend active fetch slots
through dot247 to include column32, plus prerender/previousline prefetch columns0/1.
Exactly990cells/15840pixel-window plane reads are required. Tile changes within an8x8cell reject.
Software decode shifts source x byfine-X, using the extra column when the tile column reaches32.
All240source rows must match actual NES indexed reference before building the SNES ROM.
The builder calls021's input audit; the low-level encoder is not a standalone full-cadence validator.

## SNES layout and transaction
Mode0 BG1,64x32map shape. Double map bases atVRAM word0000 and0800.
Each set has two32x32pages; totalreservedmap space8KiB. CHR word2000..3fff contains the full16KiB immutable atlas.
No observed-union preload; allsourceROM bytes are available at loading.
DMA1:1920B contiguous words, VMAIN80, destination setbase.
DMA2:60B as30words separated by32words, VMAIN81, destination setbase+0400.
DMA3:8Bpalette. Then write packet fine-X and high0 toBG1HOFS and selectmap viaBG1SC=(slot*8)+1.
The next frame resets VMAIN80 before its contiguous transfer.
The actual CPU validates header bytes0..11 and16..19 duringVBlank;release metadata12..15 is not a synchronization primitive.
Unused columns33..63 and bottomrows30..31 are outside the tested fine-X0..7/vertical0 viewport.
No runtime bounds-generalization, CRC, epoch/reset or live producer ownership claim.

## Reproduction
From the checkout, fresh output paths:

~~~powershell
python -B tools/build_nes_fine_scroll.py --workloads analysis/local-video-workloads-021 --out <fresh-build> --case fine_x --viewport 0
python -B tools/run_nes_fine_scroll.py --mesen analysis/local-mesen/Mesen.exe --probe <fresh-build> --out <fresh-ASCII-capture>
~~~

Run fine_x viewport1, baseline viewport0, then fine_x viewport0 faults edge/scroll/length.
Runtime uses the existing isolated Mesen settings with frame skipping disabled. No global installation/settings changes.
edge changes all30right-column tile keys; onlyx255 differs atfine-X1.
scroll deliberately writesHOFS0 instead ofthepacket1;length changespacket2 maplength andmustrejectbeforeDMA.
Fault results remain normal_pass=false and require exact expected_outcome_verified.

Evidence layout <runs>/{top,bottom,baseline,edge,scroll,length}/{build,capture}.
python -B tools/verify_nes_fine_scroll.py --runs <runs> --workloads analysis/local-video-workloads-021 --out <fresh-json>
Auditor reparses raw DMA/phase/VMAIN/scroll records, matches stored results and tests malformed/source-edge data.
Two independent239row viewports coverall240rows but do not implement simultaneous240rowdisplay or alternating-view product policy.
Consumer timing assumes already-complete packets in ROM. Live producer/pacing/memory/CDC/FIFO and fullboard resource accounting remain open.
