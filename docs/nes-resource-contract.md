# Latest-core resource probe contract

SPDX-License-Identifier: MIT.

NES-R1-RESOURCE-018 imports the bytes of the successful014 Mapper4 regression.
All17 inventory entries are checked before copying; T65/wrapper/adapter have explicit hash pins.
Only the VHDL/SV closure is synthesized; upstream cart.sv is replaced by the local standardMMC3 adapter.
No upstream tree, functional runner, ROM, or GBC implementation is modified.
Source-adoption holds remain; copied/generated HDL and vendor reports stay local ignored evidence.

Historical64KiBPRG/16KiBCHR fixture cuts are widened in the resource-only copy.
Flags stay standardmapper4. Variant1 exposes memory inputs; variant2 inserts2KiBCPU RAM,
2KiBCIRAM and8KiBPRGRAM. RAM is synchronous one-address read-old-data with no initialization
or second-master port. The new wrapper's functional/boot behavior has not been simulated.
No resource result depends on ROM contents or a constant game trace.

Reproduce each fresh ASCII output:
~~~powershell
& $PY -B -X utf8 tools/nes_resource_probe.py --validated-rtl analysis/local-rdy-014/integrated-01 --out $LOGIC --quartus-bin $QUARTUS
& $PY -B -X utf8 tools/nes_resource_probe.py --validated-rtl analysis/local-rdy-014/integrated-01 --out $RAM --quartus-bin $QUARTUS --local-ram
& $PY -B -X utf8 tools/verify_nes_resources.py --logic $LOGIC --ram $RAM --out $REPORT
~~~
The pinned validated input is local evidence; regenerate it using014 regression instructions if missing.
Quartus25.1std build1129, EP4CE15F17C8, seed1,4workers,46.560846ns, no exception masking.
map/fit/sta only: no asm, download, board image or Questa seat.
Keep sources, constraints, result.json, phase logs and output_files reports; database binaries are not evidence.

Verification requires phase returns0, source hashes, fitter success, core/mapper hierarchy survival,
15 timing records with nonnegative slack and zeroTNS,12M9K/98,304payload bits and the2/2/8RAM split.
It reports unconstrained IO and warning codes; nested entity resource values must not be summed twice.
Latin1 decoding is used only to parse ASCII fields in locale-encoded reports; raw bytes are unchanged.
Unconstrained ports and the unassigned clock pin prevent board timing signoff.

Memory capacity separates measured12KiB from conditional packet/cache scenarios and unknown controller,
encoder,CDC,SNES,audio and loader costs. SNES VRAM residency is not automatically FPGA RAM.
Arithmetic LE/LAB headroom cannot guarantee routing. R1 remains partial until R2 workload and real IO/
memory service contracts can be included in the full system.
