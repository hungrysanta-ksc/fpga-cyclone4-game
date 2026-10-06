# H1 pattern diagnostic033 contract

SPDX-License-Identifier: MIT.

This original diagnostic extends unchanged031 transport with a queue-clock ROM producer.
It is separate from the NES game core and does not resolve live encoding, normal frame pacing,
240-line display policy, or the remaining40LAB of the032 core co-placement.

## Producer and payload

The builder creates three distinct 2048-byte SNES Mode0 BG1 maps in h1-pattern.hex.
A shared4480-byte CHR atlas and palette are preloaded by the SNES program.
The ROM producer uses a synchronous6144-byte ROM, one begin/write/publish command at a time,
and waits for registered acceptance. It waits eight queue edges after common reset.
reset_epoch must remain stable through both endpoint release and the complete generation.

Sequence starts at1. Page order1/2/3 advances only after accepted publish.
BEGIN error1 (slot unavailable) retries without changing sequence, page, or payload.
Other errors fail-stop; a missing response for256 queue edges also stops with error15.
Publishing65535 sets exhausted and stops, avoiding sequence0. This boundary is implemented,
but the present bounded run does not execute65535 packets.
Common reset invalidates both queue ownership and producer position; independent resets remain unsupported.
The six-KiB diagnostic ROM is not an estimate for a live NES encoder.

## Actual 65816 client

The ROM copies code to WRAM, preloads CHR/palette, then shows LINK WAIT.
It configures epoch1 and the expected16-bit sequence through bank00:6002..6005.
Acquire retries when IDLE; BUSY is polled; each acquisition has a65535-iteration budget.
It checks READY, length2048, stage and frontend errors before transfer.

After the next VBlank edge it performs actual incrementing A-bus DMA from40:8000..87ff
to2118/2119 (mode1), then checks consumed2048 and both error registers.
Commit is issued only after DMA, and acknowledged IDLE is required before advancing the visible page.
A59-boundary hold plus the next transfer boundary gives60 NTSC frames between visible pages in this run.
Sequence exhaustion, acquisition timeout, bad length, consumed count, bus faults or commit timeout
route to a static readable LINK ERROR / RESET / NO PASS screen, with error byte at WRAM1fe8.
The diagnostic does not recover an interrupted packet in-place.

Epoch1 is a cold, common-reset laboratory assumption. A board loader must establish a fresh
generation and coordinate the ROM's epoch before warm-reset/menu lifecycle can be approved.
224 active rows are for this diagnostic only; no NES crop policy is adopted.

## Evidence boundaries

1. Actual Questa runs the autonomous producer and unchanged031 RAM queue/CDC/stage/frontend.
   The logical SNES pin driver uses20ns setup,180ns RD/WR low,20ns hold plus80ns idle.
   Three queue/host periods46.560846/11.904762,20/10,46.560846/20ns are tested.
   Tests cover two-slot backpressure, six exact pages, reset during payload drive,
   reset during production followed by a fresh generation, and injected wrong-epoch fail-stop.
   The final error injection intentionally forces only the producer epoch.
2. Actual Mesen runs this ROM's CPU and PPU DMA. An explicit Lua cartridge-device model supplies
   bytes captured from the first actual RTL run. This is sequential evidence, NOT timing-coupled
   co-simulation. The model's21478-master-clock staging delay and200-clock commit delay are
   assumptions, not measured RTL or board latency. Register polling timing is not cross-proven.
   Positive run and no-response/bad-length negative runs are independently inspected.
3. Quartus map/fit uses exactly the same H1 RTL and pattern bytes. Virtual pins and two
   unassigned clock pins are used. No STA, board PLL, physical IO, CDC timing or loader exists here.
   async_reg is unrecognized by this Quartus version; actual synchronization placement/timing
   constraints must be supplied and reviewed before board signoff.

The emulator observer returns device bytes intentionally; it does not patch VRAM, registers,
or the expected screen into the PPU. Mesen's CPU really programs DMA and PPU rendering produces the image.
Read callbacks cover DMA reads according to the inspected local ScriptManager implementation.
Actual DMA has8-master-clock intervals plus48-clock intervals spanning DRAM refresh.
The audit checks each long interval's position, full bytes, full239-row captures (7+224+8),
DMA bank/address/mode/count, VBlank timing, and no payload DMA in negative tests.

## Reproduce

Run tools/build_nes_h1_pattern.py --out FRESH_BUILD.
Use tools/run_nes_h1_pattern.ps1 with the existing FLOAT wrapper and explicit Python/Questa paths,
-Pattern FRESH_BUILD/h1-pattern.hex and -Out FRESH_RTL. No recurring license smoke check is required.
Run tools/run_nes_h1_client.py --probe FRESH_BUILD --rtl-bytes FRESH_RTL/q46_h12.bin
--out FRESH_CAPTURE --mesen INSTALLED_MESEN, with mode normal, absent or bad_length.
Run tools/nes_h1_pattern_resource.py --pattern FRESH_BUILD/h1-pattern.hex
--out FRESH_FIT --quartus-bin INSTALLED_QUARTUS.
Preserve build/rtl/normal/absent/bad_length/resource under a common ignored evidence directory;
tools/verify_nes_h1_pattern.py --root EVIDENCE --out RESULT.json rechecks it.

No hardware-test package is released from this milestone. Next gates are actual board PLL/reset,
pin and bus arbitration, ROM/renderer service, MCU loading/recovery, and same-candidate fit/STA.
