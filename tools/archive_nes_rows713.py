"""Hash-verified private713 evidence; preserve rejected runs, exclude original ROM."""
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
 folders=[a.temp/(prefix+str(phase)) for prefix in ('nes-bg707-step','nes-rows713-a','nes-rows713-b') for phase in (1,2)]
 folders += [a.temp/'nes-rows713-diag1']
 folders += [a.temp/('nes-rows713-'+kind+suffix) for kind in ('exit','stop') for suffix in ('01','b01')]
 for d in folders:
  assert d.is_dir(),d
  for p in d.rglob('*'):
   if not p.is_file():continue
   if p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log','.txt'):
    add(p,d.name+'/'+p.relative_to(d).as_posix())
  pixels[d.name]={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*.rgb')}
  if d.name.startswith('nes-bg707-step'):
   for pattern in ('map-*.bin','expected-*.bin','colors636-*.bin'):
    for p in d.glob(pattern):add(p,d.name+'/'+p.name)
 for p in a.probe.iterdir():
  if p.is_file() and p.suffix in ('.py','.ps1','.json','.log'):add(p,'probe/'+p.name)
 for name in ('patch01','normal-patch01','patchb01','normal-patchb01'):
  for p in (a.probe/name).iterdir():add(p,'probe/'+name+'/'+p.name)
 for name in ('arm02','normal01','armb01','normalb01'):
  d=a.probe/name
  for pattern in ('nes*.c','nes*.h'):
   for p in (d/'src').glob(pattern):add(p,name+'/src/'+p.name)
  for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):add(d/'src/obj-nes-100'/n,name+'/'+n)
  for p in d.glob('*.log'):add(p,name+'/'+p.name)
 for n in ('none','program','done','busy','token'):
  add(a.probe/f'base01-{n}/result.json',f'base01-{n}/result.json')
 for n in ('sink165.sfc','build.json','labels.json','body.bin'):add(a.probe.parent/'nes-longrun694/client01'/n,'client/'+n)
 for p in ROOT.glob('tools/*rows713*.py'):add(p,'tools/'+p.name)
 for n in ('rows713-verification.json','ready712-budget.json','ready712-archive.json','bg707-verification.json','bg707-archive.json'):
  add(ROOT/'analysis'/n,'analysis/'+n)
 add(ROOT/'docs/nes-rows713-results.ko.md','docs/nes-rows713-results.ko.md')
 pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
 inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
 ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n');zp=a.out/'evidence.zip'
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
 with zipfile.ZipFile(zp) as z:
  for n,r in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
 r=dict(stage=713,location='WORKSPACE/probes/nes-rows713/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),
  all_verified=True,original_game_ROM=False,license=False,pixel_hashes_only=True,private_derived_fixture=True,
  complete_CPU_frames=159,failed_B_phase1_last_completed=917,exact_failure_reproduction=True,
  selected_source_archive='analysis/bg707-archive.json',inherited_original_ARM_archive='analysis/ready712-archive.json')
 (ROOT/'analysis/rows713-archive.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
