# NES063 full C-to-board session verification

This test captures the unchanged062 C manual-menu diagnostic and replays its
SPI transactions through the061 physical diagnostic top. It is a digital
load/CHECK-only test, without CPU/PPU RUN or an installable SD pair.

## Captured source and timing

`tools/nes_board_session.py` compiles the actual062 menu, SD probe, SPI and
verification C with a host SD/GPIO platform. Both approved fixtures are read
from their iNES headers through complete loading, reread validation, byte
comparison, FINISH, STOP and base recovery. Menu preparation/release are host
callbacks; they do not simulate a physical FPGA reconfiguration or SNES menu.

The compact trace records CS start/end,16/64bits, all MOSI bits and the MISO
samples consumed by C. Within active frames, the capture validates MOSI
transition times, SCK rising-edge times, sample times and CS boundaries against
the2us GPIO delay template. SCK falling-edge order requires the sample to have
occurred; its time is reconstructed from the unchanged C template. Replay rebuilds
that template without shortening time. The command-byte MISO is unused by C;
all response bits after it must match the captured model. This verifies the
assumed explicit GPIO delays, not physical STM32 execution or wall time.
GPIO mode/latch restoration outside SPI frames is checked by the host platform;
the replay ends with the diagnostic top after STOP. It does not replay physical
base-FPGA configuration, alternate-function handoff or menu reloading.

## Clocks and models

The loader SPI decoder and PSRAM state machines run continuously at8MHz,
including every idle period. Pin RAM starts uninitialized and only real WE
pulses populate it. Every write/read chip and sequential address is checked.
Writes use byte strobes; reads enable both word lanes and select the byte
internally. All returned byte/tag bits and final RAM bytes must match the
independently generated fixture.
The delayed pin model uses70ns read,35ns disable and350ns minimum WE pulse.
These are test assumptions, not the identified device's min/max datasheet.
The nominal replay uses one oscillator phase and reconstructs only explicit C
delays. It does not model SD/CPU execution latency, interrupt jitter or a sweep
of asynchronous phases; those belong to the remaining timing review.

`--mask-link 1` gives only the reset-held H1 transport separate test clock
expressions. It does not force an input port: forcing a collapsed input net
could stop the shared PLL clock. The raw first failed trial is retained.

`--park-legacy 1` stops the digital84MHz legacy/H1 stub after CF61/F0A5/F144.
Every later command must be a loader6x command and every response sample must
select the8MHz loader reply. RUN remains forbidden. This reduces simulation
cost in a domain unused by this diagnostic; it is not a physical clock design
change, PLL qualification or a free-running full-board waveform claim.
Use `--park-legacy 0 --mask-link 0` for a baseline comparison. Record the test
transform separately from unchanged production RTL hashes.

## Commands

Use fresh ASCII output directories and the established Starter FLOAT wrapper;
one licensed job at a time. Repository-relative paths below are entry points;
the wrapper/job paths passed to PowerShell must be absolute.

```text
python -B -X utf8 tools/nes_board_session.py --out HOST --gcc GCC
pwsh -NoProfile -File tools/run_nes_board_session.ps1 -Python PYTHON -FloatWrapper WRAPPER -QuestaBin QUESTA -Out REPLAY -HostRun HOST -Case fine_x -MaskLink 1 -ParkLegacy 1
```

Repeat for `-Case banks32`. `-LimitFrames N` only verifies a prefix and must
never be counted as complete success. Full completion requires exact frame,
DATA, physical write/read and ACK counts, END, verified FINISH, cleared STOP,
idle peripheral ownership, all response bits and every final RAM byte.

External IO constraints, actual device timing, blocking-call recovery,
visible progress, final image packaging and hardware observation remain
separate gates in the [readiness guide](development/NES-HARDWARE-READINESS-REVIEW.ko.md).
