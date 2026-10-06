# NES P0/P1 interface contract (candidate 001)

SPDX-License-Identifier: MIT. 2026-10-04. This freezes the **software experiment**
contract; FPGA wire layout, board pins and hardware acceptance remain open.

## Scope and adoption

Product target: designated Japanese SMB3, mapper 4/MMC3, NTSC SNES, FXPAK Pro
Rev.D STM32 / EP4CE15F17C8. NROM is auxiliary diagnostics. GBC baseline is C44 /
sd2snesHST 0.9.0. ROM paths are not arguments to any P1 tool. No common MCU change.

`analysis/source-lock.json` fixes 13 upstream files, SHA256, individual notices,
and 134 prior evidence files / 16 planning snapshots. P1 currently adopts only
original MIT Python/Lua code. MiSTer CPU/PPU/APU is the P2 candidate; headerless
MMC3, save-state helpers and RAM wrapper are explicitly held before vendoring.
T65 uses its original source/synthesized-form BSD-style notice, not a substituted
MIT header. OPLL/VM2413 and unlicensed N8 code are excluded. File enumeration here
is a candidate inventory, not a complete, tested P2 compile dependency closure.

## Clock, memory and physical interfaces

| Boundary | Required contract | Status |
| --- | --- | --- |
| NES master | Nominal NTSC 21.47727 MHz, CPU divide 12, PPU divide 4; existing probe 46.560846 ns | Existing probe assumption; board clock phase/odd-frame drift unresolved |
| External PRG/CHR | Byte addresses, preserve >=25-bit PRG and >=22-bit CHR candidate interface; original physical CHR address before cache translation | No runtime server yet; no arbitrary CPU/PPU CE stretching to hide latency |
| CPU RAM/CIRAM | Separate 2 KiB each; deterministic reset policy and read-during-write | Proposed only |
| PRG RAM | SMB3 working allocation 8 KiB; no battery/save claim | Proposed only |
| Board RAM | Source says PSRAM 16 MiB, 16-bit, 70 ns; SRAM 512 KiB, 8-bit, 45 ns | Pin map, turnaround, IO delays, arbitration and worst response unverified |
| Mailbox crossing | Bundled immutable payload plus synchronized ownership; epoch reset invalidates outstanding transfers | Python lifecycle model only; CDC RTL/constraints absent |
| Audio/input | Native CPU/APU time and bounded latency; no frame dropping or slowdown | P1 does not implement these paths |

The earlier 12,122 LE / 0 M9K fit excludes external memory, MMC3, real IO and the
video path. It is neither a board fit nor evidence of zero NES memory cost.

## Synthetic raster/event contract v1

Coordinates: source x=0..255, y=0..239. Events are sorted `(y,x)`; stable input
order defines same-dot writes. `x,y` means **effective pixel state**, not CPU bus
write time. A future adapter must resolve loopy v/t, fine X, fetch timing,
mirroring and physical CHR generation from the real PPU. The model does not claim
to emulate those mechanisms or to derive MMC3 A12/IRQ behavior.

JSON packet: schema, epoch, frame_id, name, atlas, 240 line records. Atlas key is
`physical_chr_byte_address:generation:bg|obj`; each value is an 8x8 2bpp planar
tile, interleaved low/high plane bytes for each row. Resolved runs have x/end,
key, fine offset, row, palette group, and palette/emphasis/grey/mask/blank state.
Sprite line records retain the first eight NES-selected sprites in OAM order,
8x16 tile selection, BG priority and transparent-first-hit behavior. No silent
coalescing or eviction. Limit is 64 source events; overflow/order/range/kind errors
stop the experiment. All 240 rows are compared; display loss is counted separately.
Each pattern's frame ID and pixel coordinates are in the evidence. Numeric y/frame
labels are not yet drawn into pixels; this is not a complete visual diagnostic UI.

A = independent analytic synthetic renderer; B = planar atlas/run decoder.
`native_candidate` is a restricted software comparison (line-only state changes,
32 sprite selection). It is **not C** and is not an exhaustive SNES renderer.
C = actual Mesen SNES PPU output of the WRAM host, currently fixed scroll/split only.

The full resolved trace is a diagnostic format (up to 126,736 bytes of 16-byte
run records in these tests), not an adopted per-frame cart transport format.
Packets and atlas stay immutable through READY/READING. Hardware packing, queue
storage and admission accounting still need a compact event compiler.

## Ownership and reset

Two slots: FREE -> producer construction -> READY -> READING -> ack -> FREE.
Model publication requires `complete=True`, strictly increasing frame_id, free
slot. Consumer takes the oldest READY. Acknowledgement must match epoch, frame_id,
slot, READING owner. Reset increments epoch, clears both slots and frame ordering;
stale ack is rejected. Full queue is a fatal recorded experiment error, never an
implicit frame drop or acceptable production policy. 1,000 sequential transfers
check bounded bookkeeping, not oscillator drift or hardware throughput.

TileCache pins immutable `(physical address, generation, role)` keys per owner.
Admission computes free/evictable space before mutation. Insufficient capacity
fails without removing pinned tiles or publishing the new owner. New generation
never aliases old generation. Actual BG/OBJ capacity and per-frame admission are
not integrated with the FPGA or SNES VRAM yet. Reset must retire all DMA before
any new epoch can reuse physical memory; Python epoch rejection alone is not that
hardware guarantee.

## Schedule model and host

VBlank usable clocks = `(261-height)*1324 - 4`, conservatively including the odd
short line. DMA = 8 clocks/byte plus assumed 24/channel +16 synchronization.
CPU reserve 768 clocks, register setup 192/channel, diagnostic adds 256 clocks.
HDMA initialization estimate 18+24/channel; line estimate 18+16/channel+8/byte.
272 clocks is an explicit conservative line service **assumption**, not measured
board allowance. Eight channels maximum. Deadline and 80% target are separate.
Original 6123.5/3641-byte upper bounds omit all these reserves. References:
[SNES timing](https://snes.nesdev.org/wiki/Timing),
[Anomie's timing research](https://github.com/gilligan/snesdev/blob/master/docs/timing.txt).

Budget cases are transparent stress/example payloads, not SMB3 worst-case bounds.
They include named CHR/map/OAM/CGRAM bytes; a complete compact event transport,
HDMA table fetch/refresh variation, MCU contention, read starvation, handler
instruction trace, and timing measurements remain outside model acceptance.
No active-display VRAM DMA or forced-blank streaming is assumed.

Host: original LoROM boot copies 65816 code to $7e:2000. DBR/DP/stack/mode are set.
Startup forced blank loads 8192 tile +4096 map +32 palette bytes once. Mode0 BG1,
64x32 map, horizontal offset 1 -> 0 at source y=117 via direct HDMA channel 1.
BG vertical offset compensates SNES visible scanline numbering. Steady-state VRAM
DMA is zero: this proves raster replay, not continuous new-frame upload capacity.
239-line display is explicitly a laboratory probe; row 239 is unrepresented.
Diagnostic ON adds a WRAM marker only, not FPGA instrumentation overhead.

Mesen is isolated with its own portable settings. Lua only reads PPU output and
WRAM, writes captures, and stops after frames 10/11. No screen-buffer injection,
PPU writes, cheats or overlay. Compare all displayed pixels at fixed coordinates,
no alignment search. RGB555 expands by bit replication `(v<<3)|(v>>2)` per the
pinned local Mesen source; this is a synthetic LUT, not a NES analog-color claim.

## Mode1 fixed-scene extension

The later `build_patch_probe.py` experiment also passes C for the synthetic
midline palette event (y=119,x=123). BG3 uses 2bpp; BG1 uses a sparse 4bpp overlay.
Seventeen patch tiles, four palette groups, and a BG3 map switch at line 120 are
preloaded; transparent entry 0 is reserved and black is a nontransparent patch
entry when necessary. The patch-omission mutation reproduces exactly 91 errors.
This is a second fixed-scene implementation, not the compact streaming compiler.
