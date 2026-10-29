# SPDX-License-Identifier: MIT
"""Area-only MMC3 restoration on exact471 board; not a functional/hardware profile."""
import argparse,hashlib,json,re,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['board','cart','closure','out']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 baseline=json.loads((ROOT/'analysis/receive476-verification.json').read_text(encoding='utf8'))
 original=json.loads((ROOT/'analysis/nrom406-verification.json').read_text(encoding='utf8'))
 assert sha(a.cart)==original['reference_cart']
 for n,h in baseline['FPGA_inputs'].items():assert sha(a.board/n)==h,n
 for n,h in baseline['FPGA_inputs'].items():assert sha(a.closure/n)==h,('executed source mismatch',n)
 current=(a.board/'cart_nrom.sv').read_text(encoding='utf8');replacement=a.cart.read_text(encoding='utf8')
 def ports(s):return ''.join(re.search(r'module cart_top(?:\s*#\([^)]*\))?\s*\((.*?)\);',s,re.S)[1].split())
 assert ports(current)==ports(replacement)
 a.out.mkdir(parents=True,exist_ok=False)
 # The executed471 MAP also auto-found CIRAM and the sink hex. QSF-only pins
 # are not the complete dependency closure; make CIRAM explicit in this probe.
 assert sha(a.board/'nes_native_ciram165.sv')==sha(ROOT/'src/nes/diagnostic/nes_native_ciram165.sv')
 extras={n:sha(a.board/n) for n in ['nes_native_ciram165.sv','sink-program.hex']}
 # board.sdc sources a separate exact CDC contract. The public-era QSF-only
 # snapshot omitted it; recover from the matching executed471 project, not a
 # newly weakened/generated constraint. Validate recursively before Quartus.
 pending=['board.sdc'];sdc_dependencies={}
 while pending:
  name=pending.pop();source=a.closure/name
  for child in re.findall(r'^source\s+([A-Za-z0-9_./-]+)\s*$',source.read_text(encoding='utf8'),re.M):
   assert (a.closure/child).is_file(),child
   if child not in sdc_dependencies:sdc_dependencies[child]=sha(a.closure/child);pending.append(child)
 for n in [*baseline['FPGA_inputs'],'board.qsf','board.qpf',*extras]:
  source=a.board/n
  if not source.exists():continue
  target=a.out/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 for n in sdc_dependencies:shutil.copyfile(a.closure/n,a.out/n)
 shutil.copyfile(a.cart,a.out/'cart_nrom.sv')
 q=a.out/'board.qsf';s=q.read_text(encoding='utf8')
 assert 'SYSTEMVERILOG_FILE nes_native_ciram165.sv' not in s
 q.write_text(s+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_native_ciram165.sv\n',encoding='utf8',newline='\n')
 modified={n:sha(a.out/n) for n in baseline['FPGA_inputs'] if sha(a.out/n)!=baseline['FPGA_inputs'][n]}
 assert list(modified)==['cart_nrom.sv']
 r={'scope':__doc__,'base_inputs':baseline['FPGA_inputs'],'original_auto_found_dependencies':extras,'original_transitive_SDC_dependencies':sdc_dependencies,'changed':modified,'QSF_change':'declare already-required CIRAM explicitly','port_interface_equal':True,'WRAM_note':'same nes_local_memory.sv contains8KiB PRG RAM, previously pruned with NROM; now may be inferred','functional_game_validation':False,'ARM_loader_profile_changed':False,'FPGA_status_profile_is_still_NROM78':True,'hardware_use_approved':False}
 (a.out/'mmc478-preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'changed':modified,'hardware_use_approved':False}))
