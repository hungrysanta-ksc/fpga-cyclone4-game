# NES065 menu return contract

Compile-only diagnostic overlay; no installable SD image. The original044/056/062/064 publication sources and GBC hashes remain unchanged. Read [Korean result](../analysis/MENU-RETURN-RESULT.ko.md) and [current handoff](../cores/nes/HANDOFF.ko.md).

## Ownership and failure boundary

Manual entry saves the original USB IRQ state, disables USB and holds RESET before UART output. Active ownership survives candidate load/verify/STOP/base restoration and the menu reload. The real main releases RESET only after menu/readback/prepared logging pass, retains ownership during its100ms settling and status setup, and reasserts RESET on a subsequent native fault/CIC failure/SRAM reliability failure. Only the checked final return restores active LED ownership and the saved USB IRQ state.

The constrained return skips CIC/SD/CLI retry loops, unchecked recent/favorite parsing, redundant legacy base programming and cfg_save. Recent/favorite counts are0 in this return. Normal inactive branches retain their prior behavior. A failed diagnostic remains protected until external reset; there is no DATA/ACK/write retry or pad cancellation.

Menu loading retains the original classification/setup/tail and replaces only active transfer with an independent FIL/256-byte buffer and full SRAM comparison. Only MENU_FILENAME, flags0, mapper0/1, carttype0–2, payload≤4MiB and no supplemental core/SGb/EGBC are accepted. Whole load_rom execution on hardware is still pending.

SPI waits have25 ticks/1,000,000 polls per wait. TIM2 uses a requested-duration tick budget plus2 ticks and a finite count-derived poll fallback; stale UIF is cleared and CR1 stopped on failure. FatFS cache/allocation visits share6000 ticks/1,000,000 visits for menu preparation and1000 ticks/10,000 visits for the log. Ticks are100Hz, these are software limits, not measured physical timing guarantees. All IRQs are not disabled.

SD is buffered CMD17 read-only outside the explicit PREPARED log window. The window allows checked single-block CMD24, original four-lane DATA/CRC generation, accepted response token and bounded busy. Native SD/SPI/TIM2/FatFS failures block later IO and release. Ordinary optional file API failures leave RAM/UART observation available. SD stores PREPARED_RESET_HELD; after release the RETURN_READY_RESET_RELEASED report is RAM/UART-only and does not prove a displayed menu.

## Reproduction with explicit private input

Host lifecycle/trace generation uses public-generated diagnostic fixtures. The lower helper/ARM checks require the separately preserved hash-pinned materialized062 platform. That private tree, original menu/configuration files and frozen063 traces are not distributed here; these steps are not reproducible from a public clone alone. Use a new output directory for every execution.

```powershell
python -B tools/nes_menu_return_host.py --out <new-menu-host> --gcc <host-gcc>
python -B tools/nes_menu_return_host.py --session --reference <frozen063-host-02> --out <new-session-host> --gcc <host-gcc>
python -B tools/nes_menu_return.py --baseline <materialized062-root> --out <new-arm-root>
python -B tools/nes_menu_return_checks.py --platform <new-arm-root>/src --out <new-unit> --gcc <host-gcc>
python -B tools/nes_menu_return_checks.py --platform <new-arm-root>/src --out <new-mutation> --gcc <host-gcc> --mutation <menu-compare|log-release|sd-crc|fatfs-budget>
```

Use tools/build_nes_menu_return_arm.ps1 with SourceRoot, ArmBin, HostGcc, Make, UnixBin and the hash-verified MiniImage or QuartusBin arguments from064. Its temporary drive mappings must be unused and are cleaned up. Build results are compile-only. The recorded supplemental objdump checks disassemble get_fat and move_window into fat-get-disassembly.txt/fat-window-disassembly.txt and require both to call nes_return_io_step; load_rom must call nes_return_copy_menu. Three marker calls must reach the same run block through the recorded narrow/wide branch targets, not just a permissive call count.

```powershell
python -B tools/verify_nes_menu_return.py --evidence <frozen065-archive>
```

This audits immutable files and saved execution evidence; it does not run new hardware tests. Preserve failed preparations/builds/tests and the initial verifier filename error. Never rerun the one-shot065 finalizer over the archive or change older manifests.

The new full diagnostic SPI traces must equal063 byte-for-byte. Reusing the old board replay/fit is limited to that boundary and unchanged production RTL. Menu hardware SPI, MCU/SD/CPU delays, actual PLL phase and external IO still need physical qualification. Any new actual Questa job uses the authorized Starter FLOAT wrapper sequentially; do not repeat license smoke tests.
