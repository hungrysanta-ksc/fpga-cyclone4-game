# Mapper4 video workloads and offline packet admission021

SPDX-License-Identifier: MIT.

New original NES Mesen reference runs only. Existing core014, SNES020, source ROMs and upstream remain unchanged.
Do not claim new RTL or SNES execution from these results.

## Variants
build_nes_video_workloads.py derives from the project's MIT original009 builder.
baseline: same functional zero-scroll two-group BG.
fine_x: CPU sets horizontal scroll1 at initialization and each NMI service.
sprite: CPU installs OAM entry(y79,tile1,attribute0,x40) and PPUMASK1E.
split: actual MMC3 IRQ handler changes R0/R1 to the opposite BG group while rendering.
banks32: immutable CHR grows to32KiB; CPU cycles groups24,0,8,16 in captured frames6..9.
All other PPU palettes use the same four distinct reference colors. CHR bytes remain original generated data.

## Reproduce
Use the existing isolated Mesen runtime; absolute fresh ASCII capture paths are required by Lua I/O.
For each baseline/fine_x/sprite/split/banks32:

~~~powershell
python -B tools/build_nes_video_workloads.py --case <case> --out <fresh-build>
python -B tools/run_nes_video_workloads.py --mesen analysis/local-mesen/Mesen.exe --probe <fresh-build> --out <fresh-ASCII-capture>
~~~

Arrange evidence as <runs>/<case>/build and <runs>/<case>/capture.
python -B tools/verify_nes_video_workloads.py --runs <runs> --out <fresh-json>
Final published result uses verification-final.json; initial admission/verifier/results are preserved as historical iterations.

## Observation and audit
Lua records actual CHR physical read addresses/values, CPU mapper/PPU writes and endFrame mask/ctrl/scroll/counters plus full256x240 RGB.
The scroll latch is tracked from actual2002reads and2005/2006writes; fixtures use paired writes, no observer-forced state.
Auditor checks ROM hashes, declared CHR geometry, byte values and all241*68 BG pattern slots/frame.
BG slot coordinates use the existing zero-scroll helper only as a candidate conversion.
Fine-X actual framebuffer disagreement demonstrates why that helper cannot be treated as a general renderer.
AllCHR capture also includes sprite/dummy fetch; reported LRU policies apply ONLY to BG patterns.

## Conservative admission
nes_video_packet_admission.admit takes one frame's full BG events, immutable CHR bytes,
observed control evidence and a full240-row reference indexed framebuffer.
It rejects absent control fields, nonzero scroll, sprite/unsupported mask, alternative BG table/nametable,
active PPU writes, mutable/oversizedCHR, incomplete cadence, mixed frames, nonmonotonic ticks, inconsistent address/tile/value/coordinates.
Only after those checks does it call the historical020 packet primitive and compare all restored pixels.
Unsupported cells and full-frame mismatch also reject. Rejected frames produce no packet.
This is an offline reference-assisted gate, not runtime validation or a universal safety boundary.
It does not retrofit020's historical entrypoint. The old020 fixed-ROM/full-golden preconditions remain intact.

The twelve negative tests include removal of an unused fetch: the primitive can ignore that fetch,
but the full new admission gate now requires complete cadence. Initial gate/verifier revisions are retained.

## Scope
Twenty reference frames, four accepted static BG frames, sixteen explicitly rejected unsupported frames.
Rejecting a workload does not implement that feature or establish hardware/game compatibility.
No commercial ROM access, Questa license session, physical queue/service, CDC, final palette, full240 simultaneous display or board fit/STA.
Next implement and replay the fine-X representation before treating current static packets as a general live bridge.
