# Packet consumer CDC028 contract

SPDX-License-Identifier: MIT.

Original nes_packet_cdc wraps unchanged027 nes_packet_queue.
Producer commands remain entirely in queue_clk. Only consumer commands and replies cross to host_clk.
One outstanding transaction; no asynchronous payload FIFO or physical SNES bus interface is implemented.

## Held-data protocol

cmd_valid && cmd_ready at host edge latches op,epoch,sequence,address and flips request toggle.
Host holds that bundle until reply reception. A two-stage request synchronizer and queue phase machine
issue one registered027 command, wait for its execution, then capture result plus length observed before acquire.
Queue holds reply fields and flips acknowledgement toggle. Host synchronizes ack, captures held reply,
and holds rsp_valid and fields until rsp_ready accepts them. A new command is blocked until that response drains.
Response tags echo the accepted request; queue performs actual epoch/sequence validation.
rsp_data_valid is a payload field: use it only with rsp_valid and preferably the rsp_valid && rsp_ready transfer.
All returned fields may retain old values after rsp_valid drops.

host_read_owned is asserted after an accepted acquire response arrives and cleared after accepted commit response
or reset. It is not by itself a SNES DMA permit or a combinational memory read grant.
Only command transactions can access queue bytes. Send commit after the actual downstream consumer is finished.
An in-progress commit can have released the queue before its acknowledgement returns; no new command is accepted in that window.
Caller must latch successful acquire length and retain normal packet-header validation.

## Reset and timing assumptions

One common asynchronous reset clears both mailbox toggles,valids and local release pipes.
Each domain releases after two local edges, then synchronizes peer-up before host requests are accepted.
Queue reset remains synchronous but is asserted while its local release pipe is low.
Clocks may stop through common reset; restart must allow queue reset and both peer-up handshakes before commands.
External reset_epoch must be fresh and stable through queue reset.
Independent endpoint reset,epoch reuse/rollover coordination and external reset pulse qualification are unsupported.

Bundled-data hold is a logical contract, not a physical timing signoff.
Constrain and verify control synchronizers,held request/response data arrival and skew,and async reset recovery/removal
in the eventual hierarchy. No unchecked generic SDC waiver is added here.
Metastability is not represented by zero-delay digital RTL simulation. Board clock/enable strategy remains unresolved.

## Reproduce

Use tools/run_nes_packet_cdc.ps1 with existing Python,FLOAT wrapper,QuestaBin and fresh absolute ASCII Out.
It shares the approved RunOnly temporary FLOAT route and does not compile upstream NES core.
The Python driver compiles027 queue+028 CDC+original TB once,then runs three clock/phase combinations serially.
Keep licenses/server logs outside evidence and Git. No repeated smoke or uncounted fallback.

~~~powershell
./tools/run_nes_packet_cdc.ps1 -Python <existing-python> -FloatWrapper <approved-probe_float.ps1> -QuestaBin <existing-questa-bin> -Out <fresh-absolute-ASCII-output>
python -B -X utf8 tools/verify_nes_packet_cdc.py --run <run> --out <fresh-json>
~~~

Final raw copy analysis/local-packet-cdc-028/run; first compile failure in compile-failure-01.
The initial testbench receive task used9arguments for8parameters; fixed only that call.
3actual runs ×13cases,6405checked bytes each,6426host responses and4commits each.
Two reset-canceled requests per run include one response byte already read but not delivered.
Trace R records request,Q queue response,H acceptedhostresponse,X reset.
Independent verifier reconciles transactions,payload,ownership,tags and canceled generations.

Observed accepted-read latencies include response backpressure and are synthetic-clock test measurements.
Next step needs SNES MMIO/status registers and host-side data staging/prefetch before fixed-latency DMA reads,
then measured ready-wait and real service timing. No current SNES DMA,actual CDC fit/MTBF or full-board claim.
