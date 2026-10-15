# SPDX-License-Identifier: MIT
"""Join compact ROM, actual C/65816, ARM objects and immutable prior records."""
from pathlib import Path
import argparse,hashlib,json,shutil
from nes_bulk194_evidence import verify_archive
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);archive=BASE/'probes/nes-bulk195'
 temp=Path('C:/Users/mohallo/AppData/Local/Temp')
 for name in ('snes01','coupled01','coupled02','coupled03'):
  shutil.copytree(temp/('nes-bulk195-'+name),archive/name)
 build=read(archive/'coupled03/candidate/client/build.json');snes=read(archive/'snes01/result.json');coupled=read(archive/'coupled03/result.json');obj=read(archive/'objects03/result.json')
 assert all(x['passed'] for x in (snes,coupled,obj))
 assert build['body_bytes']==3935 and build['program_bytes']==4096 and build['body_free']==1
 rom=archive/'coupled03/candidate/client/sink165.sfc';digest=sha(rom)
 assert digest==sha(archive/'build02/sink165.sfc')==snes['client_sha256']==coupled['client_sha256']
 for n,h in coupled['source_pins'].items():assert sha(BASE/n)==h,n
 for n,h in coupled['fixture_pins'].items():assert sha(BASE/'probes/nes-consume181/evidence/test05'/n)==h,n
 assert coupled['unit']=='PASS BULK195 checks=225'
 for name in ('normal','bad_token','stop_dma'):
  left=archive/'coupled03'/name;right=archive/'snes01'/name
  req=list(sorted(left.glob('req-*.bin')));assert req
  for f in req:assert f.read_bytes()==(right/f.name).read_bytes(),f.name
  for i in range(1,8 if name=='normal' else 2):assert (left/f'frame-{i}.rgb').read_bytes()==(right/f'frame-{i}.rgb').read_bytes()
 o=obj['results'];assert o['candidate']['layout']==o['prior']['layout']==dict(video_size=15912,sink_size=32)
 for n,s in o['prior']['stacks'].items():assert o['candidate']['stacks'][n]==s,n
 assert o['candidate']['stacks']['nes_sink195_bulk']['bytes']==40
 # No production changes to bus/control/producer RTL during195.
 previous=read(ROOT/'analysis/bulk194-verification.json')
 for n,h in previous['source_pins'].items():assert sha(BASE/n)==h,n
 archives=[verify_archive(e['name']) for e in previous['prior_archives']]+[verify_archive('nes-bulk194')]
 sources=['tools/nes_bulk195.py','tools/test_nes_bulk195_coupled.py','tools/check_nes_bulk195_objects.py','tools/nes_bulk195_evidence.py','src/nes/firmware/nes_sink_bulk195.h','src/nes/firmware/nes_sink_bulk195.inc','tests/nes-functional/bulk195_host.c','docs/nes-bulk195-contract.ko.md']
 result=dict(passed=True,selected=['build02','snes01','coupled03/candidate','coupled03','objects03'],
  rom_sha256=digest,body_bytes=3935,boot_reserved_bytes=96,program_bytes=4096,body_free=1,
  snes_cases=snes['cases'],coupled_cases=coupled['cases'],c_boundary_checks=225,
  c_packets_equal_prepared194=True,reference_pixels=428288,arm_objects=obj,
  production_c_issuer=True,production_descriptor_acquisition=False,actual_rtl_snes_cosimulation=False,
  source_pins={n:sha(ROOT/n) for n in sources},prior_archives=archives,
  actual_scroll_measured=False,performance_change_percent=None,physical_fps=None,
  full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  next='Production descriptor/plan CDC/epoch/frame latch/board integration; minimal joint lifecycle then paired real first-level scrolling.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 (ROOT/'analysis/bulk195-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,body_bytes=3935,program_bytes=4096,c_checks=225,prior_archives=len(archives))))
if __name__=='__main__':main()
