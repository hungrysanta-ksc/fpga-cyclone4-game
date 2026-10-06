# H1 043 qualified SNES frontend contract

043 preserves the original031,040 and041 implementations. The experimental
replacement is `src/nes/nes_snes_frontend_qualified.sv`; the materializer installs
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

## Protocol43 D0..DF

D0=cause bits; D1=output_valid,payload_pending,local_pending,read_issued,read_seen,
rd_previous,pending[1:0]; D2=ready,busy,fault,reg_rvalid,data_valid,sampled ROMSEL,RD,WR.
D3..D5=little-endian decision address (addr_sync), D6..D8=latched read address,
D9..DA=position16bits. DB low nibble=registered event's mapped error bits;
DB bit4=response eligibility at the aligned RD sample; DC..DE=previous address
sample. DF=43. All are pre-update event context. No raw-strobe pulse counters remain.
The MCU returns30 detail bytes as before but requires F1=43 and writes log043.
Never decode this schema using the041 raw-address/counter labels.

## Verification limits

A vendor timing notifier's X models uncertainty, not an analog voltage. The
uncertain-WR-release test requires one completion after a stable accepted write
and high recovery; its edge-only negative control must lose that write. Do not
interpret this experiment alone as the cause of the physical041 failure.

Full fit/STA checks internal clocks and physical pins; external asynchronous IO
still has no measured constraint envelope. SDF timing checks stay enabled. A
functional RTL pass or a zero-delay gate control is not electrical signoff.
