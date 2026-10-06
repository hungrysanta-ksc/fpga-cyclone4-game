# NES early ROM read051 contract

Candidate `NES-R1-ROM-EARLY-051`.044 remains the hardware baseline.

## Causal scheduling

`src/nes/nes_rom_early.sv` derives the original050 service without changing its one-outstanding-request protocol, geometry, response/tag checking, cache capacity, reset/timeout or sticky faults. New inputs permit reads from current core addresses before the actual data strobe. These are immutable memory reads, with no future trace, precomputed packets or predicted mapper state as input.

CPU address qualification is the explicit NES export `prg_addr[15] && prg_allow`. PPU address qualification is the explicit PPU export `ALE && !vram_w`, forwarded through NES/probe. The service uses the CURRENT post-mapper physical address. Address changes or mapper changes before demand still require a matching physical tag; an early response for an old address cannot validate the new one. ROM contents must remain immutable until common reset invalidates both caches.

Priority is PPU actual demand, CPU actual demand, PPU early-only request, CPU early-only request. An already accepted read cannot be preempted. The actual CPU/PPU sampling taps and failure decisions remain050's. There is no NES pause/clock slowdown or frame dropping. As in050, a fault stops new grants but the eventual board caller must abort/discard the affected frame and handle recovery; this testbench stops on the next edge.

All backend signals still share the NES master clock. `rom_request` is a ready-qualified grant strobe, not held-valid. Common reset must flush backend replies. There is no asynchronous CDC, epoch protocol, PSRAM pin controller, loader or save policy in051. Preserve050's diagnostic64KiB PRG/32KiB CHR and049's RAM-reset restrictions.

## Measured behavior

Two-, three- and four-clock registered-response backends pass banks32/fine_x,8frames per condition. Each run matches050's491520pixels,16064packet bytes and complete live.tsv exactly. Each condition handles624788 requests, only170 more than050's624618 at its faster one-clock backend. CPU and PPU bytes are checked against ROM data at valid sampling edges.

The unchanged050 scheduler still fails the two-clock backend.051's eight-clock backend fails. Thus2/3/4 clocks are tested passing settings and8 a tested failing setting;5–7 were not characterized for these finite workloads; this is not a universal hardware timing limit. One test clock is46.560846ns. The physical controller, turnaround, faster memory clock and CDC must be budgeted together rather than equating these numbers to memory-device tAA.

| Schedule | ROM | Reply clocks | Error | Decision tick | Observation tick |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline | banks32 | 2 | 2 | 852269 | 852270 |
| baseline | fine_x | 2 | 2 | 852269 | 852270 |
| slow | banks32 | 8 | 2 | 852205 | 852206 |
| slow | fine_x | 8 | 2 | 852205 | 852206 |

The recorded050 banks32 failure is causal: CPU read0xE187 grants at tick852264; PPU demand for0x201FF2 appears at852266 while it is pending. The CPU response and PPU grant occur at852267. PPU samples at852269 while response is still low and its tag invalid. The model registers the two-clock response only after that edge, too late for the sample. The next-edge Fatal shows0x201FFA, which is not the failed read address.

The test-only16-entry ring stores inputs before each clock edge. Nonblocking writes plus dumping inside the fault observer preserve the previous16edges, ending at the actual decision tick. The ordinary Fatal's bus addresses are one edge later and must not replace that history. Initial observer placement raced the simulator's Fatal and emitted no history; preserve that initial baseline and the executed driver. Only the observer changed afterward. Production HDL is identical in all three normal tests and fit. Live2/fit used the archived pre-fix driver; live3/live4 and final failure recordings used the fixed driver.

Unit checks4168/525requests retain all050 six fault categories and256CPU/PPU cache pairs; add all4actual/early priority combinations, early reads without strobes, changed-address stale response rejection and later demand hitting a completed early entry. This is bounded simulation coverage, not formal equivalence or general NES game accuracy.

The initial Delay4 exploration was configured to expect failure, but banks32 passed all4frames. The runner stopped only because that expectation was false, before fine_x. Preserve the untouched probe and its result. A completion driver validates and reuses those exact banks32 logs/pixels, then runs fine_x with the same source hashes. A nonzero harness exit alone is not a hardware or license failure. Delay5–7 remain uncharacterized.

## Resources and next gate

Joint fit13420LE,935/963LAB,4895registers,26M9K,182922memory bits,282virtual pins,5unlocated physical pins,PLL0. Against050, LE falls118 while LAB increases7; capacity is determined by placement, so LAB headroom is28, not an area-win claim. No new10036/10240 warnings; existing core/startup/port/RAM warnings remain preserved. This is not whole-board fit or STA.

Next connect a concrete physical memory/faster-clock/CDC service within the measured request-to-sample windows, preserving the eight-clock failure as a negative control. Measure it jointly with real pins/PLL and error recovery before loader/epoch/SNES consumer integration and a recoverable hardware package. OAM initialization, save retention,240-row output, DMC/IRQ accuracy and per-file HDL adoption holds remain open.

The next physical-path experiment must retain the NES master period46.560846ns;84MHz divided by4 would be21MHz and is not an equivalent clock. The existing GBC psram_rw3 uses three read clocks plus a release interval, but its timing is an assumption for an unidentified part. Budget request synchronization, grant, pin access, response capture and return synchronization explicitly. Sweep independent clock phase, verify stable bundled address/data and common-reset cancellation, and measure sampling-edge slack before claiming this path meets051. Preserve GBC sources as references only.

Reproduce through `tools/run_nes_rom_early.ps1`: live/Delay2,3 or4, baseline/Delay2, negative/Delay8. Unit uses `tools/run_nes_rom_early_checks.ps1`; fit uses `tools/nes_rom_early.py resource`. Use the approved Starter FLOAT wrapper and fresh absolute ASCII job paths. Current verifier `tools/verify_nes_rom_early.py` checks raw evidence and frozen044–050 manifests with saved statuses. GBC152protected files and044SD images remain unchanged.
