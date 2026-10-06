# NES053 diagnostic ROM boot contract

Candidate `NES-R1-ROM-BOOT-053`. Preserve044 hardware and all044–052 checkpoints.

## Implemented boundary

`nes_rom_loader.sv` accepts a byte stream in the memory-clock domain and writes a fixed diagnostic image through physical PSRAM pins. `nes_rom_boot.sv` grants those pins exclusively to the loader while stopped and to unchanged052 read/CDC logic while running. This is a loader RTL interface, not a connected MCU/SPI firmware loader. No real board top/clock connection or new SD image is included.

Controls load_begin/load_chr32/load_valid/load_end/start/stop and load_data must be synchronous to mem_clk. load_valid is consumed only with load_ready during RECEIVE; backpressure during WRITE/HOLD is permitted. A BEGIN in IDLE/READY latches16KiB versus32KiB CHR mode and clears loaded_bytes. The stream is exactly65536PRG bytes at0..FFFF, followed by16384/32768CHR bytes at200000..203FFF/207FFF. It preserves052 chip/lane layout: byte bit1 selects chip, byte bit0 selects high/low physical lane respectively. Only the selected byte enable is active during writes.

Each accepted byte latches address/data, asserts WE for3memory clocks, keeps CE/address/data/byte-enable for1hold clock with WE high, then releases pins for at least1clock before another write. loaded_bytes advances only after the hold completes. Reaching the byte count alone leaves loaded/run low. END is accepted only at the exact completed count with no active write. It sets loaded, but START is separately required to enter RUN. No CRC/readback engine is in hardware; loaded means the stream length and write sequence completed, not verified data integrity. The future MCU loader must validate its source and the physical readback policy.

While RUN, writes are blocked and052 serves reads. STOP during RUN returns to READY, cancels pending reads through common reader reset, and preserves immutable ROM for restart. The caller must also reset the NES core/cache/packet pipeline; the integration uses reset_request=boot_reset || !run_enable, retaining049 RAM scrub before core release. STOP in RECEIVE abandons the image. STOP during WRITE/HOLD records error6 and drains the accepted write before releasing pins. BEGIN permits replacement only when stopped.

| Error | Meaning |
| --- | --- |
|1| BEGIN outside IDLE/READY |
|2| END before exact count or during an active write |
|3| START before READY |
|4| Data in IDLE/READY/RUN or beyond the fixed length |
|5| Conflicting control commands |
|6| STOP during active write/hold |

Faults are sticky until common reset. A fault during WRITE/HOLD finishes the pulse and hold, then disables pins; it cannot enable RUN. The command-observation edge may extend the pulse, but must not shorten it. External common reset is the deliberate exception: it immediately releases pins and invalidates the whole image; an interrupted byte may be incomplete and must never be reused as a loaded image. There is no independent-domain reset policy or save-data preservation claim.

## Evidence

Final unit check360505 passes with180226byte reads: complete64KiB PRG+16KiB CHR and64KiB PRG+32KiB CHR readback through052, plus2restart reads. Eight invalid-command scenarios cover all6cause codes, including draining bad END and STOP during a write. Reset during write, load completion before START, stop/restart with a read pending, run-time write rejection, byte mapping and pin ownership are checked. The memory model starts uninitialized and is populated only at PSRAM WE release edges; it asserts minimum write pulse and rejects unknown write data or read/write conflict.

Actual NES execution loads98304bytes for banks32 and81920for fine_x through the same pin model. The test checks every written byte before START, then executes2ROMs/8frames. No RAM preload/readmemh exists in the memory model; fixture files feed loader input and independent expected-data checks only.491520pixels match052 and16064packet bytes match except release timestamps. Per-frame release tick offsets versus052 are {'banks32': [-4, -4, -4, -4], 'fine_x': [1, 1, 1, 1]}; all S/E/F/D event ticks have the same per-case offset with all other fields equal. The core divider already runs during reset, so differing load duration changes release phase; do not claim unchanged timestamps. Measured runtime ROM read latency remains4NES clocks under052's25ns model assumption.

Initial unit failed only at its final negative stimulus, because a command did not cross a sampling edge. Corrected negedge alignment and added safe write drain tests; preserve the old failure and source. Initial actual-core compilation failed on run_enable forward declaration; both wrappers now declare it first. Final actual-core, unit and resource evidence use exact final production RTL. The initial successful resource run is preserved too.

Final diagnostic fit13612LE,929/963LAB,5016registers,26M9K,182922memory bits,293virtual pins,22unlocated physical pins,PLL0.34LAB remain. Compared with052, LE+65/LAB+4/registers+57. The16bidirectional data pins cannot be virtualized and are real but unlocated IO in this area probe; that is not a board pin binding. No new loader/boot map warnings or10036/10240 warnings are accepted; inherited warnings remain. Earlier052/051 timing-failure controls and all GBC152hashes remain frozen.

Nominal clocks remain46.560846ns NES and11.904762ns memory, with existing1ps simulation rounding to46.560/11.904ns. Three write clocks are35.712ns and one hold clock11.904ns in the model. Actual PSRAM tAS/tDS/tWP/tDH/tAA/turnaround, bundled CDC routing, reset and real IO timing remain unverified. No electrical signoff follows from this digital pin model.

## Next step and reproduction

Materialize044's generated boundary, add MCU/SPI stream and load-completion/error telemetry, and bind the loader to board reset/run control. The existing top exposes SNES_SYSCLK at PIN_A9 and CLKIN for the8MHz-to84MHz PLL, but SNES_SYSCLK frequency/routing and supported console region must be qualified; it is not bound or qualified here. Do not substitute84MHz/4 for the NES master. Add the real NCR1 SNES consumer/deadlines and recovery path, then fit the complete real-pin board and constrain memory/CDC timing before a recoverable hardware trial. The old044 program/pattern must not be mistaken for that consumer.

Use run_nes_rom_boot_checks.ps1 through approved Starter FLOAT for units. Use run_nes_rom_boot.ps1 -Mode live -Delay3 -PhasePs3500 for actual cores. Resource: nes_rom_boot.py resource --out <fresh ASCII path> --quartus-bin <path> --phase-ps3500, without --delay. Verifier: tools/verify_nes_rom_boot.py. Do not flash053: no hardware image exists.
