# Host packet staging 029
SPDX-License-Identifier: MIT.

Original MIT nes_host_stage runs entirely on host_clk and connects directly to the028 command/response interface.
027 queue and028 CDC remain unchanged. All register/data strobes must already be synchronous single-cycle events.
There is no SNES physical address assignment, PHI2 synchronization, bidirectional output enable, bus turnaround or external wait-state contract here.

## Register interface
reg_read produces registered reg_rdata with reg_rvalid at the accepting host edge.
Unmapped reads return0. reg_write consumes one command per asserted clock edge.
Data arrives through a separate data_read strobe; its accepted edge registers data and data_valid.
A physical frontend must generate exactly one event per bus access; holding a SNES read level across host clocks must not consume multiple bytes.

| Offset | Read | Write |
|---|---|---|
|0|bit0 ready,bit1 busy,bit2 fault|1 start,2 commit|
|1|sticky bus_error|0 clear error code (does not exit FAULT)|
|2,3|epoch low/high|editable only IDLE|
|4,5|sequence low/high|editable only IDLE|
|6,7|packet length low/high|invalid|
|8,9|consumed bytes low/high|invalid|

start snapshots epoch/sequence, acquires027 through028, reads declared1..3072 bytes into local RAM sequentially,
then asserts ready. Empty acquire returns IDLE without fault; poll/retry start.
No payload output during fill. Once ready, consecutive data_read edges produce consecutive bytes without CDC round trips.
Pauses consume nothing. Queue ownership remains held through staging and all local reads.
Only explicit commit after all local bytes were read releases the queue slot. An early commit is rejected without changing READY.
If last data_read and commit share an edge, commit sees the old consumed count and is conservatively rejected; issue commit on a later edge.
Metadata/status read simultaneous with a write observes the prior value.

Local errors:1 busy/config write,2 invalid acquired length,5 early commit,6 overread,7 invalid read/commit state,8 invalid register command,
9 response tag mismatch,10 malformed response. Queue token errors propagate; errors are sticky until clear/reset.
Malformed or rejected nonempty queue responses enter FAULT; only common reset recovers.
Clearing error code does not release ownership or recover FAULT.
Common asynchronous reset must also reach028/027; fresh reset_epoch and peer release rules from028 apply.
Independent endpoint reset, retry after partial fault, epoch wrap and host watchdog/abort policy remain unimplemented.
RAM is not cleared on reset; counters/state ensure stale bytes are inaccessible.

## Cost and timing scope
New local buffer3072B plus027 queue6144B means9216B of payload storage, excluding source assembly scratch/renderer/core memory.
Actual M9K/LAB packing and fit/STA are unmeasured.
Logical data response is registered in host_clk and handles one accepted byte per host edge.
It is not a proof of SNES setup/hold, fixed read deadline, source-to-VBlank latency or physical CDC.
Prefetch still costs one CDC round trip per byte. Raw P trace timestamp includes test status/guard overhead; do not label it pure fill latency.
The consumer needs a defined timeout/recovery and must wait for READY before initiating DMA.

## Reproduction
Run tools/run_nes_host_stage.ps1 with -Python, -FloatWrapper, -QuestaBin and fresh ASCII -Out using the installed approved FLOAT paths.
Then run tools/verify_nes_host_stage.py --run OUT --out VERIFICATION.json.
No repeated license smoke check, global environment changes or uncounted fallback.
Testbench uses actual023/024/025 packet inputs plus3072B and17B synthetic patterns at three synthetic clock pairs.
No NES CPU, Mesen or Quartus execution is added in029.
