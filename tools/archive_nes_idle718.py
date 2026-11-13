"""Pin718 actual sources/builds/traces/failed harnesses; exclude original ROM."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from nes_raw506 import sha
ROOT=Path(__file__).resolve().parents[1]

def run(a):
 a.out.mkdir(parents=True,exist_ok=False);files={};pixels={}
 def add(p,n):
  assert p.is_file() and n not in files,p
  assert p.suffix.lower() not in ('.nes','.chr','.prg','.dat') and 'license' not in n.lower(),n
  files[n]=p
 folders=sorted(p for p in a.temp.glob('nes-idle718-*') if p.is_dir())
 assert all((a.temp/f'nes-idle718-{tag}{ph}/joint.json').is_file() for tag in ('a','b') for ph in (1,2))
 for d in folders:
  assert d.is_dir(),d
  for p in d.rglob('*'):
   if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log','.txt'):add(p,d.name+'/'+p.relative_to(d).as_posix())
  pixels[d.name]={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*.rgb')}
 for p in a.probe.iterdir():
  if p.is_file() and p.suffix in ('.py','.ps1','.json','.log'):add(p,'probe/'+p.name)
 for name in ('patch01','normal-patch01','patch-b01','normal-b-patch01'):
  for p in (a.probe/name).iterdir():add(p,'probe/'+name+'/'+p.name)
 for name in ('arm02','normal01','arm-b01','normal-b01'):
  d=a.probe/name
  for pattern in ('nes*.c','nes*.h'):
   for p in (d/'src').glob(pattern):add(p,name+'/src/'+p.name)
  for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):add(d/'src/obj-nes-100'/n,name+'/'+n)
  for p in d.glob('*.log'):add(p,name+'/'+p.name)
 for n in ('sink165.sfc','build.json','labels.json','body.bin'):add(a.probe.parent/'nes-longrun694/client01'/n,'client/'+n)
 for p in ROOT.glob('tools/*718*.py'):add(p,'tools/'+p.name)
 add(ROOT/'tools/trace_nes_map527.py','tools/trace_nes_map527.py')
 for n in ('idle718-verification.json','tail717-archive.json','tail717-verification.json','lazy716-archive.json','ready712-archive.json','bg707-verification.json','bg707-archive.json'):
  add(ROOT/'analysis'/n,'analysis/'+n)
 add(ROOT/'docs/nes-idle718-results.ko.md','docs/nes-idle718-results.ko.md')
 pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
 inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
 ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n');zp=a.out/'evidence.zip'
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
 with zipfile.ZipFile(zp) as z:
  for n,r in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
 r=dict(stage=718,location='WORKSPACE/probes/nes-idle718/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),
  all_verified=True,original_game_ROM=False,license=False,pixel_hashes_only=True,private_derived_fixture=True,
  complete_CPU_frames=212,candidate_CPU_frames=212,inherited_observer_control_CPU_frames=106,inherited_baseline_CPU_frames=106,selected_source_archive='analysis/bg707-archive.json',
  inherited_original_ARM_archive='analysis/ready712-archive.json',new_delivery=False)
 (ROOT/'analysis/idle718-archive.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
