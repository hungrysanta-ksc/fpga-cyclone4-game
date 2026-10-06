# 054 SPI ROM loading contract

SPDX-License-Identifier: MIT.

This is an original diagnostic control interface for the unchanged053 loader and
052 read controller. It does not parse iNES files, implement a game menu, validate
physical PSRAM contents, or provide an actual NES video consumer.

## Wire format

Mode0, MSB first, SCK at most250kHz, at least1us between bytes and after the final
rising edge before CS release. The C driver uses2us low/high halves, samples at
the end of the high half, and holds CS across exactly8bytes. The FPGA advances
MISO only on synchronized falling SCK, preserving the044/036 sampling fix.

| TX byte | Meaning |
| --- | --- |
| 0 | command |
| 1–3 | expected completed byte count, big endian24bits |
| 4 | argument |
| 5 | bitwise complement of argument |
| 6 | CRC8, polynomial0x07, initial0, non-reflected, no final XOR, over bytes0–5 |
| 7 | fixed tail0xA5 |

| Command | Meaning | Argument / count |
| --- | --- | --- |
| 60 | BEGIN | arg0=PRG64KiB+CHR16KiB, arg1=PRG64KiB+CHR32KiB; count must0 |
| 61 | DATA | arg=one byte; count must equal completed loader count |
| 62 | END | arg0; exact final count required by053 |
| 63 | START | arg0; separate from END, requires completed image |
| 64 | STOP | arg0; RUN→loaded READY; unfinished/other stopped image abandoned per053 |
| 65 | STATUS | arg0; count ignored; no state change |

Only a complete, checked frame commits on synchronized CS rising. Partial frames
after a recognized command, extra bytes, bad CRC/tail/complement, invalid args,
busy DATA and count mismatch are sticky errors. A received byte with matching
count is accepted exactly once; retransmitting that count fails instead of
writing it again. There is no automatic retry/reordering. All other command
nibbles are left to the044 parser. A transaction ending before a complete command
byte has no effect. This is not a defense against arbitrary continuous noise.

## Response and errors

Byte0 is ignored. Bytes1–7 are ONE snapshot taken after receipt of the command
byte; they describe the state BEFORE this command's CS commit. A caller must
issue STATUS afterward to confirm the command. The C helper does this and checks
the resulting count/state; a successful transfer alone does not mean success.

| RX byte | Meaning |
| --- | --- |
| 1 | protocol0x54 |
| 2 | flags: bit0 ready, bit1 loaded, bit2 RUN, bit3 SPI fault, bit4 loader fault |
| 3 | SPI error code |
| 4–6 | completed byte count, big endian24bits (only17bits used) |
| 7 | unchanged053 loader error code |

SPI codes:1 framing,2 CRC/tail/complement,3 opcode/argument,4 DATA not ready,
5 unexpected count. The first SPI fault is sticky until common reset. Status
remains readable, including the completed count, after fault. Loader errors retain
the053 definitions. Invalid commands after a fault do not clear or overwrite it.

CRC protects the command frame, **not physical ROM integrity**. `loaded` means
the expected number of pin writes completed and END was accepted. Neither CRC8
nor count is cryptographic validation or PSRAM readback proof. A future board
loader must define readback/integrity handling before running unverified data.

## Ownership, resets and044 coexistence

`nes_spi_boot` instantiates the unchanged053 pin owner. SPI errors mask exported
RUN/loaded/ready and reset the read controller, but do not reset an accepted write
pulse. Only external common reset may cut a write, invalidating the image.
The core/cache/packet path must follow reset OR !RUN and the049 RAM scrub contract.

`tools/nes_spi_boot.py:integrated_boundary()` materializes044, renames its local H1
ROM signals, and adds this loader on the SAME SPI pins with a response mux. Legacy
F0/F1 queries still return A5/44. New60–6F transactions select the054 response after
the command byte. The H1 diagnostic RUN and NES ROM RUN are intentionally separate;
the H1 pattern generator is not a live NES video consumer. The board adapter uses
clock84 for the memory/control domain and takes a separate NES clock input. These
are ports, not qualified physical clock sources. PLL loss immediately removes
drive and invalidates the ROM path, even if the clock stops.

The portable C driver performs the actual bitbang timing via platform pin/delay
callbacks. The caller must acquire SPI/GPIO and hold the console reset as in044;
GPIO mode takeover, USB interrupt ownership, SD/iNES reading and invocation from
the STM32 menu are not added by this driver. Its callback waveform is tested at
the documented250kHz timing. This is not a complete flashed STM32 firmware image.

The conservative one-byte command plus status query costs about556us/payload byte
with these delays: approximately45.5s for80KiB or54.7s for96KiB, excluding setup.
This is a diagnostic throughput choice; batching and production load speed remain
future work, with the same count/commit/ownership guarantees required.

## Verification and reproduction

`tools/run_nes_spi_boot.ps1` takes explicit `-Python -FloatWrapper -QuestaBin -Gcc
-Mode unit|wave -Out` arguments. Use a fresh ASCII output path and the existing
authorized FLOAT workflow. Licenses/server logs stay private.

- `unit`: accelerated digital SPI stress, not electrical timing qualification.
  Full80KiB is populated only by serial frames and PSRAM pin writes, then read
  through052. Malformed frames, sequence errors, early START/END, STOP, reset,
  CRC/tail/complement and writes during RUN are exercised.
- `wave`: actual new C transfer callback timestamps and consumed response bits
  against materialized044+054,64pin-written bytes, legacy identification queries,
  CRC failure, and PLL-loss reset. Command/dummy response bits are explicitly ignored.
- `tools/nes_spi_boot_resource.py --baseline <private053-resource> --out <fresh>
  --quartus-bin <installed>`: checks every053 source hash before adding SPI to its
  actual-core resource geometry. It excludes H1 diagnostic shell/program ROM,
  board PLL/pins, real SNES consumer and STA signoff. Standalone or virtual joint
  fit is not proof of complete physical-board feasibility.

No054 SD image or new hardware acceptance follows from these tests. Keep044 and
GBC intact. Full96KiB SPI completion, actual-core execution after SPI loading,
MCU board binding, memory integrity, real clocks/consumer and physical timing
remain explicit integration gates.
