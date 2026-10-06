# H1 board boundary034 contract

SPDX-License-Identifier: MIT.

This is an independent H1 diagnostic core, without a NES game core, external-memory service,
SD access, sound, or save data. Preserve the GBC implementation and images.
The physical top uses the established EP4CE15F17C8 board's135 pin assignments unchanged.
The existing gbc_bus_pll0 takes8MHz and generates84MHz. Both H1 producer and host use84MHz.
That diagnostic clock choice does not solve NES master-clock/frame-rate synchronization.

## Start, stop and ROM

The board initially does not drive the SNES bus. The MCU must hold the actual SNES RESET line
through configuration, identity queries, ARM and generation verification.
The FPGA top has no SNES RESET input; short/long reset detection and re-entry are MCU duties.

SPI is mode0, at most250kHz, with at least1us between bytes and1us SS hold after the final
rising clock. Stock42MHz MCU SPI cannot be reused without slowing it for this binding.
SS high immediately disables MISO. Commands are interpreted after synchronized SS rising.

|Command bytes under one SS assertion|Meaning|
|---|---|
|F0 00|Second received byteA5 identity token|
|F1 00|Second byte34 hexadecimal diagnostic revision|
|F2 00|Second byte: bit0 RUN,bit1 PLL locked,bit2 diagnostic fault,bit3 sequence exhausted|
|F3 00 / F4 00|Generation low/high|
|E8 A5 5A|ARM once while stopped; increments generation|
|E9 A5 5A|STOP; common transport reset and SNES output disable|

Bad keys, partial bytes, short packets and extra bytes do not ARM.
ARM while already running has no effect. Generation65535 refuses another ARM; reconfiguration
is required. The boundary test checks generations1→2→3, not the65535 rollover.
Generation is configured to0 and retained across STOP/PLL loss.
PLL loss gates outputs immediately even when the84MHz clock stops, clears RUN, and requires
explicit re-arm after relock. Physical analog PLL lock behavior is not modeled in the RTL test.

The033 producer/queue/CDC/stage/frontend source bytes are unchanged.
Program ROM reads select LoROM banks00..3F/80..BF, address8000..FFFF, ROMSEL active.
The64KiB original ROM is represented by24KiB of initialized storage; unstored regions returnFF.
The builder and RTL test independently check all65536 bytes, plus bank80/81 mirrors.
Program/epoch/transport data are multiplexed with separate receive and drive directions.
Writes select receive direction without driving FPGA data onto the bidirectional SNES pins.
Unused ROM/RAM writes and enables are inactive, memory data pins high impedance, DAC/IRQ low.

Read-only bank00:600B/600C exposes generation. The034 ROM reads that pair before each acquire
and writes it into the unchanged031 host-stage epoch registers.
The program is derived reproducibly from pinned033 builder bytes in ignored output.
It has a readable NES H1 034 title; it does not change the NES display policy.

## Portable MCU code

src/nes/firmware/nes_h1_session.c is implemented and compiled/tested as host C.
Its platform callbacks still need binding into the actual STM32 firmware.
start asserts RESET, configures /sd2snes/fpga_nh1.bi3, performs a bounded identity wait,
checks revision/IDLE/generation, arms, and releases RESET only after RUN and incremented generation.
Failures keep RESET asserted; post-ARM failures attempt STOP without hiding the first error.
stop asserts RESET and verifies STOP, leaving RESET held for the caller's menu-image restoration.
The module itself does not restore the menu, write SD files, or change any GBC image.
No firmware menu hook, full ARM build, compressed FPGA image or deployable package is claimed here.

## Actual evidence and timing limits

Questa actually executes the84MHz boundary with injected clock-enable and PLL-lock inputs:
identity/framing negatives, one-shot ARM,64KiB ROM/mirror reads,3 pattern pages, STOP during
held read, fresh generation, and clock-stopped PLL loss/re-arm. Logical SNES reads use180ns
low and20ns address setup/hold; that waveform is not a measured console pin envelope.

Mesen executes the034 ROM twice at modeled epochs1 and2. Its Lua MMIO model is an explicit
adaptation of033's pinned observer. It receives the first3 pages captured from034 RTL,
repeated for6 displayed pages; this repetition is a diagnostic fixture, not a NES frame-drop policy.
Each run captures7 exact screens and verifies60-frame progression. It is not timing-coupled
RTL/Mesen co-simulation. The model retains its assumed21478-clock fill and200-clock commit delay.

Quartus actually maps/fits the physical top and runs STA at the real8MHz/84MHz clocks.
There are no virtual pins, false paths, multicycle exceptions or clock-period relaxation.
Internal setup/hold/recovery/removal/pulse-width slack is positive across reported corners.
However38 input ports/804 input paths and11 output ports/933 output paths are unconstrained,
and MTBF coverage is incomplete. Positive internal slack and STA warnings0 do not constitute
external SNES/SPI setup/hold/turnaround or CDC/reset signoff.

QSF adds Quartus synchronizer identification, but one queue_up_h assignment is ignored after
same-clock optimization. Original031 async_reg attributes still produce warnings.
Unused external-memory pins/constant outputs and ROM write ports also produce documented warnings.
Review synthesized chain endpoints, actual pad delays and the console/MCU timing envelope next.

Reproduction tools:
- build_nes_h1_board.py --out FRESH_BUILD
- run_nes_h1_board.ps1 with explicit Build(FRESH_BUILD/build), Out, Python, FloatWrapper, QuestaBin
- run_nes_h1_board_client.py --build FRESH_BUILD/build --out FRESH_CAPTURE --epoch 1 (or2) --mesen EXE
  (place actual RTL payload bytes as FRESH_BUILD/board-payload.bin; no generated replacement)
- nes_h1_board_resource.py --build FRESH_BUILD/build --out FRESH_FIT --quartus-bin BIN
- Host C test: compile nes_h1_session.c plus h1_session_test.c with the header in include path.
  Recorded run used MSVC x64 /W4 /WX /std:c11.
- verify_nes_h1_board.py --root PRESERVED_EVIDENCE --out RESULT.json

The next deliverable must bind the MCU callbacks/menu recovery, constrain and review actual IO
and synchronizers, then build the same candidate's full firmware/FPGA package and recovery guide.
