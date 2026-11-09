"""Archive unchanged-target712 traces, raw failures and selected source pins."""
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
    for prefix in ('nes-bg707-step','nes-ready712-trace','nes-ready712-row'):
        for phase in (1,2):
            d=a.temp/f'{prefix}{phase}';assert d.is_dir(),d
            for p in d.iterdir():
                if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log'):
                    add(p,d.name+'/'+p.name)
            if prefix=='nes-bg707-step':
                for pattern in ('map-*.bin','expected-*.bin','colors636-*.bin'):
                    for p in d.glob(pattern):add(p,d.name+'/'+p.name)
            pixels[d.name]={p.name:sha(p) for p in d.glob('frame-*.rgb')}
    for p in a.probe.iterdir():
        if p.is_file() and p.suffix in ('.py','.ps1','.json','.log'):add(p,'probe/'+p.name)
    for name,d in [('long',a.probe.parent/'nes-longrun694/arm01/src'),('normal',a.probe.parent/'nes-trial704/arm704-02/src')]:
        for pattern in ('nes*.c','nes*.h'):
            for p in d.glob(pattern):add(p,'ARM/'+name+'/'+p.name)
        add(d/'stm32f4xx/spi.c','ARM/'+name+'/stm32f4xx/spi.c')
        for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):
            add(d/'obj-nes-100'/n,'ARM/'+name+'/'+n)
    for n in ('sink165.sfc','build.json','labels.json','body.bin'):
        add(a.probe.parent/'nes-longrun694/client01'/n,'client/'+n)
    board=a.temp/'nes-bg707-board04';add(board/'inputs707.json','board/inputs707.json')
    prior=json.loads((ROOT/'analysis/credit710-verification.json').read_text())
    for n,digest in prior['boards']['707D']['reports'].items():
        p=board/'output_files'/n;assert sha(p)==digest;add(p,'board/'+n)
    for p in ROOT.glob('tools/*ready712.py'):add(p,'tools/'+p.name)
    for n in ('ready712-budget.json','deadline711-budget.json','deadline711-archive.json','credit710-verification.json','bg707-verification.json','bg707-archive.json','longrun694-verification.json'):
        add(ROOT/'analysis'/n,'analysis/'+n)
    add(ROOT/'docs/nes-ready712-results.ko.md','docs/nes-ready712-results.ko.md')
    pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
    inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
    ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n')
    zp=a.out/'evidence.zip'
    with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
    with zipfile.ZipFile(zp) as z:
        for n,m in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==m['SHA256']
    r=dict(stage=712,location='WORKSPACE/probes/nes-ready712/'+a.out.name,files=len(inventory),
        SHA256=sha(zp),inventory_SHA256=sha(ip),all_verified=True,original_game_ROM=False,license=False,
        private_derived_fixture=True,pixel_hashes_only=True,final_observed_frames=106,preliminary_observed_frames=106,
        failed_observer_attempts=3,source_707D_archive='analysis/bg707-archive.json',
        selected_target_changed=False)
    (ROOT/'analysis/ready712-archive.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
