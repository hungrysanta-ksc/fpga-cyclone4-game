# SPDX-License-Identifier: MIT
"""Verify paired ingress/RUN/capture/link and immutable previous evidence."""
from pathlib import Path
import argparse,json
from nes_metadata203 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive

FILES=['tools/nes_metadata203.py','tools/test_nes_metadata203.py','tools/test_nes_metadata203_capture.py',
 'tools/nes_metadata203_arm.py','tools/check_nes_metadata203_arm.py','tools/nes_metadata203_evidence.py',
 'docs/nes-metadata203-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-metadata203';test=read(d/'test04/result.json');capture=read(d/'capture02/result.json');arm=read(d/'check01/result.json')
 for n,r,script in [('test04',test,'test_nes_metadata203.py'),('capture02',capture,'test_nes_metadata203_capture.py')]:
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/script),n
  for path,h in r['source_pins'].items():assert sha(BASE/path)==h,path
 for path,h in test['generated'].items():assert sha(d/'test04'/path)==h,path
 for path,h in arm['public_sources'].items():assert sha(ROOT/path)==h,path
 prep=read(d/'arm01/preparation-metadata203.json')
 for path,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(d/'arm01'/path)==h,path
 for path,h in read(d/'test04/preparation203.json')['generated'].items():
  assert sha(d/'test04'/path)==h,path
  if path.endswith(('.c','.h','.inc')):assert sha(d/'arm01/src'/path)==h,path
 assert sha(d/'capture02/nes_native_export203.sv')==sha(d/'test04/nes_native_export203.sv')
 assert capture['bench_sha256']==sha(d/'capture02/bench.sv') and capture['join_sha256']==sha(d/'capture02/metadata203_join.svh')
 assert test['frames']==9 and test['runtime_faults']==6 and test['boundaries']==9 and test['export_faults']==3
 assert test['host_receiver_bytes']==9880 and test['removed_chr_storage']==8192
 assert capture['commits']==3 and capture['no_fill_instance'] and capture['checks']==558
 assert arm['passed'] and arm['remaining_margin']==9260 and arm['foreground_bound']==28784 and arm['irq_reserve']==508
 assert sha(d/'arm01/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 nm=(d/'check01/nm.txt').read_text();assert 'nes_native_video185_build' not in nm and 'nes_native_video165_build' not in nm
 previous=read(ROOT/'analysis/runtime202-verification.json')
 for path,h in previous['source_pins'].items():assert sha(ROOT/path)==h,path
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-runtime202')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 r=dict(passed=True,selected=['test04','capture02','arm01','check01'],source_pins={n:sha(ROOT/n) for n in FILES},
  result_pins={n:sha(d/n/'result.json') for n in ['test04','capture02','check01']},prior_archives=archives,
  frames=9,bulk_tiles=100,export_scenes=11,export_faults=3,receiver_boundaries=9,runtime_faults=6,capture_checks=558,
  duplicate_chr_ingress_removed_in_candidate=True,receiver_host_bytes=9880,removed_chr_storage=8192,
  full_arm=True,firmware_bytes=arm['firmware_bytes'],compile_only_sha256=arm['firmware_sha256'],ram_static=arm['ram_static'],
  foreground_bound=arm['foreground_bound'],irq_reserve=508,remaining_margin=9260,minimum_margin=1024,
  production_board_mux=False,source_epoch_producer=False,actual_c_rtl_trace_replay=True,actual_c_rtl_simultaneous=False,
  actual_snes_cpu_new_test=False,new_fit=False,new_hardware_firmware=False,new_package=False,physical=False,
  actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,meets_60fps_budget=False,
  next='Actual loader epoch/ready/write + source192 exported201 lease + SPI/descriptor/consume mux and SNES195 in production board. Replace old fill/arbiter, minimal BGOBJ board-C-SNES and fullFIT/IO, then FIRSTLEVELSCROLL; no standalone codec loops.')
 text=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/metadata203-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),removed_chr_storage=8192,remaining_margin=9260)))
if __name__=='__main__':main()
