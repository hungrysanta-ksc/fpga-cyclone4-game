# SPDX-License-Identifier: MIT
"""Join multi-frame rearm checks; no physical FPS or production capture claim."""
from pathlib import Path
import argparse,hashlib,json,re
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-frame200'
 scripts=dict(test03='test_nes_frame200.py',faults02='test_nes_frame200_faults.py',c01='test_nes_frame200_c.py')
 results={n:read(d/n/'result.json') for n in scripts}
 for n,r in results.items():
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/scripts[n]),n
  for f,h in r['source_pins'].items():assert sha(BASE/f)==h,f
 cases=results['test03']['cases'];assert sum(c['frames'] for c in cases)==9 and sum(c['bytes'] for c in cases)==1968
 tokens={}
 for c in cases:
  t=(d/'test03'/f"scene{c['scene']}-mode0-slow1.log").read_text()
  rows=re.findall(r'PASS FRAME200 frame=(\d+) gen=(\d+) bytes=(\d+) next_token=(\d+)',t)
  assert [int(v[1]) for v in rows]==[65534,65535,0]
  ts=[int(v[3]) for v in rows];assert 1000<ts[0]<ts[1]<ts[2];tokens[str(c['scene'])]=ts
 assert results['faults02']['checks']==50 and results['c01']['checks']==10
 previous=read(ROOT/'analysis/short199-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-short199')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 files=['src/nes/rtl/nes_plan_batch200.sv','src/nes/rtl/nes_plan_spi200.sv','src/nes/firmware/nes_plan_service200.h','src/nes/firmware/nes_plan_service200.c','tests/nes-functional/plan200_driver.svh','tests/nes-functional/spi200_bus.svh','tests/nes-functional/frame200_faults_tb.sv','tests/nes-functional/frame200_host.c']
 files+=['tools/'+n for n in scripts.values()]+['tools/nes_frame200_evidence.py','docs/nes-frame200-contract.ko.md']
 result=dict(passed=True,selected=list(scripts),result_pins={n:sha(d/n/'result.json') for n in scripts},source_pins={n:sha(ROOT/n) for n in files},prior_archives=archives,
  rtl_cases=cases,frames=9,output_bytes=1968,next_tokens=tokens,spi_checks=50,c_checks=10,common_reset_between_frames=False,
  final_ack_gate='actual195 C sink validation; mocked exchanges',actual_c_rtl_cosimulation=False,actual_snes_cpu_new_test=False,
  actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,meets_60fps_budget=False,
  production_runtime=False,production_capture_lease=False,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Connect immutable capture generation/content epoch grant/release and board SPI/descriptor mux, production RUN begin-plan-finish-seal-retire; fullARM/FIT/IO then actual first-level scrolling. No frame-global reset, no more isolated codec loops.')
 text=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/frame200-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),frames=9,output_bytes=1968,spi_checks=50,c_checks=10,next_tokens=tokens)))
if __name__=='__main__':main()
