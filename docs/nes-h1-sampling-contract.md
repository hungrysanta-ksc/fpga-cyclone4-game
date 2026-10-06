# H1 044 qualified SNES frontend contract

044 preserves the original031,040 and041 implementations. The experimental
replacement is derived by `tools/nes_h1_sampling.py` from the pinned043 frontend; the materializer installs
it under the original module name only in isolated build directories.

## Input and response contract

The84MHz domain samples RD, WR and ROMSEL through two stages, and address/data
through bundled first/second samples. It accepts a read only when two consecutive
active samples agree on address and ROMSEL and both report WR high. It tracks one
request until RD release. Register writes retain the latest pair of equal active
address/data samples and complete once both WR samples are high. A write is not
reissued while WR remains high. This avoids relying on a single rising-edge
comparison after a first-stage uncertainty interval.

This is a bounded bundled-data interface, not an arbitrary asynchronous multibit
CDC guarantee. The RTL regression covers address setup20ns, read low120/180ns,
12 starting phases, release skew0/1/6/12/24/36ns, and independent additional pad
latencies0..11ns. Streams use155ns idle gaps. The board stimulus additionally
checks real queue/stage response latency. These synthetic bounds have not been
measured on the user's SNES. More than one sample of relative input skew, shorter
pulses, and electrical setup/hold/turnaround remain unqualified.

A stable in-read address change, active ROMSEL deselection, WR collision, wrong
payload order/not-ready and missing response still fault. Raw pins retain immediate
pad release for RD high, WR conflict, address mismatch or payload deselection.
The registered error checks use only sampled inputs. Transients that do not form
a stable pair can release the external driver without latching an address/deselect
fault; this is deliberate qualification, not proof such transients are harmless.

At each first RD sampling edge, response eligibility is sampled alongside RD and
pipelined by the same number of stages. An accepted read ending before a response
was available still produces the early-release event even if the response exists
by the time synchronized RD reports high. Unselected cycles and requests rejected
before issue are not classified as early response termination. A completed response
can persist internally after raw RD release; legal address/ROMSEL release then
must not become an abort.

## One registered error event

A combinational cause vector is registered together with its context. On the next
edge, both sticky frontend_error and the first frontend_snapshot consume this
same event. Cause bits0..3 map to error1, bit5 to2, bit4 to4, bit6 to8. No independent
raw-input predicate may update either output. An edge-by-edge regression checks
both consumers and preservation/reset of the first record.

The aggregate F5..FF snapshot remains a later observation. A prior stage or producer
fault can make its frontend field0; it must not be compared blindly to the later
first frontend event. Simultaneous frontend causes may set several mapped bits.

## Protocol44 D0..DF

D0=cause bits; D1=output_valid,payload_pending,local_pending,read_issued,read_seen,
rd_previous,pending[1:0]; D2=ready,busy,fault,reg_rvalid,data_valid,sampled ROMSEL,RD,WR.
D3..D5=little-endian decision address (addr_sync), D6..D8=latched read address,
D9..DA=position16bits. DB low nibble=registered event's mapped error bits;
DB bit4=response eligibility at the aligned RD sample; DC..DE=previous address
sample. DF=44. All are pre-update event context. No raw-strobe pulse counters remain.
The MCU returns30 detail bytes as before but requires F1=44 and writes log044.
Never decode this schema using the041 raw-address/counter labels.

## Verification limits

A vendor timing notifier's X models uncertainty, not an analog voltage. The
uncertain-WR-release test requires one completion after a stable accepted write
and high recovery; its edge-only negative control must lose that write. Do not
interpret this experiment alone as the cause of the physical041 failure.

Full fit/STA checks internal clocks and physical pins; external asynchronous IO
still has no measured constraint envelope. SDF timing checks stay enabled. A
functional RTL pass or a zero-delay gate control is not electrical signoff.

## 044 predicate identity and trace evidence

For current sample A, previous sample P and latched read address L, the original
address abort required A=P and A!=L.044 spells its changed bits as
`|( (A^L) & (P^L) )`, while retaining A=P. For all binary values these predicates
are identical: if A=P, the AND is (A^L). Thus this change does not relax the real
address-change condition.4096 exhaustive4bit triples supplement the algebra;
24bit bounded-resolution RTL cases retain both actual binary outcomes.

043 fitted trace at normal read completion: addr_meta[12] notifier at641373597ps,
then addr_sync contains X while the preceding sample and latched address are both
40805A. The old equality and inequality can both become X, even though each0/1
resolution makes the combined abort false. Event bit0 then becomes X, followed
by sticky error bit0. This is a simulation reconvergence issue, not proof of a
physical address fault. The trace checks actual retained primitive q taps.
Fitted RD/ROMSEL/rd_previous q taps are inverted versus source signals and must
not be read as literal pin levels. Optimized snapshot aliases are not telemetry.

044 raw SDF later fails at126bytes: RD first-stage notifier at654444998ps propagates
through RD synchronization to read_seen/read_issued/pending. At read start,0/1
resolution has two legitimate timing histories; indefinite digital X does not
choose one. This is distinct from the contradictory043 address predicate.

## Separate bounded-resolution gate experiments

The raw SDF failure and every notifier remain enabled and preserved. A separate
TESTBENCH model can resolve only35 frontend first-stage primitive q outputs
(addr_meta24,data_meta8,RD/WR/ROMSEL3)1ns after their notifier, then releases the
force2ns after the next local clock. It never forces second stages, event/error
registers, ROM outputs or payload values. The35-node allowlist is checked against
actual dffeas instances before simulation; every applied resolution is logged.

Old selects the last known q at the preceding negative clock edge; new selects
the primitive's current effective d/asdata input. Mixed alternates these selections
by event/node. A floating effective input falls back to the previous value.
These deterministic models are not exhaustive analog metastability probabilities,
MTBF calculations, or a measured settling bound. They test defined binary timing
histories alongside the unmodified X/notifier run, not instead of it. A payload
match under this assumption must retain `timing_pass=false` when violations exist.

Hardware package readiness means a bounded diagnostic experiment after RTL/board,
actual MCU SPI replay, internal fit/STA, image-decoder, old/new/mixed resolution,
and backup/restore checks. It is explicitly separate from electrical signoff or
physical root-cause verification. Record the raw SDF failure in any such package.
