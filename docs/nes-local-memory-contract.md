# NES local memory049 contract

Candidate: `NES-R1-LOCAL-MEMORY-049`. Hardware baseline remains044.

`src/nes/nes_local_memory.sv` is shared by actual-core RTL execution and the joint resource top. It replaces047/048's separate ideal local arrays and resource-only RAM instances. External ROM still uses ideal synchronous data in simulation and virtual ports in fitting. This module does not implement a physical PSRAM controller, loader or memory handshake.

| Core physical address | Memory | Capacity |
| --- | --- | --- |
| CPU 0x380000–0x3807ff | CPU RAM | 2KiB |
| CPU 0x3c0000–0x3c1fff | PRG RAM | 8KiB |
| PPU 0x3a0000–0x3a07ff | CIRAM | 2KiB |

Other addresses select the caller's external data and cannot write these RAMs. Local reads are synchronous, one clock, with old data on a simultaneous same-address write. CPU and CIRAM can write concurrently. There is no local ready/stall handshake: the caller must retain the existing NES memory sampling contract. The fitted M9K parameters explicitly use single-port OLD_DATA, with2+8+2 blocks for these memories.

On reset assertion `init_done` drops asynchronously and output data is masked to zero. Reset release must be synchronized to the NES master clock by the eventual board wrapper. The RAM arrays have no reset/initialization statements. On the first8192 edges after release, the address counter writes zero; the2KiB memories clear on the first2048 edges. The last PRG RAM write and `init_done` assertion happen together. The core and packet pipeline remain reset until completion; the memory controller itself uses the external reset, avoiding a reset feedback loop. At46.560846ns per clock this takes0.381426ms, excluding caller reset synchronizer latency.

This diagnostic policy clears PRG RAM on EVERY reset. It must not be adopted for battery-backed game saves without a separate cold/warm/save policy. The core's OAM arrays and evaluator are outside this module;048's OAM initialization issue remains open. No complete board warm reentry or asynchronous clock-domain release has been proven.

The unit test executes153604 checks: full12KiB zero scan after three completed scrubs, interrupted scrub restart, full-address patterned writes/readback, simultaneous CPU/CIRAM accesses, same-address old-data behavior, boundary fallback/no aliasing, reset assertion and writes held during scrub. No hierarchical array initialization is used.

Actual accepted048 core +047 tap +046 encoder +045 producer +044 transport runs banks32/fine_x afresh:8frames,131104fetches,16064bus bytes,491520pixels. All pixels and packet content except release timestamps match048. Each release timestamp and S/E/F/D event is4master clocks later relative to the tap counter. The core CPU/PPU dividers continue while reset is asserted; extending reset changes release phase. Preserve this measured offset, not an exact full-trace equality claim or an absolute hardware timing calibration. No pause/drop mechanism was added. SNES consumer remains testbench bus stimulus.

Joint diagnostic fit:13477LE,920/963LAB,4811registers,26M9K,182922memory bits,237virtual pins,5unlocated physical pins,0PLL. Compared with048, LE rises194 and registers14; LAB falls6 due to placement/packing. This is not a194LE area saving or guaranteed43LAB board budget. No STA/full board IO signoff. Existing276020/276027 RAM warnings and startup simulation warnings are preserved; no10036/10240 warnings were introduced.

Run `tools/run_nes_local_memory.ps1 -Mode unit|live` with the existing approved FLOAT wrapper and fresh absolute ASCII output path. Run `tools/nes_local_memory.py resource --out ... --quartus-bin ...` for fitting. `tools/verify_nes_local_memory.py` is the current checkpoint verifier. Frozen044–048 manifests use saved status snapshots. Initial unit run and failed declaration compile are retained separately; final unit/live/resource share identical local-memory HDL. GBC files and044 SD pair remain unchanged.

Next: external ROM arbitration/response deadline and loader contract; real NES/host clock/reset/epoch integration; actual SNES NCR1 consumer/CHR atlas and VBlank pacing; combined physical fit/STA then recoverable hardware package.
