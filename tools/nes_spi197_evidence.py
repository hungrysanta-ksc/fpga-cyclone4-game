# SPDX-License-Identifier: MIT
"""Join197 SPI/reader and C service checks, preserve prior immutable records."""
from pathlib import Path
import argparse,hashlib,json
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-spi197';results={n:read(d/n/'result.json') for n in ('test03','faults01','c03')}
 scripts=dict(test03='test_nes_plan_spi197.py',faults01='test_nes_plan_spi197_faults.py',c03='test_nes_plan_service197.py')
 for n,r in results.items():
  assert r['passed'] and r['script_sha256']==sha(ROOT/'tools'/scripts[n]),n
  for f,h in r['source_pins'].items():assert sha(BASE/f)==h,f
 assert results['test03']['pressure_bytes']==8192 and results['faults01']['checks']==17
 assert results['c03']['checks']==21 and results['c03']['frames']==105
 previous=read(ROOT/'analysis/plan196-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-plan196')]
 files=['src/nes/rtl/nes_plan_spi197.sv','src/nes/firmware/nes_plan_service197.h','src/nes/firmware/nes_plan_service197.c','tests/nes-functional/spi197_bus.svh','tests/nes-functional/plan197_driver.svh','tests/nes-functional/plan197_faults_tb.sv','tests/nes-functional/plan197_host.c','tools/test_nes_plan_spi197.py','tools/test_nes_plan_spi197_faults.py','tools/test_nes_plan_service197.py','tools/nes_spi197_evidence.py','docs/nes-spi197-contract.ko.md']
 result=dict(passed=True,selected=['test03','faults01','c03'],result_pins={n:sha(d/n/'result.json') for n in results},source_pins={n:sha(ROOT/n) for n in files},
  prior_archives=archives,rtl_output_bytes=1840,pressure_bytes=8192,pressure_chunks=4,spi_fault_checks=17,c_checks=21,c_frames=105,
  modeled_spi_mhz=8,min_plan_bytes=42,ss_gap_us=4,min_512_plan_ms=23.552,meets_60fps_budget=False,
  actual_scroll_measured=False,physical_fps=None,performance_change_percent=None,actual_c_rtl_cosimulation=False,
  production_runtime=False,frame_controller=False,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Batch/credit in existing plan M9K plus stable pattern reuse to remove per-tile status overhead, then generation/epoch/controller and board/runtime joint lifecycle; fullARM/FIT/IO and first-level scrolling.')
 text=json.dumps(result,indent=2)+'\n';(a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/spi197-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,prior_archives=len(archives),spi_checks=17,c_checks=21,plan_lower_bound_ms=23.552)))
if __name__=='__main__':main()
