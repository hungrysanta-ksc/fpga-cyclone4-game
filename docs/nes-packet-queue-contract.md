# Original packet queue027 contract

SPDX-License-Identifier: MIT.

Original MIT block src/nes/nes_packet_queue.sv, two synchronous slots of3072bytes.
This is not an async FIFO or a connected NES/SNES frontend. Core014 stays unchanged.
External clocks, memory service, packet assembly and PPU commit remain separate work.

## Interface

All requests are sampled on clk rising edge; accept/error/data_valid are registered pulse responses.
Drive one command for one clock or consecutive byte commands with the next byte on each clock.
p_op:0 idle,1 begin,2 sequential write,3 publish. c_op:0 idle,1 acquire,2 sequential read,3 commit.
p_epoch/p_seq and c_epoch/c_seq must match current epoch and expected nonzero sequence.
Producer sequence increments at publish, consumer sequence at commit. Both begin at1 after reset.
Data is written sequentially with internal count. Reads must request exactly the next address.
All payload writes must finish before publish; all reads must finish before commit.
When acquire meets FREE/WRITING it returns no accept and no error, preserving state.
Metadata ready_length/ready_sequence is valid while packet_ready. Consumer must latch before/across successful acquire.
No same-edge free-and-reallocate bypass. Different-slot operations can run together.
An invalid command changes neither payload nor ownership; error pulses let the caller handle failure.

Errors:1 producer state/busy,2 length,3 epoch,4 sequence,5 incomplete publish/commit,
6 extra producer byte,7 read/commit without READING,8 out-of-order/out-of-range read.
Read data is zero and data_valid false unless an accepted read returns a byte.
No packet header/CRC/format validation is provided here.
Acknowledge consumption only after actual PPU/display commit when integrating, never merely on DMA start.

Synchronous reset invalidates both slots and counters without clearing payload RAM.
The external reset controller supplies a fresh16bit reset_epoch and must not reuse it while old requests survive.
Sequence0 is reserved; rollover blocks until generation reset. Epoch rollover coordination is unimplemented.
This block cannot itself prove physical CDC ordering, metastability safety or reset when its clock is stopped.
RTL default length counters assume SLOT_BYTES at most4095; only3072 was executed.

## Actual verification

The14 directed cases run at a synthetic10ns clock, with real historical packet bytes from023/024/025.
10492writes/10460byte comparisons/68commits/2008simultaneous byte-read-write edges.
Reset intentionally abandons32unread bytes. Normal operations are not dropped or repeated.
Raw trace includes cycle,reset,p_op,p_accept,p_error,c_op,c_accept,c_error,data_valid,data,states,ready,active,epoch.
The Python verifier checks byte concatenation,legal ownership transitions,reset visibility,error responses and pinned hashes.

Use the approved Starter FLOAT route via tools/run_nes_packet_queue.ps1, an original-block-specific sibling
of run_nes_functional.ps1 that reuses the same pinned temporary FLOAT wrapper with RunOnly/absolute AfterSmokeScript.
It does not compile upstream CPU/PPU or touch any adoption-held HDL.
No license smoke repetition, uncounted fallback, global environment or permanent server changes.
Wrapper/server output stays private; copied evidence excludes license-route.local.json and server logs.

~~~powershell
./tools/run_nes_packet_queue.ps1 -Python <existing-python> -FloatWrapper <approved-probe_float.ps1> -QuestaBin <existing-questa-bin> -Out <fresh-absolute-ASCII-output>
python -B -X utf8 tools/verify_nes_packet_queue.py --run <run-directory> --out <fresh-json>
~~~

Final raw copy:analysis/local-packet-queue-027/run. Verification requires actual PASS and no Fatal/Error,
not just simulator exit0. Preserved verifier correction concerns a fixture2 expected3byte prefix;
RTL/testbench/simulation were not changed or reinterpreted as a weaker pass.

## Next integration gates

Connect source assembler/memory writes and consume commit through a reviewed CDC/mailbox protocol.
Validate old generations and reset races on both sides before exposure to SNES DMA.
Then measure SNES ready-wait overhead and actual memory latency; integrate VRAM ownership and rerun resource018.
The clock audit shows existing GBC board CLKIN-derived PLLs and asynchronous SNESphi2.
The NES test clock is synthetic, not a proven board phase lock.026 drift requirements remain open.
