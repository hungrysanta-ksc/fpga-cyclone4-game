"""Archive730 source/builds, failures, guard logs and both complete replays."""
import argparse,json,hashlib,zipfile
from pathlib import Path
from nes_raw506 import sha
ROOT=Path(__file__).resolve().parents[1]

def run(a):
 a.out.mkdir(parents=True,exist_ok=False);files={};pixels={}
 def add(p,n):
  assert p.is_file() and n not in files
  assert p.suffix.lower() not in ('.nes','.chr','.prg','.dat') and 'license' not in n.lower()
  files[n]=p
 for tag in ('a1','a2','b1','b2'):
  d=a.temp/f'nes-owner730-{tag}';r=json.loads((d/'joint.json').read_text());assert r['passed'] and r['commits']==53
  for p in d.rglob('*'):
   if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log','.txt'):add(p,d.name+'/'+p.relative_to(d).as_posix())
  pixels[d.name]={p.name:sha(p) for p in d.glob('*.rgb')}
 for p in a.probe.iterdir():
  if p.is_file() and p.suffix in ('.py','.ps1','.json','.log','.patch','.md'):add(p,'probe/'+p.name)
 for d in a.probe.iterdir():
  if d.is_dir() and 'patch' in d.name:
   for p in d.iterdir():
    if p.is_file():add(p,'probe/'+d.name+'/'+p.name)
 for name in ('normal01','arm01','normal02','arm02'):
  d=a.probe/name
  for pat in ('nes*.c','nes*.h','crc.h','crc.S'):
   for p in (d/'src').glob(pat):add(p,name+'/src/'+p.name)
  for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):add(d/'src/obj-nes-100'/n,name+'/'+n)
  for p in d.glob('*.log'):add(p,name+'/'+p.name)
 for p in ROOT.glob('tools/*730.py'):add(p,'tools/'+p.name)
 for n in ('build_nes_trial577.ps1','test_nes_observer717.py','analyze_nes_accept726.py','analyze_nes_fence714.py','analyze_nes_rows713.py','check_nes_supply485_arm.py','check_nes_reuse635_arm.py','prepare_nes_tail729.py','check_nes_tail729.py','check_nes_deadline719.py'):add(ROOT/'tools'/n,'tools/'+n)
 for n in ('owner730-verification.json','pair727-verification.json','pair727-archive.json','dma728-archive.json','bg707-verification.json','bg707-archive.json'):add(ROOT/'analysis'/n,'analysis/'+n)
 add(ROOT/'docs/nes-owner730-results.ko.md','docs/nes-owner730-results.ko.md')
 p=a.out/'pixels.json';p.write_text(json.dumps(pixels,indent=2)+'\n');add(p,'pixels.json')
 inv={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
 ip=a.out/'inventory.json';ip.write_text(json.dumps(inv,indent=2)+'\n');zp=a.out/'evidence.zip'
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
 with zipfile.ZipFile(zp) as z:
  for n,r in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
 r=dict(stage=730,location='WORKSPACE/probes/nes-owner730/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),all_verified=True,complete_CPU_frames=212,inherited_baseline_CPU_frames=106,original_game_ROM=False,license=False,pixel_hashes_only=True,new_delivery=False)
 (ROOT/'analysis/owner730-archive.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
