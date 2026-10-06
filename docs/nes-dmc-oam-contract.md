# DMC/OAM contention contract

SPDX-License-Identifier: MIT.

NES-P2-DMC-OAM-017 checks bounded arbitration and continuation using the unchanged
NES-P2-RDY-014 core. Its separate runtime_timing_match field is false: actual Mesen and
RTL DMC refill phases differ. A true passed/arbitration_passed value never means full
DMC/APU timing conformance. Keep this unresolved difference visible in downstream status.

The original ROM programs the actual APU with rate15, no IRQ/loop, sample addressC000,
length17. It delays0/40/100/180 NOPs before a real $4014 write with two padding variants.
There are8cases; page and OAM start are coupled to case index, not a full parameter matrix.
After completion each channel is disabled and allowed more than432cycles to drain the
sample buffer. Playback is intentionally stopped before all17bytes have been fetched.
No DUT signals are forced. Rendering is disabled, SEI masks CPU IRQ and memory is ideal.

Observation:
- dma-bus.tsv has cart_ce tick/effective address/read/data/case/CPU address/read/pause/DMA/put.
- arbitration.tsv has the same tick/case, actual DMC request/ack/address, sprite and DMC
  controller states, input data, sample buffer and have_buffer. These are read-only observations.
- oam.tsv records completion value, OAMADDR and256 physical OAM bytes per case.
- Mesen callbacks are read-only actual runtime CPU reads/writes plus OAM snapshots.
  Exec callbacks exist in the raw trace but do not establish instruction retirement.
- Case comparison starts at its $4014 write and stops at the RAM$20 completion write.

Independent expectations come from deterministic ROM source bytes, physical OAM attribute
maskE3, the256ordered read/write pairs, and the bounded arbitration schedule: DMC occupies
an OAM get slot, its following put slot is idle, then the displaced OAM read occurs.
Each observed overlap therefore adds2cycles to that timeline's513/514cycle pause.
The verifier checks this separately for RTL and Mesen rather than pretending that their
request times match. It also checks actual RTL priority/grant/ack, next sample-buffer latch,
source progression fromC000, CPU hold, and one post-DMA INC$10. Ten corruption tests
must fail. Exact refill phases and sample indices are compared and retained as a distinct
false timing-match result. First byte0 enable+5 agrees; byte1 +123/+275 does not.

Require explicit simulator PASS with no Fatal/Error and zero period/unknown counts,
plus verifier pass for the limited scope. Existing42full-core warnings remain. Simulator
exit0 alone is insufficient. Initial verifier off-by-one and initial instrumentation are
preserved; final raw traces were not edited. Additional instrumentation does not change ROM/core.

Reproduce with fresh absolute ASCII output directories:

```powershell
& $PY -B -X utf8 tools/build_nes_dmc_oam.py --out $ROM
& ./tools/run_nes_rdy.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out $RTL -Diagnostic $ROM -Testbench tests/nes-functional/dmc_oam_tb.sv
& $PY -B -X utf8 tools/run_nes_dmc_oam_reference.py --mesen analysis/local-mesen/Mesen.exe --probe $ROM --out $MESEN
& $PY -B -X utf8 tools/verify_nes_dmc_oam.py --rom $ROM --rtl $RTL --mesen $MESEN --out $REPORT
```

Use installed tools and existing authorized FLOAT wrapper paths from AGENTS.md and
questa-execution.md. No new license or recurring smoke check is needed. Preserve original
licenses and exclude license-route.local.json/server logs from source and evidence copies.
Generated adapted HDL, ROMs, emulator and raw logs remain ignored. The prior016manifest
was checked before mutable status was snapshotted. Full fit/STA, hardware, SMB3, NES-to-SNES,
DMC start/end collisions, IRQ/loop/wrap, abort, RMW, controller side effects, audio accuracy,
rendering writes, arbitrary memory stalls and licensing holds remain open.
