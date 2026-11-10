"""Pin728 builds, immutable maps, guard failures/results and complete replay logs."""
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
 for variant in ('a','c'):
  for ph in (1,2):
   result=json.loads((a.temp/f'nes-dma728-{variant}{ph}/joint.json').read_text())
   assert result['passed'] and result['commits']==53
 for d in sorted(a.temp.glob('nes-dma728-*')):
  if not d.is_dir():continue
  for p in d.rglob('*'):
   if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log','.txt'):add(p,d.name+'/'+p.relative_to(d).as_posix())
  pixels[d.name]={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*.rgb')}
 for p in a.probe.iterdir():
  if p.is_file() and p.suffix in ('.py','.ps1','.json','.log','.patch','.md'):add(p,'probe/'+p.name)
 for d in sorted(p for p in a.probe.iterdir() if p.is_dir() and 'patch' in p.name):
  for p in d.iterdir():
   if p.is_file():add(p,'probe/'+d.name+'/'+p.name)
 for name in ('normal01','normal02','arm01'):
  d=a.probe/name
  for pat in ('nes*.c','nes*.h','crc.h','crc.S'):
   for p in (d/'src').glob(pat):add(p,name+'/src/'+p.name)
  for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):add(d/'src/obj-nes-100'/n,name+'/'+n)
  for p in d.glob('*.log'):add(p,name+'/'+p.name)
 for label,folder in [('base-client',a.probe.parent/'nes-longrun694/client01'),('candidate-client',a.probe/'client02')]:
  for n in ('sink165.sfc','build.json','labels.json','body.bin','sink-program.hex'):add(folder/n,label+'/'+n)
 for p in ROOT.glob('tools/*728*.py'):add(p,'tools/'+p.name)
 for n in ('check_nes_supply723.py','check_nes_rows713.py','test_nes_observer717.py','build_nes_trial577.ps1','prepare_nes_accept726.py','check_nes_accept726.py','analyze_nes_accept726.py','analyze_nes_pair727.py','analyze_nes_rows713.py','analyze_nes_fence714.py','trace_nes_map527.py'):
  add(ROOT/'tools'/n,'tools/'+n)
 for n in ('dma728-verification.json','pair727-verification.json','pair727-archive.json','supply723-verification.json','supply723-archive.json','ready712-archive.json','bg707-verification.json','bg707-archive.json'):
  add(ROOT/'analysis'/n,'analysis/'+n)
 add(ROOT/'docs/nes-dma728-results.ko.md','docs/nes-dma728-results.ko.md')
 pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
 inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
 ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n');zp=a.out/'evidence.zip'
 with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):z.write(p,n)
 with zipfile.ZipFile(zp) as z:
  for n,r in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
 r=dict(stage=728,location='WORKSPACE/probes/nes-dma728/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),
  all_verified=True,original_game_ROM=False,license=False,pixel_hashes_only=True,private_derived_fixture=True,
  complete_CPU_frames=212,inherited_baseline_CPU_frames=106,selected_source_archive='analysis/bg707-archive.json',
  inherited_comparison_archive='analysis/pair727-archive.json',new_delivery=False)
 (ROOT/'analysis/dma728-archive.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
