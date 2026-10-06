# Joint core/transport resource032 contract
SPDX-License-Identifier: MIT.

Purpose: measure actual co-placement of unchanged018 latest014 NES core/standardMMC3/basic12KiBRAM
and unchanged031 RAM-inferred packet queue/CDC/stage/SNES pin frontend.
This is an area/packing probe. It is not a complete functional NES-to-SNES integration.

Inputs are hash-checked before copying:
- analysis/local-resource-018/ram-01/result.json and every recorded source.
- analysis/local-snes-frontend-031/resource/result.json and current matching src/nes RTL.
No upstream rewrite, mapper/address simplification or behavioral optimization is applied.
Core RAM adapter remains018's resource-only adapter with its earlier functional-validation limitation.

Generated top nes_joint_resource exposes all original nonclock ports with nes_ or transport_ prefixes.
NES master and transport queue share clk; host_clk is independent.
Packet producer pins stay external. NES video outputs are retained but not encoded into the queue.
Separate reset controls stay external; no common board reset/clock strategy is implied.
All281 nonclock bits use virtual pins.2clock pins are unassigned. EP4CE15F17C8,seed1,default mapping/fit settings.
Declared clocks46.560846ns/11.904762ns are assumptions inherited from the component probes.
No false paths, clock relaxation, area settings or extra seeds were used to obtain the successful fit.
Only map/fit ran. The report phrase Timing Models: Final does not mean STA or physical IO signoff.

The verifier checks:
- Core and transport source bytes against prior inputs and compiled copies.
- Exact aggregate21KiB payload/24M9K and preservation of2/2/8 core RAM plus8/4 packet/stage blocks.
- Nonzero CPU,PPU,APU,MMC3 and frontend hierarchy.
- No hard-coded logic target: LE/LAB/register values come from the final fitter summary.
- Warning codes and remaining device/design-target resources.
Parent hierarchy includes its children; never add PPU and OAMEval again.

Reproduce with installed Quartus:
tools/nes_joint_resource.py --out FRESH_ASCII --quartus-bin INSTALLED_BIN
tools/verify_nes_joint_resource.py --run FRESH_ASCII --out RESULT.json
The first command expects preserved018 and031 input evidence in this checkout.
Raw sources/logs/reports and generated project stay ignored. Public tools contain no upstream HDL copy.
No Questa/Mesen runtime or license server is needed for this resource-only milestone.

A successful co-placement fit closes the question whether these current blocks fit together.
It does not reserve the remaining40LAB for future logic. Producer/encoder,memory controllers,PLL,loader,
SNES program service,physical audio/input,reset/lifecycle and IO timing remain outside this build.
Do not claim an executable game or board image. H1 may proceed as an original diagnostic once its own full hardware gates close.
