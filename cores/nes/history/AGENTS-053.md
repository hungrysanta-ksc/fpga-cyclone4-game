# NES development instructions

- Continue in this existing independent checkout; preserve the upstream and original probe drafts.
- Before Questa simulation, use `tools/run_nes_functional.ps1` with the previously verified FLOAT wrapper. Read `docs/questa-execution.md`. The inherited uncounted license file is not the working execution path on this host.
- Run actual tests through the FLOAT server; do not repeat license smoke checks or ask for authorization already granted. A server stopped after a job is normal.
- Keep original license content and upstream files unchanged. Keep temporary server files, raw HDL experiments, ROMs, saves, and raw logs ignored. Use the explicit allowlist.
- Record the difference between compile, actual RTL execution, emulator reference, full fit/STA, and hardware verification. Never replace a failed test with a weaker success claim.

## Hardware diagnostic readability
- Manual hardware-test packages must show a readable candidate/page ID, visually distinct patterns, and an observable progress sequence with an explicit expected result.
- Noise-like byte-validation fixtures alone are not suitable for asking the user to judge hardware correctness. Keep them for automated comparisons.
- Include reference images captured from an actual emulator execution. Record inconclusive user observations as inconclusive, not as a hardware pass or a diagnosed hardware fault.

## Cross-boundary SPI verification
- Before an MCU/FPGA hardware candidate, replay the actual firmware's GPIO/clock/sample timing against the corresponding RTL. Independent host mocks and edge-only RTL sampling are not sufficient integration evidence.
- Preserve a known-bad candidate failure when fixing SPI timing. Compare response bits the firmware consumes; explicitly identify discarded command/dummy bytes.
- For H1 use the036 derived boundary from tools/nes_h1_spi.py, not the unmodified034 board HDL with035 firmware. The legacy pair returns a shifted identity at the actual +2us sample point.
- Keep Quartus Tcl job paths ASCII; copy an audit script into the private build directory before running it.

## H1 hardware delivery
- Preserve037/038/039 screen1/automatic-menu-return failures. Current041 is a paired MCU/FPGA diagnostic with protocol0x41/log041; back up039 MCU/040 FPGA, and keep marker037/title034 explicit. Never infer the FPGA version from the unchanged MCU log candidate.
- Before SD mutation verify the candidate pair, back up original target files outside the SD, and use the tested restoration path. Do not overwrite unknown firmware or changed recovery files.
- Package readiness and bounded hardware experiments are separate from electrical signoff. Preserve unknown IO/turnaround requirements and report physical results separately.

## Runtime failure evidence
- Preserve automatic-menu-return reports as hardware failures until explained. Do not treat a visible first page as a completed H1 pass.
- Collect a user-readable exit reason before further runtime guesses;038 records after base recovery without weakening the existing failure exit.
- Reused attachment filenames are not proof of new media. Compare bytes/hashes with prior evidence and never describe historical H0 video as newly observed H1 behavior.

- 038 establishes F2_STATUS/07;039 first-fault log establishes frontend1,stage0,producer0 with RD/WR/ROMSEL high.040 reproduces the same status with legal synthetic read release and fixes the false abort. Hardware causality still requires040 physical retest; synthetic stimuli are not measured hardware traces.
- Every future SNES frontend/boundary regression must vary ROMSEL and address at normal raw RD release while synchronized output_valid persists. Test simultaneous and delayed ROMSEL release across phases; retain early-release/active-deselect/address/conflict errors. Do not leave ROMSEL asserted throughout normal read tests and call termination covered.
- Snapshot address/control are capture-time values one clock after registered error observation, not necessarily the original offending transaction.

- 040 reported hardware retest failed before screen completion. Log still has frontend1 but ROMSEL low/address4080E0; its0x39 protocol cannot identify039 versus040 FPGA, and no SD hash was supplied. Do not claim040 fixed hardware or infer an exact offending transaction from the aggregate capture.
- Use041 pre-update cause/pending/raw-and-latched-address/position/strobe counters before another timing change. Preserve040 behavioral checks and real aborts. Same aggregate status reproduction alone is not proof of physical causality.

- Actual041 hardware log confirms protocol0x41 but aggregate frontend1 and causal0x20 (implies frontend2) disagree. Do not diagnose payload order from041 causal byte alone; addr_sync was not recorded and raw counters are not physical measurements.
- 042 is investigation only, no new hardware image. Same fitted041 netlist with SDF failed227bytes/617timing errors, unannotated control passed512bytes. Preserve notifier-enabled failure; asynchronous first-stage violations/X propagation alone are not proof of the physical root cause.
- Generated Quartus timing netlists can contain initial $sdf_annotate. Explicitly audit annotation mode in a control run; preserve the original netlist. Do not interpret optimized-away internal debug aliases as actual hardware SPI telemetry.
- Before another candidate, make error decisions and capture share a registered event and define coherent bus sampling; preserve normal termination and real-abort regressions.041 repeated flashing is not the next step.

- 043 implements two-sample bundled input qualification and ONE registered event for sticky error/first capture. Preserve accepted-write stable-release completion; the edge-only negative control loses a write after uncertainty. Keep early-release, active address/ROMSEL, collision, order and missing-response errors tested.
- Protocol43 D3..D5 is the sampled decision address, DB the event mask/response eligibility, DC..DE previous sample; D1 records issued/seen state. Do not decode as041 raw-address/counter schema or reintroduce first-stage diagnostic taps.
- Final043 RTL/MCU/board/fit pass, but annotated SDF fails91bytes/612first-stage-or-ROM violations while identical unannotated control passes512. Keep notifiers and failed evidence; no SD package or requested041 repeat. Trace first X and validate bounded binary resolution/skew before a new hardware trial.043 normal termination stimulus differs from042; byte counts are not a like-for-like regression metric.
- Acquisition bounds must cover2048 CDC request/response round trips. The intermediate20us gate bound was invalid; final043 uses1ms. Parent wall-timeout shutdown messages from a simulator are not evidence of a license entitlement problem.

## H1 sampling044 handoff
- 044 replaces the043 address-change predicate with a binary-equivalent stable-difference expression; retain4096 identity checks,576 binary resolutions,288 legacy-X negative controls and96 independent sample-delay cases. Keep936 normal/504 real-abort and shared-event regressions.
- Trace only retained primitive outputs and verify netlist connections and polarity. Fitted rd_sync/sel_sync/rd_previous q can be inverted relative to source; optimized-away aliases and q names are not raw pin measurements.
- Preserve044 raw SDF failure126bytes/884violations. Separate old/new/mixed first-stage finite-resolution experiments each pass512bytes with304 testbench resolutions and4365 timing violations. Never call these an unmodified SDF pass, analog MTBF proof, electrical signoff, or proven cause of041 hardware failure.
- 044 is a bounded diagnostic hardware package. Install BOTH044 MCU and FPGA after backing up and verifying041 pair; keep marker037/title034. Decode protocol/tag0x44 and log nes-h1-last-044.txt with the044 decoder. No actual044 hardware result exists until the user supplies it.
- Last actual hardware observation remains041 automatic-menu-return failure. On044 failure inspect its coherent first event and pair identity before another speculative timing change; on success check cycling, RESET, reentry, then GBC. Do not ask for another041 run.

## Latest044 physical observation (supersedes pending-hardware notes above)
- User reports no automatic exit, repeating LINK SCREEN1->2->3->1 and normal GBC gameplay. Log SHA2564ef6d67bf607714c6d9e6ec71cb6db5b91941fa57661579387fc278a269adf97 confirms protocol44, status03 without fault, RESET_ASSERTED, start/stop0 and base_restored1. Record bounded H1 visual/RESET recovery pass and user-reported GBC gameplay.
- Preserve044 as the working diagnostic baseline. Do not rebuild/reflash it merely to collect the same observation or apply the041-only installer over an already installed044 pair. Keep original package/manifests immutable; later hardware evidence is a separate addendum.
- Zero fault snapshot/tag on this successful log means no captured event, not a protocol mismatch.1954 ticks means19.54s including configuration, not measured video/GBC duration. No SD image readback hashes were supplied.
- Warm H1 reentry, extended/repeated lifecycle and separate GBC menu return remain unconfirmed. No electrical signoff, exact041 causal proof or full NES game acceptance follows from this bounded pass. Continue real producer/memory integration planning while keeping these gates open.
- Current evidence verifier is tools/verify_nes_h1_hardware_044.py; it verifies frozen044 artifacts using the saved pre-observation status files. The earlier sampling verifier represents the pre-hardware checkpoint.

##045 memory producer continuation
-045 is an original completed-packet memory reader tested through unchanged044 transport. Eight historical NES trace-derived packets are NOT a new NES/live encoder execution; descriptor arrival is not a VBlank/deadline model. No045 SD image exists. Preserve044 hardware baseline.
- Source owns immutable bytes until done or common reset. Full-slot backpressure must not trigger source reads, partial publish, dropped frames or an assumed right to pause NES. Physical memory controller/CDC/exactly-once replies remain to be implemented.
- Capture generation synchronously on queue_clk while common reset is held; do not put variable epoch data in an async reset-only branch (initial045 inferred16latches). Immediately gate requests with reset. Preserve the failed resource report and final matching-source regression.
- Final045 standalone416LE/155registers/0M9K/61totalLAB with virtual pins is not a full joint fit or STA. Do not subtract independent LAB totals from032's40LAB headroom as proof.
- Current development verifier: tools/verify_nes_packet_memory.py; prior044 checkpoints and hardware report are immutable with saved status snapshots. Next connect live encoder/source ownership and physical memory/clock, then joint resource and runtime consumer.

##046 streaming encoder continuation
-046 is original causal RTL for the restricted NCR1 BG contract, tested with131104 historical NES fetches at their recorded tick gaps; it is not a fresh NES core run. Golden packets are consumer references only. Actual PPU event classification, mapper physical-address tap, attribute and supported-mode monitor are still required.
- Preserve single source-buffer ownership until045 done. An overlapping incoming frame fails; do not quietly drop, delay or slow NES to satisfy backpressure. frame_end is required to detect a missing tail; a stalled source has no independent046 timeout.
- The complete16388 raw/15840 useful fetch cadence and stable990 cells must validate before descriptor publication. Unsupported modes, attributes, mutable CHR, mixed windows and midframe changes are not implemented game features.
- Final046 shared RAM2M9K/672LE/292registers/118totalLAB is standalone, not full NES fit. Implicit-function unused warnings were removed via explicit function inputs; final functional fitted-netlist6024byte check passes. Preserve276027 and vendor vopt-13162 warnings; no SDF/timing signoff is claimed.
- Keep044 hardware image and045 product source unchanged. Current verification is tools/verify_nes_ncr1_encoder.py with archived status snapshots. Next bind live PPU/mode evidence and run actual core integration plus joint resource measurement before any new hardware pair.

##047 actual-core PPU binding continuation
-047 executes original021 banks32/fine_x anew through the private014 core exports,047 tap, unchanged046/045/044.8frames/131104fetches/16064bytes/491520actual PPU pixels and20tap checks pass. This is now live core RTL evidence, still not hardware or a running SNES consumer.
-018's full-address resource cart adapter ignores its mask ports. Apply masks in047's separate generated adapter, only ROM addresses; preserve CPU/PRG RAM/CIRAM mapping. Merely changing mask constants did not repair boot. Preserve failed01..06 and pre-mask fit; keep018/044/045/046 frozen.
-Actual attributes0..3 are canonicalized ONLY while all four actual BG palette groups equal15/33/48/22. This is a diagnostic palette restriction, not general palette support. Reject active PPU/CHR mapping/mode changes, unsupported memory addresses and ownership overlap; never pause NES/drop frames to pass.
-Final047 joint diagnostic-geometry fit14153LE/953of963LAB/26M9K leaves10LAB.237virtual/5unlocated pins, no boardPLL/ROM controller/loader/fullSTA. The resource RAM wrapper differs from ideal initialized simulation memory. Do not claim full board feasibility or add standalone LAB totals.
-Next prioritize full-board resource budget and equivalence-backed area reduction, then real memory/loader/clock and SNES NCR1 consumer/deadline/display integration before a new recoverable hardware pair.044 SD remains unchanged. Current verifier tools/verify_nes_ncr1_live.py; historical status snapshots preserve older manifests.

##048 primary OAM write optimization
- Accepted048 uses tools/nes_oam_compact.py on private generated047 PPU. The banks-only tools/nes_oam_banked.py variant is a dependency/rejected experiment:14161LE/961LAB is worse. Keep both records; do not accidentally deploy the banks-only branch.
- Eight32-byte register banks preserve256bytes. Share only the normal row-copy/CPU write decoder; their exclusivity requires pinned corrupting_write=0. The generator asserts this. Preserve savestate-before-copy-before-CPU per-byte priority, simultaneous different-address writes and old-data row reads. No sprite features or memory capacities are removed.
- Final048216362-clock differential outputs/state/256primary+64secondary bytes pass, with2012same-edge write collisions and directed same-address cases. Actual core8frames/16064bytes/491520pixels and full live trace match047 exactly. This is bounded simulation equivalence, not formal proof or hardware acceptance.
- Original eval_count lacks explicit initialization/reset. Differential testing first preserves X then seeds both models0..3 identically. Do not describe test-only seeding as a product fix or hardware reset guarantee; resolve this scope before sprite accuracy claims.
- Same diagnostic-geometry joint fit13283LE/926of963LAB/26M9K/4797registers saves870LE and27LAB;37LAB remain. No fullboard/STA guarantee. Separate044 boundary402cells and program18cells/24M9K are reference-only, never additive LAB proof.
- Keep044..047 frozen, GBC protected and044 SD installed. Next concrete memory/clock/loader/SNES consumer integration and combined board budget/deadline checks. Current verifier tools/verify_nes_oam_banked.py with archived status snapshots.

##049 common local RAM and startup
- Use src/nes/nes_local_memory.sv in both actual-core tests and joint synthesis. CPU2KiB/CIRAM2KiB/PRGRAM8KiB clear by8192 real clocked writes, without hierarchical/testbench RAM initialization. Hold core and packet reset until init_done; feed the memory external reset, not that combined reset.
- Reset release needs board-domain synchronization. This diagnostic clears PRG RAM on every reset; do not silently use it for battery save retention or claim OAM initialization is solved. External ROM/loader/physical clocks/consumer are still unimplemented here.
- Final153604unit checks and8actual-core frames pass.491520pixels and packet content outside release timestamps match048; all S/E/F/D times and release tick have measured+4master-clock offset. Keep this startup-phase difference; do not claim full byte/trace equality.
- Joint04913477LE/920LAB/26M9K/4811registers has43LAB left in virtual diagnostic geometry. LE increased194; lower LAB count is packing, not guaranteed board area savings. Keep old RAM warnings and no STA/hardware claim.
- Current verifier tools/verify_nes_local_memory.py checks frozen044–048 using saved statuses. Preserve failed initial compile and successful preliminary unit evidence. Keep044 SD/GBC unchanged; next external-memory response/deadline and real clock/loader/SNES consumer integration.

##050 shared immutable ROM service
- Use nes_rom_service for diagnostic64KiB PRG/up to32KiB CHR only. One NES-clock backend, one outstanding transaction, PPU priority, per-client1-byte physical-address cache. rom_request is a grant strobe gated by ready, not held-valid. Common reset MUST flush the backend and cache; no CDC/epoch/invalidation across independent reset is implemented.
- Explicit CPU sample export observes existing cart_ce/cpu_ce; PPU uses actual tap_ce/read.1-clock registered backend response passes624618requests/8frames/491520pixels/16064bytes with exact049 live trace.2-clock backend fails PPU deadline in both ROMs, observed tick852270. Preserve Fatal/error logs; slow passed=true means expected failure verified, never a slow-backend functional pass or physical timing specification.
- Sticky faults1..6 stop new grants; caller must abort/discard affected frames and provide board recovery.050 testbench stops next edge. Printed addresses are next-edge observations, not captured causal addresses. Do not claim complete board fault handling or first invalid sample prevention.
-4148unit checks cover arbitration/cache/reset/ready and6faults. Joint13538LE/928LAB/26M9K/4895registers has35LAB left in virtual diagnostic geometry; no real PSRAM/PLL/CDC/STA/loader/SNES runtime. Keep044 SD/GBC and049prior evidence frozen.
- Current verifier tools/verify_nes_rom_service.py. Next concrete physical ROM/clock/CDC response budget and scheduling, then loader/epoch/SNES consumer and combined board fit/STA; do not reuse a two-clock service unchanged and assume deadline safety.

##051 causal early ROM reads
- nes_rom_early uses only current exported CPU(prg_addr[15] && prg_allow) and PPU(ALE && !vram_w) address qualification. Physical-address tags still validate demand; old-address responses never validate a new address. Priority: actual PPU, actual CPU, early PPU, early CPU. Do not preempt accepted reads or assume mutable ROM/invalidation support.
- All2/3/4-clock synchronous replies pass8frames each with exact050 pixels/packets/live trace;624788requests each,170more than050.4168unit checks pass. Old0502-clock and new0518-clock failures are preserved. These are finite workload latency settings, not physical PSRAM timing/CDC proof.
- Dump test history inside the Fatal observer and store ring/index with NBA to avoid losing evidence to simulator termination. Initial observer race and executed pre-fix driver are retained. History ends at the decision tick; ordinary Fatal bus addresses are one edge later. Production HDL matches across live2/live3/live4/fit despite observer-only changes.
- Joint13420LE/935LAB/26M9K/4895regs leaves28LAB; LE decreases but LAB rises7. No full board/pin/PLL/STA claim. Keep044 SD/GBC/044–050frozen. Current verifier tools/verify_nes_rom_early.py.
- A negative-test runner can exit nonzero because the DUT unexpectedly passed. Inspect PASS/Fatal markers and actual pixels before classifying; preserve original logs and reuse completed valid cases with explicit provenance. Delay5–7 are uncharacterized; do not call4 the maximum supported latency.
- Next implement concrete physical memory/faster-clock/CDC response and jointly measure resource/timing; preserve8-clock negative control. Loader/epoch/fault recovery/SNES consumer are still required before new hardware delivery.

##052 read-only physical ROM and CDC
- nes_rom_physical has one outstanding bundled toggle request/response, two control synchronizers each direction, stable source address/held response data, and common async reset with local two-flop release. Independent resets, mutable ROM and loader ownership are unsupported. Physical bundled max-delay/reset constraints and synchronizer placement still require board signoff; do not blanket-false-path bundled payloads.
- Byte address bit1 selects PSRAM chip; bit0=0 uses pins15:8, bit0=1 uses7:0; physical address=zero-extended byte[21:2]. WE stays high; controller never drives data. PRG0..FFFF and CHR200000..207FFF need a future matching loader.
- At NES46.560846ns/memory11.904762ns and3read cycles,16unit phases complete8400reads/cancel208 with4NES-clock latency.25ns pin model is only a timing assumption;60ns is an expected data failure, not a controller error report. ROM has no error pin. Do not infer the user's PSRAM specification.
- Actual core8frames matches051 pixels/packets/live trace. Each test ends with one early read outstanding; unit tests drain/cancel all reads. Core execution used archived generic-attribute source; final source differs only in recognized Quartus synchronizer attributes and explicit counter constant width, verified exactly. Final source passes full strengthened unit and joint fit. Preserve old reports and never infer license trouble from parser/assertion failures.
- Joint13547LE/925LAB/26M9K/4959regs leaves38LAB. Lower LAB despite added logic is packing, not full-board feasibility.270virtual pins/6unlocated/PLL0. Keep044 SD/GBC/044–051 frozen. Current verifier tools/verify_nes_rom_physical.py.
- Next integrate044 physical boundary, independent clock generation/common reset, memory ownership and diagnostic ROM loader, then real SNES packet consumer/frame deadlines/fault recovery and joint physical fit/STA. No052 SD image exists. Resource command omits --delay and uses default3; do not pass live-only parser arguments.

##053 diagnostic ROM stream boot
- nes_rom_loader accepts memory-clock byte stream, fixed64KiB PRG then16/32KiB CHR. END requires exact completed count; START separately enables run. loaded is length/write completion, NOT CRC or physical readback verification. No MCU SPI decoder/firmware path or real board clocks are connected yet.
- nes_rom_boot owns PSRAM pins exclusively: byte-select writes while stopped, unchanged052 reader while RUN. Caller must drive core/cache/packet reset from external reset OR !run_enable, then retain049 local scrub. STOP from RUN preserves loaded ROM but cancels pending reads; common reset invalidates the image. No independent-reset/save retention claim.
- Invalid commands during WRITE/HOLD must drain the accepted pulse/hold before FAILED. Do not gate write outputs directly with fault or freeze their counter. STOP during active write is sticky error6/drain; external reset may abort the byte and must invalidate the image. Eight negative scenarios cover six error codes.
- Final360505checks/180226read bytes and2actual-core ROMs/8frames pass from initially unknown pin RAM populated ONLY by writes. Actual packet/trace timestamps shift by the measured per-case constant due to core divider reset-release phase; preserve recorded offsets, do not claim byte-exact timestamps. Final unit/core/fit source hashes match.
- Align test control pulses to memory-clock sampling and declare run_enable before wire initializer use. Preserve failed initial unit and integration compile plus pre-fix driver; neither failure is a license problem.
- Joint13612LE/929LAB/26M9K/5016regs leaves34LAB.293virtual/22unlocated pins/PLL0;16bidirectional data pins are unlocated, not physical board binding. Keep044 SD/GBC/044–052 frozen. Current verifier tools/verify_nes_rom_boot.py.
- Next add MCU SPI load/status integration to materialized044 boundary and qualify board clocks/reset, then real SNES NCR1 consumer/deadlines/recovery and full-board fit/STA. SNES_SYSCLK/PIN_A9 is only an identified candidate clock source; frequency/region/routing remain unqualified. No053 SD image exists.
