# SPDX-License-Identifier: MIT
"""Join selected194 evidence and verify immutable prior archives. No test run."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def verify_archive(name):
 d=BASE/'probes'/name;m=d/'manifest01.json';entries=read(m)
 for n,h in entries.items():assert sha(d/n)==h,(name,n)
 return dict(name=name,files=len(entries),manifest_sha256=sha(m))
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);d=a.archive
 build=read(d/'build03/build.json');rtl=read(d/'rtl03/result.json')
 snes=[read(d/n/'result.json') for n in ('snes05','snes06','snes07')]
 assert build['body_bytes']==3999 and build['program_bytes']==8192 and all(s['passed'] for s in snes) and rtl['passed']
 rom=d/'build03/sink165.sfc';assert sha(rom)==sha(d/'build02/sink165.sfc')
 for s in snes:assert s['client_sha256']==sha(rom)
 compact=bytes.fromhex((d/'build03/sink-program.hex').read_text());image=rom.read_bytes()
 assert len(compact)==8192 and compact[:0x1fc0]==image[:0x1fc0] and compact[0x1fc0:]==image[0x7fc0:]
 assert image[0x100:0x100+3999]==(d/'build03/body.bin').read_bytes()
 cases=[c for s in snes for c in s['cases']];assert len(cases)==12 and cases[0]['commits']==7
 for c in cases[1:]:assert c['commits']==1
 pins={}
 for n,h in rtl['source_pins'].items():
  f=BASE/n;assert sha(f)==h,n;pins[n]=h
 for n in ('tools/nes_bulk194.py','tools/test_nes_bulk194_snes.py','tools/test_nes_bulk194_rtl.py','tools/nes_bulk194_evidence.py'):
  pins['repository-nes-milestone/'+n]=sha(ROOT/n)
 archives=[verify_archive(e['name']) for e in read(BASE/'probes/nes-bulk193/evidence01/result.json')['prior_archives']]
 archives.append(verify_archive('nes-bulk193'))
 result=dict(passed=True,selected=['build03','rtl03','snes05','snes06','snes07'],body_bytes=3999,program_bytes=8192,
  rom_sha256=sha(rom),rom_projection_exact=True,compact4096_approved=False,rtl=rtl,cases=cases,
  reference_pixels=7*256*239,negative_snes_cases=11,source_pins=pins,prior_archives=archives,
  actual_scroll_measured=False,performance_change_percent=None,physical_fps=None,full_arm=False,new_fit=False,new_firmware=False,new_package=False,
  actual_rtl_snes_cosimulation=False,production_c_sink=False,scope='Separately: actual193+194 raw bus RTL and actual65816 DMA/PPU/finalACK on held fixture bus. Seven archived C scenes, not live game or scroll performance.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 (ROOT/'analysis/bulk194-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,pixels=result['reference_pixels'],negative_cases=11,prior_archives=len(archives))))
if __name__=='__main__':main()
