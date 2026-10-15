# SPDX-License-Identifier: MIT
"""Verify selected plan RAM tests, wire CRCs and immutable archives; no simulation."""
from pathlib import Path
import argparse,binascii,hashlib,json
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);d=BASE/'probes/nes-plan196/test02';test=read(d/'result.json')
 assert test['passed'] and test['boundary_checks']==273
 assert test['host']=='PASS PLAN196 plans=97 bytes=1580 boundaries=268'
 for n,h in test['source_pins'].items():assert sha(BASE/n)==h,n
 for key,n in [('script_sha256',ROOT/'tools/test_nes_plan_stream196.py'),('generated_tb_sha256',d/'plan_stream196_tb.sv'),('generated_consumer_sha256',d/'tile_bulk193_consumer.svh')]:assert sha(n)==test[key],n
 plans=payload=ends=0
 for scene in range(8):
  lines=(d/f'scene{scene}.wire').read_text().splitlines()
  for index,line in enumerate(lines):
   v=[int(x,16) for x in line.split()];n=v[0];b=bytes(v[1:-1]);assert len(b)==n and b[15]==1
   assert n==16+2*b[1].bit_count() and binascii.crc_hqx(b,65535)==v[-1]
   if b[0]==3:assert index==len(lines)-1;ends+=1
   else:plans+=1;payload+=n
 assert (plans,payload,ends)==(97,1580,8)
 cases=test['cases'];assert len(cases)==9 and sum(c['bytes'] for c in cases if c['external_plan']==1)==1840
 assert cases[-1]['external_plan']==0 and cases[-1]['bytes']==288
 previous=read(ROOT/'analysis/bulk195-verification.json')
 # 195 C issuer/client and its verification sources are intentionally unchanged.
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-bulk195')]
 sources=['src/nes/firmware/nes_plan_wire196.h','src/nes/rtl/nes_plan_stream196.sv','src/nes/rtl/nes_tile191.sv','src/nes/rtl/nes_source_tile192.sv','tests/nes-functional/plan196_host.c','tests/nes-functional/plan196_driver.svh','tests/nes-functional/plan196_boundary_tb.sv','tools/test_nes_plan_stream196.py','tools/nes_plan196_evidence.py','docs/nes-plan196-contract.ko.md']
 result=dict(passed=True,selected=['test02'],intermediate_pass_not_selected=['test01'],wire_version=1,
  c_checks=268,rtl_checks=273,plan_count=plans,plan_payload_bytes=payload,end_count=ends,crc_bytes_per_record=2,
  output_bytes=1840,cases=cases,test_result_sha256=sha(d/'result.json'),
  source_pins={n:sha(ROOT/n) for n in sources},prior_archives=archives,
  actual_scroll_measured=False,performance_change_percent=None,physical_fps=None,
  production_spi=False,production_controller=False,actual_snes_cpu_connected=False,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Production SPI/descriptor/controller with chunk service while waiting plan credit; epoch/common cancel and joint C-SNES lifecycle; fullARM/FIT/IO then paired first-level scrolling.')
 text=json.dumps(result,indent=2)+'\n'
 (a.out/'result.json').write_text(text,encoding='utf8');(ROOT/'analysis/plan196-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,plans=plans,output_bytes=1840,c_checks=268,rtl_checks=273,prior_archives=len(archives))))
if __name__=='__main__':main()
