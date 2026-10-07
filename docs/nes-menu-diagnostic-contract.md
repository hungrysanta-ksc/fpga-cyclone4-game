# NES062 manual load/verify diagnostic contract

062 connects the candidate-aware SD function to the three manual menu routes. It is a compile/test candidate, **not an installable MCU/FPGA pair**. CPU/PPU never RUN. The061 board RTL and044 H1 route remain unchanged.

## Entry and identity

Exact basenames `NES VERIFY 062 80.nh1` and `NES VERIFY 062 96.nh1`, case insensitive, select fixed read-only files `/sd2snes/nes/fine_x.nes` and `/sd2snes/nes/banks32.nes`. The marker contents are unused. No new marker or ROM files are installed by these tools. Browser visibility uses the existing NH1 filter; file selection, recent items and favorites each intercept before normal ROM loading and before adding to recents. Existing044 markers use the old H1 path. All NH1 autoboot remains NACK.

The selected geometry must match the approved iNES header and whole CRC before FPGA configuration. The new FPGA path is `/sd2snes/fpga_nlv.bi3`; it intentionally differs from044's `/sd2snes/fpga_nh1.bi3`. Before BEGIN, actual SPI must return **CF61/F0A5/F144/protocol59**, empty count and idle flags. Values60/44/zero, incorrect legacy IDs or protocol are rejected without BEGIN/DATA. CF identifies a protocol candidate, not the SHA256 of the installed image. Final paired-image hashes remain required.

The generator derives a new062 entry from frozen060. It preserves the entire044+056 prefix,256-byte SD buffering, repeated header/size/CRC/close gates, ordered comparison ACK, FINISH, STOP and base token recovery. It never adds DATA/ACK retries or calls START. The old uncalled056 entry remains historical code and is not the new menu route.

## Lifecycle and reporting

`nes_menu_diagnostic_run` is synchronous and rejects a pending second entry. Its true return permits menu reload, including safely recovered test failures. It does not mean verification passed. Base recovery failure returns false, leaves RESET/USB protection held, prints the RAM report over UART, and does not write SD or continue to the menu.

The main loop reloads the menu and prepares mapper/configuration as before. A nonzero menu load and reliable SRAM are required before `nes_menu_diagnostic_prepared` permits RESET release. The final ELF has three calls from main to the new run function and a call from run to the actual SD probe; this is stronger evidence than retaining an unused symbol. The main loop also calls preparation and release reporting. It is ARM call-site/host evidence, not execution on STM32 or a physical SNES menu observation.

The report distinguishes candidate/observed CF, requested geometry, load/file error, acknowledged/compared byte counts, verify error, verification, END, STOP, base attempt/restoration, safe-to-reload and menu boundary. `PREPARED_RESET_HELD` precedes RESET release; `RELEASE_BOUNDARY_REACHED` means the code reached that boundary, not that a user saw a working screen. After safe recovery, a separate local FIL writes `/sd2snes/nes-verify-last-062.txt`, temporarily disabling USB IRQ and restoring its original state. Log open/write/short-write/close errors are printed over UART and do not prevent recovery. The report is written at both boundaries so an earlier preparation report can survive failure to open the later log. This is not atomic/power-loss-safe logging.

UART gives a pre-run wait warning and final results. **There is no new on-screen result/progress display or implemented cancellation input.** RESET-held SNES pad/button behavior is not assumed. Explicit SPI delays alone total113.9/136.6 seconds for80/96KiB, plus SD/configuration/calls and any additional polls; this is not a measured hardware duration or upper timeout bound. Existing `fpga_pgm` panic and FatFS blocking behavior still need a deliberate termination policy.

## Reproduction

Fresh output directories are mandatory. Host and GPIO tests generate the two original public diagnostic fixtures; no private NES CPU core or user ROM is needed.

```text
python -B -X utf8 tools/nes_menu_diagnostic.py --out <fresh-host> --gcc <host-gcc>
python -B -X utf8 tools/nes_menu_diagnostic.py --out <fresh-bad-CF> --gcc <host-gcc> --mutation candidate
python -B -X utf8 tools/nes_menu_diagnostic.py --out <fresh-bad-menu> --gcc <host-gcc> --mutation menu-release
pwsh -File tools/run_nes_menu_diagnostic_wave.ps1 -Python <python> -FloatWrapper <approved-wrapper> -QuestaBin <questa> -Out <fresh-ASCII-wave> -HostRun <fresh-host>
python -B -X utf8 tools/prepare_nes_menu_diagnostic_arm.py --baseline <verified-private060-ARM-tree> --out <fresh-ARM>
pwsh -File tools/build_nes_menu_diagnostic_arm.ps1 -SourceRoot <fresh-ARM> -ArmBin <ARM-bin> -HostGcc <gcc> -Make <make> -UnixBin <unix-bin> -MiniImage <hash-approved-mini>
python -B -X utf8 tools/verify_nes_menu_diagnostic.py --evidence <frozen-private062>
```

The ARM input is the hash-verified private060 preparation and pinned sd2snes platform/toolchain. Public clone alone does not supply that input. The final verifier audits saved sources/logs/manifests; it does not run new tests. The public builder also verifies disassembled call sites; this run performed those checks after linking, with the original executed builder retained separately.

## Remaining hardware gates

061 production SV hashes match; reuse its186LAB/44M9K physical fit/internal STA without a new fit.54 input/49 output ports remain externally unconstrained. The actual part, pin/electrical timing, readable observation/cancel/blocked-call policy, full80/96KiB real C→board success, FPGA ASM/compression, paired package, SD backup/rollback and physical reentry/GBC recovery remain open. The bounded GPIO CHECK setup uses testbench loader pin writes for96KiB, then actual C verifies256 bytes before SD error; it is not a complete C load/verify success. The059 full-core959LAB/4LAB budget remains separate.
