# Packet memory producer045 contract

SPDX-License-Identifier: MIT.

Original `nes_packet_memory_producer.sv` reads a completed immutable packet through a same-queue-clock memory service, then publishes it through the existing two-slot3072-byte queue. It replaces neither a live NES fetch encoder nor a physical SRAM/SDRAM controller. The044 transport/frontend source bytes used in this test are unchanged.

## Ownership and commands

`desc_valid && desc_ready` at queue_clk accepts `{epoch,seq,base,length}`. Length must be1..3072, seq must be the next nonzero sequence, epoch must match the current reset generation, and the24-bit inclusive address range must not wrap. Fields are latched; the source owner must retain all packet bytes unchanged until the one-cycle `done` pulse or common reset. `published` is the last accepted publish sequence. Sequence65535 completes and blocks further descriptors until reset; exhaustive wrap-boundary execution is outside this17-case suite.

The producer first obtains a queue slot with BEGIN. A full queue retries the same BEGIN without reading source memory or advancing sequence. There is no finite timeout on genuine full-slot backpressure. Queue command responses themselves must arrive within TIMEOUT_CYCLES. One byte is fetched, accepted by the queue, then the offset advances. PUBLISH is issued only after all writes were acknowledged. An error leaves an unpublished partial slot until common reset; no partially filled packet becomes visible. The consumer commits only after its actual display commit in future runtime integration; this testbench models commit after all bytes are read, without executing a PPU.

## Memory service and reset

Request valid/address/epoch remain stable until request ready. Exactly one read may be outstanding. A response must arrive at least one queue clock after request acceptance and return the same address and epoch exactly once; zero-cycle or duplicate responses are outside the service contract. All memory-service signals are synchronous to queue_clk. A future different-clock controller requires a separate verified CDC bridge.

The default timeout is255 cycles; tests use32 with variable request stalls and1..7-cycle service delay counters. Supported parameter range is1..65535. Stale-epoch responses are drained without changing bytes or restarting the watchdog. Current-epoch wrong-address/service-error/unsolicited responses fail closed. Epoch+address cannot distinguish a duplicated reply to a later read of the same address; exactly-once service is a required property, not a claimed safeguard.

Common reset must cover queue rising edges and supply a stable fresh reset_epoch, shared with the044 queue/host path. Epoch is captured synchronously on queue_clk while reset is asserted; it is not assigned variable data through an asynchronous reset latch. Requests, producer commands and response-ready gate off immediately with reset. Do not reuse an epoch while old replies can survive; epoch rollover coordination remains external. The service and source owner must cancel/invalidate outstanding ownership on common reset. No independent producer-only reset is supported.

Error codes:01 length,02 descriptor epoch,03 descriptor sequence,04 address overflow;10 queue response timeout,11 request handshake timeout,12 response timeout,13 response address,14 memory service error,15 current-epoch unsolicited response;2x queue error x. First error is sticky until reset. Busy-slot error1 during BEGIN is retried.

## Executed evidence and limits

Eight2008-byte NCR1 packets (four banks32 and four fine-X frames) were reconstructed from original021 NES reference fetch traces with025 encoder and exact full-frame reference decoding, then placed in synthetic memory. This establishes provenance; it is not a new NES execution, live packet generation, or causal arrival scheduling. All descriptors in the transport test refer to already completed packets; recorded source release ticks are not replayed as live arrival times.

Three queue/host period combinations46.560846/11.904762ns,20/10ns,46.560846/20ns execute17 cases each. Each run compares19153 payload bytes via actual044 frontend/MMIO, including16064 reference bytes, reset/stale cases,3072-byte maximum and last-address boundary. Full queue, empty-acquire retry, invalid descriptors, request/response timeout, wrong address, memory fault after five writes, stale response after reset and while waiting are covered. Normal raw read release changes RD/ROMSEL/address together.

The memory byte stream is verified independently in Python from the captured bus trace. Source is identical between final simulation and standalone map/fit:416LE,155registers,0M9K,61 total fitter LABs,266 virtual pins. This is not a full NES+044+045 joint fit, physical interface fit or STA result. It cannot be added to or subtracted from032's40LAB headroom as an integration guarantee.

Backpressure here is bounded storage ownership, not authorization to pause a continuously running NES, drop frames or crop/color-reduce output. Live encoder buffering, arrival/deadline pacing, physical memory arbitration, clock drift and the NCR1 SNES runtime consumer must be integrated separately. Existing044 hardware image remains the working diagnostic baseline; no045 SD package is produced.

Reproduce with tools/run_nes_packet_memory.ps1 using the already approved FLOAT wrapper, Python, QuestaBin and fresh ASCII Out. Run tools/nes_packet_memory_resource.py with fresh --out and --quartus-bin for the standalone fit. Raw logs, failed initial testbench revisions and the eliminated epoch-latch resource report are preserved in analysis/local-packet-memory-045. tools/verify_nes_packet_memory.py checks final evidence and historical protection.
