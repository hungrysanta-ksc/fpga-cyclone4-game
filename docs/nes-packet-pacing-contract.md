# Packet timing and ownership026 contract

SPDX-License-Identifier: MIT.

This is a parameterized offline scheduling model using022..025 measurements. Last actual SNES candidate025;
core014 and functional017 unchanged. Do not call model outcomes an implemented live pipeline.

Inputs:021 four reference cases; matching packet release headers, recorded SNES phase boundaries and captures.
Verify each source with read_case, check packet/trace/result/frames hashes against the corresponding historical artifact manifest,
then reparse raw phase start/commit ticks. Never subtract absolute clocks from different emulator runs.
Anchor NES line0dot5 minus20; use phase as an explicit independent input.
Repeated timing periods, encoder delay, service rate, CDC delay and oscillator ppm are model parameters, not board measurements.

## Equations and ownership

For source frame n, release = phase + ceil((source_start[n]+326984)*1000000/(1000000+ppm)).
Positive ppm means faster source. Claim a slot at release; reject packet length above slot_bytes.
encoded=release+encode_ticks; transfer_start=max(encoded,previous_transfer_end).
transfer_end=transfer_start+packet_bytes*clocks_per_byte; ready=transfer_end+cdc_ticks.
target blank=consumer_start[n+lag]+327360.
consume_start=max(target blank+poll,ready,previous_consume_end).
consume_end=consume_start+measured_max_duration; deadline=consumer_start[n+lag+1]-guard.
Free only at consume_end. At equal timestamps completions free before new releases claim.
Exceeding slot count or deadline is a violation. Sort violations by time/frame/kind and report the first.
Predictions after the first failure have no valid execution interpretation.
The consumer wait/guard and its instruction cost still require implementation and measurement.

No source frame discard/repeat/stall or clock-speed policy is silently used.
lag is a fixed frame-index mapping after startup, not queue feedback or a frame-skipping rule.
A two-slot assumption counts packet storage from lastfetch onward, excluding frame assembly scratch.
No content/CHR cache behavior is inferred from long timing repetition.
The263-point phase sweep is sampled only; the60,000-frame drift horizon is finite.
The output's completed count includes only commits no later than the first violation time.

## Reproduction

~~~powershell
python -B -X utf8 tools/nes_packet_pacing.py --out <fresh-model-json>
python -B -X utf8 tools/test_nes_packet_pacing.py --out <fresh-tests-json>
~~~

Latest outputs are analysis/local-packet-pacing-026/model-audited.json and tests-final.json.
Early model outputs and initial hand-written phase expectation failure are preserved.
Independent tick-step oracle covers300 deterministic cases;13 explicit boundary/regression checks.
Current schedule equations passed the oracle before the corrected hand-written expectation.
No emulator/RTL/Questa/Quartus rerun is required for this model.

## Required next interface

Proposed ownership: FREE -> WRITING -> READY -> READING -> FREE.
Publish length,sequence,generation only after all payload bytes are durable; hold data stable until consumer commit acknowledges it.
Consumer must validate current generation/sequence/length/ready before any PPU DMA; never free on DMA start.
Reset invalidates both endpoints' old generation and pending acknowledgements. CDC circuitry and memory ordering are not implemented here.
Do not solve queue pressure by pausing NES/dropping/repeating frames without an explicitly accepted product policy.
First inspect actual NES enable/SNES clock relationships; actual common-clock or bounded phase behavior remains unknown.
Measure ready-gated instruction overhead and real memory service, producer scratch, metadata/CDC cost before adopting depth.
Keep integration constraints:025 CHR overlaps023 OBJ,024patch is separate,240-row simultaneous display unresolved.
