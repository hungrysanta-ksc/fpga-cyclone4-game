# Captured one-sprite native SNES replay023

SPDX-License-Identifier: MIT.

Input: preserved021 sprite and fine_x original NES Mesen captures. No new NES/RTL execution.
Supported actual sample: one fixed front8x8 sprite atx40,y80,palette0,no flips,no clipping,plusBG.
Separate fine-X1/no-visible-sprite regression; no combined scrolling-visible-sprite reference claim.

## Evidence to packet
Replay allCPU2003/2004writes, require all256OAM bytes initialized beforeframe6, no capture-time OAM writes.
Onlyentry0 may have visibleY. Requireattributes0 and unclipped8x8 coordinates.
Validate fixed source palette32writes. Observe16CHR bytes atslot0 callbacks inlines79..86,
physicaltile257;thetwo plane callbacks share dot261,which is not electrical bus timing evidence.
Convert the16NES bytes into32SNES4bpp bytes with upperplanes0. Index0 remains transparent.
nes_sprite_packet separates the BG channel only after sprite controls/data are accounted for.
Every generated full240row BG+sprite image must match the actual NES reference.

NSP1 header uses022's20B layout with magicNSP1 and flagsbyte7 ascount0or1.
Offsets20..1939:mainmap1920B;1940..1999:edge60B;2000..2007:BGpalette8B;
2008..2039:OBJCHR32B;2040..2047:OBJpalette8B;2048..2051:OAM4B.
Total2052B;ROMstride4096B. Full16KiB immutableBG CHR atlas startup remains unchanged.
OAM source y79 -> canonicalSNES y80; independent viewport1 ROM decrements the submitted y.
Canonical packet/expected indexed files always retain full240source coordinates.

## Native SNES
Mode0 BG1 plusOBJ main-screen enable17;OBSEL2 (OBJ CHR word4000).
Map slotsword0000/0800, BGCHRword2000..3fff, OBJCHRword4000..400f.
Initialize128hidden OAMentries and high table with544B startupDMA.
Per-frame DMA:main1920B,edge60B,BGpalette8B,OBJCHR32B,OBJpalette8B atCGRAM128,
firstOAMentry4B atOAMaddress0. UpperOAM bits remain startup0; size8x8/tile0/priority3/palette0.
Total2032B PPU DMA. Completepacket header validated beforeDMA;release tick remainsmetadata.
These immutableROM tests do not validate live producer arrival,CRC,reset/epoch or asynchronous ownership.

## Reproduce
Use fresh build and ASCII capture paths with existing isolatedMesen:

~~~powershell
python -B tools/build_nes_sprite_replay.py --workloads analysis/local-video-workloads-021 --out <build> --case sprite --viewport 0
python -B tools/run_nes_sprite_replay.py --mesen analysis/local-mesen/Mesen.exe --probe <build> --out <ASCII-capture>
~~~

Repeat sprite viewport1;fine_x viewport0;then sprite viewport0 with--fault hide,obj,count.
hide forcesOAMy240;obj clears32CHR bytes;count changespacket2 count to2 forpre-DMAE2 rejection.
Faults remainnormal_pass=false andmustmatchtheirdefinedexpectedoutcome.
Arrange <runs>/{top,bottom,fine_x,hide,obj,count}/{build,capture}.
python -B tools/verify_nes_sprite_replay.py --runs <runs> --workloads analysis/local-video-workloads-021 --out <fresh-json>

Audit actualRGB,sourceOAM/CHR,6DMA transactions,VRAM/CGRAM/OAM addresses,VMAIN,TM/OBSEL andframecontinuity.
Two independent239rowviews cover240source rows; no simultaneous240display or productcropapproval.
Full-sprite priority/evaluation/overflow,8x16,flips,clipping,dynamicOAM andgeneralpalette conversionremainoutside scope.
