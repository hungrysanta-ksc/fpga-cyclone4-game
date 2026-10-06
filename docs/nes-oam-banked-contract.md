#048 OAM write-structure contract

Candidate `NES-R1-OAM-BANKED-048` uses `tools/nes_oam_compact.py`. The banks-only alternative is retained as rejected evidence. Hardware baseline044 remains unchanged.

## Transformation and preserved semantics

The original256×8 primary OAM array is represented by eight32×8 register banks: byte address low3bits choose a bank, high5bits choose a row. Reads use an explicit eight-way function; all existing address expressions remain. This remains register storage with asynchronous selection, not a new synchronous RAM pipeline or M9K allocation.

The original writes have this per-byte priority: savestate write, then8-byte row corruption copy, then non-rendering CPU OAMDATA write. The source row is always read before the clock's nonblocking updates. Different-address simultaneous savestate/normal writes remain independent. Reset still allows the original savestate write, while normal writes require `!reset && ce`.

The accepted change shares the address decoder of the two normal write sources. A row copy requires a rendering rising transition; a CPU write requires non-rendering. They cannot coincide because this pinned upstream has `corrupting_write = 0`. The transformation explicitly asserts that condition and must reject a future variant that enables corrupting writes until priority and exclusivity are reconsidered. One selected normal row address/data path feeds each bank. Savestate remains a separate earlier write source, preserving same-address overwrite priority.

Secondary OAM, extra sprite machinery, row corruption, attribute-bit masking, evaluation counters, overflow, sprite0, PAL/NTSC behavior and savestate interfaces are retained. CPU/APU/PPU timing is unchanged. No sprite feature is removed to make the diagnostic BG workload cheaper. Upstream held source remains only in ignored local generated files with its notices and COPYING; public files are project-authored transformations/tests.

## Validation limits

Differential simulation compares outputs, savestate-visible state, evaluation state, all256 primary bytes and all64 secondary bytes after every clock. It initializes primary memory through its real savestate port, exercises same-address CPU/savestate collisions, each row-copy destination lane, four evaluator seeds, deterministic random controls and complete NTSC/PAL scanline ranges with rendering transitions.

The original `eval_count` is not explicitly initialized/reset in the pinned source. The test first preserves that X state, then gives both instances identical0..3 seeds to exercise actual evaluator transitions. This test-only seeding is not a source fix, hardware initialization guarantee, formal exhaustive proof, or full sprite/game acceptance. Controls in the differential workload are binary; arbitrary X-valued reset semantics are not claimed.

Fresh actual-core banks32/fine_x execution separately checks the full048 PPU→047tap→046→045→044 pipeline. The same eight packets and491520PPU pixels must equal047 byte for byte. Both workloads are BG-only; the differential evaluator tests provide the additional OAM structural coverage.

The joint resource comparison uses the same047 top, device, seed1, diagnostics' ROM masks and clock declarations. Only the PPU's primary OAM implementation changes. Placement differences matter: independent logic-cell totals cannot be converted into a LAB guarantee. No STA/CDC/physical IO signoff or new SD image follows from this area-only fit.

## Remaining board budget

The accepted candidate contains core, resource RAM, actual PPU tap, encoder, producer and transport. SPI lifecycle, board clock/reset/epoch handling, real ROM/PSRAM service, actual SNES runtime/CHR access, input/audio/save and full pin timing still require concrete integration.044's separate402-cell boundary,18-cell/24-M9K program ROM and PLL are reference measurements only, not an additive proof or a fixed size for the future runtime. Keep044 installed until a complete recoverable candidate passes the appropriate board checks.
