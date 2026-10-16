# SPDX-License-Identifier: MIT
"""Join199 common-form output/codec tests; compare equal synthetic pressure only."""
from pathlib import Path
import argparse,hashlib,json,re
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-short199';old=BASE/'probes/nes-batch198'
 scripts=dict(test01='test_nes_plan_batch199.py',faults01='test_nes_plan_batch199_faults.py',c01='test_nes_plan_service199.py')
 results={n:read(d/n/'result.json') for n in scripts}
 for n,r in results.items():
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/scripts[n]),n
  for f,h in r['source_pins'].items():assert sha(BASE/f)==h,f
 assert results['faults01']['checks']==37 and results['c01']['checks']==24 and results['c01']['frames']==43
 assert 'PASS CODEC199 checks=283' in (d/'c01/host.log').read_text()
 for name in [f'scene{i}' for i in range(8)]+['pressure']:
  assert (d/'c01'/(name+'.batch')).read_text().split()==(d/'test01'/(name+'.batch')).read_text().split(),name
 previous=read(ROOT/'analysis/batch198-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-batch198')]
 oldtest=read(old/'test02/result.json');newtest=results['test01']
 # Changed endpoints/harness allowed; actual reader/cache/tile/aperture and source fixture must be identical.
 for n,h in oldtest['source_pins'].items():
  if n in newtest['source_pins']:assert h==newtest['source_pins'][n],n
 def measure(folder):
  t=(folder/'scene0-mode1-slow1.log').read_text()
  time=int(re.search(r'Time: (\d+) ps',t)[1])/1e9
  frames=[bytes(int(x,16) for x in line.split()[1:]) for line in (folder/'pressure.batch').read_text().splitlines()]
  payload=sum(b[1]+256*b[2] for b in frames)
  return dict(elapsed_model_ms=time,batch_payload_bytes=payload,batch_frame_bytes=sum(map(len,frames)),batches=len(frames))
 comparison=dict(before=measure(old/'test02'),after=measure(d/'test01'))
 assert comparison['before']['batch_payload_bytes']==8208 and comparison['after']['batch_payload_bytes']==3587
 assert all(c['spi_mhz']==2.625 for c in newtest['cases'])
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 files=['src/nes/rtl/nes_plan_batch199.sv','src/nes/rtl/nes_plan_spi199.sv','src/nes/firmware/nes_plan_service199.h','src/nes/firmware/nes_plan_service199.c','src/nes/firmware/nes_plan_wire199.h','tests/nes-functional/plan199_driver.svh','tests/nes-functional/spi199_bus.svh','tests/nes-functional/plan199_faults_tb.sv','tests/nes-functional/plan199_host.c']
 files+=['tools/'+n for n in scripts.values()]+['tools/nes_short199_evidence.py','docs/nes-short199-contract.ko.md']
 result=dict(passed=True,selected=list(scripts),result_pins={n:sha(d/n/'result.json') for n in scripts},source_pins={n:sha(ROOT/n) for n in files},prior_archives=archives,
  rtl_cases=newtest['cases'],rtl_output_bytes=1840,pressure_bytes=8192,spi_checks=37,c_checks=24,codec_checks=283,c_frames=43,synthetic_pressure_comparison=comparison,
  existing_spi_mhz=2.625,c_transfer_limit=248,clock_changed=False,cross_frame_cache=False,output_tiles_skipped=0,meets_60fps_budget=False,
  actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,actual_c_rtl_cosimulation=False,
  production_runtime=False,frame_controller=False,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Prioritize multi-frame lease/epoch/END rearm/token/producer-board-runtime-finalACK/STOP integration over more isolated codec work; minimum joint test/fullARM-FIT-IO then first-level scrolling. Persistent delta remains open with base/bank/slot/content validation and memory budget.')
 text=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/short199-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),spi_checks=37,c_checks=24,codec_checks=283,comparison=comparison)))
if __name__=='__main__':main()
