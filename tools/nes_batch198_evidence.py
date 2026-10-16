# SPDX-License-Identifier: MIT
"""Join selected198 tests and verify prior immutable evidence; no test rerun."""
from pathlib import Path
import argparse,hashlib,json
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-batch198'
 scripts=dict(test02='test_nes_plan_batch198.py',faults02='test_nes_plan_batch198_faults.py',c03='test_nes_plan_service198.py',dma01='test_nes_batch198_dma.py')
 results={n:read(d/n/'result.json') for n in scripts}
 for n,r in results.items():
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/scripts[n]),n
  for f,h in r['source_pins'].items():assert sha(BASE/f)==h,f
 assert results['faults02']['checks']==23 and results['c03']['checks']==24 and results['c03']['frames']==46
 assert results['dma01']['success']==744 and results['dma01']['byte_faults']==248
 for name in [f'scene{i}' for i in range(8)]+['pressure']:
  assert (d/'c03'/(name+'.batch')).read_text().split()==(d/'test02'/(name+'.batch')).read_text().split(),name
 previous=read(ROOT/'analysis/spi197-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-spi197')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 files=['src/nes/rtl/nes_plan_batch198.sv','src/nes/rtl/nes_plan_spi198.sv','src/nes/firmware/nes_plan_service198.h','src/nes/firmware/nes_plan_service198.c','tests/nes-functional/plan198_driver.svh','tests/nes-functional/spi198_bus.svh','tests/nes-functional/plan198_faults_tb.sv','tests/nes-functional/plan198_host.c']
 files+=['tools/'+n for n in scripts.values()]+['tools/nes_batch198_evidence.py','docs/nes-batch198-contract.ko.md']
 result=dict(passed=True,selected=list(scripts),result_pins={n:sha(d/n/'result.json') for n in scripts},source_pins={n:sha(ROOT/n) for n in files},prior_archives=archives,
  rtl_cases=results['test02']['cases'],rtl_output_bytes=1840,pressure_bytes=8192,pressure_batches=35,spi_fault_checks=23,c_checks=24,c_frames=46,dma_inplace_success=744,dma_byte_faults=248,
  existing_spi_mhz=2.625,existing_dma_limit=259,c_transfer_limit=248,rtl_transfer_limit=520,clock_changed=False,
  pressure_payload_only_ms=8192*8/2.625e6*1000,pressure_actual_clock_model_ms=32.096399080,meets_60fps_budget=False,
  actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,actual_c_rtl_cosimulation=False,
  production_runtime=False,frame_controller=False,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Stable physical pattern/epoch/slot reuse and changed-plan transmission before frame controller/common lifecycle, whole ARM/FIT/IO and actual SMB3 first-level scrolling; do not treat batch alone as60fps.')
 text=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/batch198-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),spi_checks=23,c_checks=24,dma_success=744,dma_faults=248,pressure_batches=35)))
if __name__=='__main__':main()
