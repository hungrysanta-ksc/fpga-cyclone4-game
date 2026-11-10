"""Preserve732 four normal resource attempts and linked guard evidence.

No new complete frame replay or long firmware is present in this archive.
"""
import argparse,json,hashlib,zipfile
from pathlib import Path
from nes_raw506 import sha
ROOT=Path(__file__).resolve().parents[1]

def run(a):
 a.out.mkdir(parents=True,exist_ok=False);files={}
 def add(p,n):
  assert p.is_file() and n not in files
  assert p.suffix.lower() not in ('.nes','.chr','.prg','.dat') and 'license' not in n.lower()
  files[n]=p
 for p in a.probe.iterdir():
  if p.is_file() and p.suffix in ('.py','.ps1','.json','.log','.patch','.md'):add(p,'probe/'+p.name)
 for d in a.probe.iterdir():
  if d.is_dir() and 'patch' in d.name:
   for p in d.iterdir():
    if p.is_file():add(p,'probe/'+d.name+'/'+p.name)
 for name in ('normal01','normal02','normal03','normal04'):
  d=a.probe/name
  for pat in ('nes*.c','nes*.h','crc.h','crc.S'):
   for p in (d/'src').glob(pat):add(p,name+'/src/'+p.name)
  for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):add(d/'src/obj-nes-100'/n,name+'/'+n)
  for p in d.glob('*.log'):add(p,name+'/'+p.name)
 for p in ROOT.glob('tools/*732.py'):add(p,'tools/'+p.name)
 for n in ('build_nes_trial577.ps1','analyze_nes_accept726.py','check_nes_overlap731.py','check_nes_supply485_arm.py','prepare_nes_tail729.py','check_nes_tail729.py','check_nes_deadline719.py','check_nes_longrun692.py','check_nes_longrun693.py'):add(ROOT/'tools'/n,'tools/'+n)
 for n in ('extent732-verification.json','overlap731-verification.json','overlap731-archive.json','pair727-verification.json','pair727-archive.json','bg707-verification.json','bg707-archive.json'):add(ROOT/'analysis'/n,'analysis/'+n)
 add(ROOT/'docs/nes-extent732-results.ko.md','docs/nes-extent732-results.ko.md')
 inv={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
 ip=a.out/'inventory.json';ip.write_text(json.dumps(inv,indent=2)+'\n',newline='\n');zp=a.out/'evidence.zip'
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
 with zipfile.ZipFile(zp) as z:
  for n,r in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
 r=dict(stage=732,location='WORKSPACE/probes/nes-extent732/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),all_verified=True,new_complete_CPU_frames=0,new_long_builds=0,normal_builds=4,inherited_timeline_frames=212,original_game_ROM=False,license=False,new_delivery=False)
 (ROOT/'analysis/extent732-archive.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
