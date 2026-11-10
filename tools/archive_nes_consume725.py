"""Pin725 consumer variants, failures, native guards and full replay evidence."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from nes_raw506 import sha
ROOT=Path(__file__).resolve().parents[1]

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);files={};pixels={}
    def add(p,n):
        assert p.is_file() and n not in files
        assert p.suffix.lower() not in ('.nes','.chr','.prg','.dat') and 'license' not in n.lower()
        files[n]=p
    for tag in ('b','f'):
        for ph in (1,2):assert (a.temp/f'nes-consume725-{tag}{ph}/joint.json').is_file()
    for d in sorted(a.temp.glob('nes-consume725-*')):
        if not d.is_dir():continue
        for p in d.rglob('*'):
            if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log','.txt'):add(p,d.name+'/'+p.relative_to(d).as_posix())
        pixels[d.name]={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*.rgb')}
    for p in a.probe.iterdir():
        if p.is_file() and p.suffix in ('.py','.ps1','.json','.log'):add(p,'probe/'+p.name)
    for name in ('client01','client02','client03','client04'):
        for p in (a.probe/name).iterdir():
            if p.is_file():add(p,name+'/'+p.name)
    for name,path in [('original',a.probe.parent/'nes-longrun694/client01'),('raw635',a.probe.parent/'nes-reuse635/client04')]:
        for n in ('body.bin','sink165.sfc','labels.json','build.json'):add(path/n,name+'/'+n)
    for p in ROOT.glob('tools/*725*.py'):add(p,'tools/'+p.name)
    for n in ('test_nes_observer717.py','test_nes_complete685.py','nes_rom636.py','prepare_nes_longrun694.py','test_nes_seal538_stop.py','check_nes_longrun694_boot.py','check_nes_longrun694_exit.py'):
        add(ROOT/'tools'/n,'tools/'+n)
    for n in ('consume725-verification.json','tail724-verification.json','tail724-archive.json','supply723-verification.json','supply723-archive.json','bg707-verification.json','bg707-archive.json','ready712-archive.json'):
        add(ROOT/'analysis'/n,'analysis/'+n)
    add(ROOT/'docs/nes-consume725-results.ko.md','docs/nes-consume725-results.ko.md')
    pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
    inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
    ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n');zp=a.out/'evidence.zip'
    with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
    with zipfile.ZipFile(zp) as z:
        for n,r in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
    result=dict(stage=725,location='WORKSPACE/probes/nes-consume725/'+a.out.name,files=len(files),SHA256=sha(zp),inventory_SHA256=sha(ip),
        all_verified=True,original_game_ROM=False,license=False,pixel_hashes_only=True,private_derived_fixture=True,
        complete_CPU_frames=212,inherited_baseline_CPU_frames=106,new_delivery=False,
        inherited_ARM_source_archive='analysis/supply723-archive.json',selected_source_archive='analysis/bg707-archive.json')
    (ROOT/'analysis/consume725-archive.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
