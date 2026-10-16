# SPDX-License-Identifier: MIT
"""Join RUN202 evidence and immutable predecessor archives; no new simulation."""
from pathlib import Path
import argparse,json
from nes_runtime202 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive

FILES=['src/nes/firmware/nes_runtime202.c','src/nes/firmware/nes_runtime202.h',
 'tests/nes-functional/runtime202_host.c','tools/nes_runtime202.py','tools/nes_runtime202_arm.py',
 'tools/test_nes_runtime202.py','tools/test_nes_runtime202_dma.py','tools/check_nes_runtime202_arm.py',
 'tools/nes_runtime202_evidence.py','docs/nes-runtime202-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-runtime202';test=read(d/'test05/result.json');dma=read(d/'dma02/result.json');arm=read(d/'check03/result.json')
 for n,r,script in [('test05',test,'test_nes_runtime202.py'),('dma02',dma,'test_nes_runtime202_dma.py')]:
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/script),n
  for path,h in r['source_pins'].items():assert sha(BASE/path)==h,path
 for path,h in arm['public_sources'].items():assert sha(ROOT/path)==h,path
 assert dma['base_script_sha256']==sha(ROOT/'tools/test_nes_batch198_dma.py')
 prep=read(d/'arm04/preparation-runtime202.json')
 for path,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(d/'arm04'/path)==h,path
 assert arm['passed'] and arm['remaining_margin']==1068 and arm['irq_reserve']==508
 assert sha(d/'arm04/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 for path,h in read(d/'test05/preparation202.json')['generated'].items():
  assert sha(d/'test05'/path)==h,path
  if path.endswith(('.c','.h','.inc')):assert sha(d/'arm04/src'/path)==h,path
 assert test['frames']==9 and test['fault_cases']==6 and dma['success']==777 and dma['byte_faults']==259
 previous=read(ROOT/'analysis/capture201-verification.json')
 for path,h in previous['source_pins'].items():assert sha(ROOT/path)==h,path
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-capture201')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 r=dict(passed=True,selected=['test05','dma02','arm04','check03'],
  result_pins={n:sha(d/n/'result.json') for n in ['test05','dma02','check03']},source_pins={n:sha(ROOT/n) for n in FILES},
  prior_archives=archives,frames=9,fault_cases=6,bulk_tiles=100,dma_success=777,dma_byte_faults=259,
  firmware_bytes=arm['firmware_bytes'],compile_only_sha256=arm['firmware_sha256'],ram_static=arm['ram_static'],
  foreground_bound=arm['foreground_bound'],irq_reserve=arm['irq_reserve'],remaining_margin=1068,minimum_margin=1024,
  production_c_run_integrated=True,full_arm=True,old_bg_obj_upload_removed=True,duplicate_chr_ingress_removed=False,
  production_board_mux=False,source_epoch_producer=False,actual_c_rtl_cosimulation=False,actual_snes_cpu_new_test=False,
  new_fit=False,new_hardware_firmware=False,new_package=False,physical=False,actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,meets_60fps_budget=False,
  next='Actual loader epoch + board mux/192 exported201 lease; remove legacy CHR ingress with paired geometry/tag/kind validation, minimal board/C/SNES join and fullFIT/IO, then FIRSTLEVELSCROLL. No isolated codec loops.')
 text=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/runtime202-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),frames=9,fault_cases=6,full_arm=True,remaining_margin=1068)))
if __name__=='__main__':main()
