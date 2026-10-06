# NES shared ROM service050 contract

Candidate: `NES-R1-ROM-SERVICE-050`. Hardware remains044. This is a synchronous service boundary and diagnostic timing experiment, not a physical PSRAM controller or clock-domain crossing.

## Interface and ownership

`src/nes/nes_rom_service.sv` connects CPU and PPU to one read-only backend in the NES master-clock domain. CPU physical addresses0x000000–0x00ffff are64KiB PRG ROM; PPU0x200000–0x207fff is up to32KiB CHR ROM. Local049 RAM bypasses this service. Geometry is deliberately the existing diagnostic geometry, not a general NES cartridge loader.

The backend has one outstanding request. `rom_request` is a grant strobe, asserted only when `rom_ready` is high and the service can accept a transaction. It is not an AXI-style valid signal held while ready is low. Addresses may change before grant; the backend latches the granted address. A response must come at a later clock edge with matching22-bit address and data, exactly once. Common reset must flush the backend's outstanding response; there is no epoch tag or asynchronous CDC. Never attach an independent reset/clock backend without a new protocol and tests.

On simultaneous uncached reads, PPU receives priority. An accepted CPU read cannot be stolen. Each client has a one-byte cache tagged by the physical ROM address; repeated reads do not rerequest the same immutable byte. A matching successful response can feed the sampling edge directly and retire into the cache. Retiring a response and granting the other client can happen at the same edge. No future trace/golden packet feeds this circuit, no NES pause is introduced, and no frame is dropped to hide a missed deadline. ROM contents must remain immutable until common reset invalidates both tags. Loading or modifying backing storage requires a reset/invalidation policy before integration.

## Deadlines and fault handling

An explicit generated NES/probe port exports `(cart_ce || cpu_ce) && mr_int && prg_addr[15] && prg_allow` as the CPU ROM sampling requirement. PPU uses the existing actual `tap_ce && ppumem_read`. These taps observe the existing core; they do not alter its timing or read strobes. Matching cached or responding data must be available at the sampling edge.

Sticky error priority: unsolicited response3; wrong response address4; backend error5; pending timeout6; PPU deadline2; CPU deadline1. Timeout fires after256 waiting edges without a response. Successful response wins that timeout edge. Fault stops new ROM grants until common reset; both data-valid outputs are false while reset or fault is asserted. The core itself has no ready/stall input here. The eventual board lifecycle must abort/discard the affected frame on fault;050's testbench stops via `$fatal` on the next edge. Do not interpret this as a completed board fault/exit path or a guarantee that the core did not sample the first invalid byte.

## Executed timing evidence

`rom_backend_model.sv` is test-only and shares the master clock. DELAY=1 registers response/address/data one full clock after the accepting edge. DELAY=2 registers them two clocks later. The model serializes requests and holds readiness low while pending. This is not a PSRAM tAA/tOE specification; model edges, cache hits, arbitration and sampling all contribute to the result.

- DELAY=1: banks32/fine_x run afresh through048 core,049 local RAM and047/046/045/044 video pipeline.312303+312315=624618 backend requests;8frames,131104 BG fetches,16064 bus bytes,491520 pixels. All packet bytes, pixels and complete `live.tsv` equal049 exactly. CPU and PPU ROM data are checked at valid sampling edges against the loaded ROMs.
- DELAY=2: both ROMs fail the actual PPU deadline, observed on the following testbench edge at tick852270/time40.083154800ms, before the armed video capture. Logs retain `$fatal`, errors=1 and no final live PASS. `slow/result.json passed=true` means the expected failure was verified, not that the slow memory worked. Printed addresses are observation-time bus values, not a separately latched fault-address snapshot. Do not claim they identify an exact electrical transaction.
- Unit:4148 checks,518 accepted requests,256 CPU/PPU cache pairs, simultaneous priority/handoff, ready-low admission, reset invalidation, non-ROM bypass and all6 fault codes. No physical timing, metastability or fairness proof follows from this finite test.

One master clock is46.560846ns in these tests. The one-versus-two-clock result identifies a concrete integration constraint for these workloads and scheduling rules. It is not a general maximum PSRAM access-time specification. The real controller, faster memory clock/CDC latency, request scheduling and turnaround must be measured together; simply attaching a two-clock service fails this diagnostic. No source clock is slowed to accommodate memory.

## Resource and continuation

Same service instance is included in joint fit:13538LE,928/963LAB,4895registers,26M9K,182922memory bits. Compared with049:LE+61,LAB+8,registers+84. Service hierarchy reports181logic cells/84registers; hierarchy cells and total LE are different metrics.282virtual pins,5unlocated physical pins,PLL0. No physical pins/PLL/controller/loader/SNES CPU runtime/STA. Existing core port/startup and RAM warnings remain; no10036/10240 warnings. Historical generated resource header/scope text still mentions the inherited RAM probe; actual instance/source hashes and this contract define050 scope.

Use `tools/run_nes_rom_service.ps1 -Mode live -Delay 1` or `-Mode negative -Delay 2` with the approved FLOAT wrapper and a fresh absolute ASCII output path. Protocol checks use `tools/run_nes_rom_service_checks.ps1 -Mode unit`. Area uses `tools/nes_rom_service.py resource --out ... --quartus-bin ...`. Current verifier: `tools/verify_nes_rom_service.py`. Raw evidence is `analysis/local-rom-service-050`;044–049 remain frozen with saved status snapshots, and GBC/SD remain unchanged.

Next implement concrete external-memory/clock/CDC timing against this deadline, considering causal earlier issue from live addresses if required; then loader/reset/epoch and SNES NCR1 consumer/CHR atlas; combine physical fit/STA/lifecycle checks before a recoverable hardware package. OAM initialization, save RAM retention,240-row display, DMC/IRQ accuracy and HDL adoption holds remain open.
