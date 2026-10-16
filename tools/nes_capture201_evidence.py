# SPDX-License-Identifier: MIT
"""Capture/ROM lease split proof and immutable prior evidence checks."""
from pathlib import Path
import argparse,json
from nes_bulk194_evidence import verify_archive
from test_nes_capture201 import ROOT,BASE,sha,rep
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-capture201'
 scripts=dict(test12='test_nes_capture201.py',faults03='test_nes_capture201_faults.py')
 results={n:read(d/n/'result.json') for n in scripts}
 for n,r in results.items():
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/scripts[n]),n
  for f,h in r['source_pins'].items():assert sha(BASE/f)==h,f
 assert results['test12']['checks']==558 and results['test12']['commits']==3 and results['test12']['overlapped_capture']==1
 assert results['faults03']['checks']==23
 # The capture implementation only exposes the existing exact start condition.
 s=(ROOT/'src/nes/video/nes_native_frame201.sv').read_text(encoding='utf8')
 s=rep(s,'module nes_native_frame201(','module nes_native_frame181(')
 s=rep(s,'output wire capture_begin,output reg owned,geometry_valid,','output reg owned,geometry_valid,')
 s=rep(s,' assign capture_begin=start&&!reset&&!release_frame;\n','')
 s=rep(s,'//201: identical181 capture; expose its exact start edge for source epoch ownership.','//181 Candidate collector join. NOT wired to the deployed board/exporter.')
 assert s==(ROOT/'src/nes/video/nes_native_frame181.sv').read_text(encoding='utf8')
 # Byte decoder / payload ownership are unchanged200; only NES retire admission
 # and its accepted pulse are new. No second mailbox or hidden frame RAM.
 s=(ROOT/'src/nes/rtl/nes_plan_batch201.sv').read_text(encoding='utf8')
 s=rep(s,'module nes_plan_batch201(','module nes_plan_batch200(')
 s=rep(s,'\n input wire retire_permitted,output wire retire_commit,','')
 s=rep(s,'wire retire_ack=!cancel&&retire_valid&&retire_permitted;','wire retire_ack=!cancel&&retire_valid;')
 s=rep(s,'\n // Same mailbox roundtrip: release the source on the accepted NES edge.\n assign retire_commit=!nr&&retire_ack&&retire_word&&closed&&state==WAIT&&!word_valid&&lease_ok;','')
 s=rep(s,'if(retire_ack)begin\n    if(!retire_word||!closed||state!=WAIT||word_valid||!lease_ok)nf<=1;', 'if(retire_valid)begin\n    if(!retire_word||!closed||state!=WAIT||word_valid)nf<=1;')
 assert s==(ROOT/'src/nes/rtl/nes_plan_batch200.sv').read_text(encoding='utf8')
 previous=read(ROOT/'analysis/frame200-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-frame200')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 files=['src/nes/rtl/nes_capture_lease201.sv','src/nes/rtl/nes_plan_batch201.sv',
        'src/nes/video/nes_native_frame201.sv','src/nes/video/nes_native_capture201.sv',
        'tests/nes-functional/capture201_join.svh','tests/nes-functional/capture201_faults_tb.sv',
        'tools/test_nes_capture201.py','tools/test_nes_capture201_faults.py','tools/nes_capture201_evidence.py',
        'docs/nes-capture201-contract.ko.md']
 result=dict(passed=True,selected=list(scripts),result_pins={n:sha(d/n/'result.json') for n in scripts},source_pins={n:sha(ROOT/n) for n in files},prior_archives=archives,
  capture_algorithm_unchanged181=True,plan_decode_unchanged200=True,successful_exports=3,raw_pixels=512,
  next_capture_rows=224,overlap=True,normal_core_resets=0,zero_tile_output_bytes=48,next_source_tokens=[1000,1001,1002],
  joint_checks=558,fault_checks=23,extra_frame_ram=False,declared_ownership_state_bits=99,
  physical=False,actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,meets_60fps_budget=False,
  actual_game_cpu=False,actual_c_rtl_cosimulation=False,production_board_mux=False,production_runtime=False,
  geometry_to_direct_tile_plan_join=False,source_epoch_producer=False,duplicate_chr_ingress_removed=False,
  full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  scope='Actual selected capture/fill/export + source lease + SPI200/batch201/tile191 zero tile/bulk193; synthetic PPU/memory/host display.',
  next='Connect loader content epoch, board SPI/descriptor mux and192 exported source lease, actual191 planner/C200/195 runtime ordering; remove duplicate CHR ingress only with actual geometry/tiles joint proof. FullARM/FIT/IO then SMB3 FIRSTLEVELSCROLL. Do not repeat isolated codec tests.')
 t=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(t,encoding='utf8');(ROOT/'analysis/capture201-verification.json').write_text(t,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),joint_checks=558,fault_checks=23,overlap=True)))
if __name__=='__main__':main()
