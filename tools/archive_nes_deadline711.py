"""Private hash-verified711 evidence; no original game ROM or licenses."""
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
    report=json.loads((ROOT/'analysis/deadline711-budget.json').read_text())
    folders={a.temp/f'nes-bg707-step{p}' for p in (1,2)}
    folders|={a.temp/r['folder'] for p in report['phases'].values() for r in p['runs'].values()}
    folders|={a.temp/f'nes-deadline711-control{p}' for p in (1,2)}
    for d in sorted(folders):
        assert d.is_dir(),d
        for p in d.iterdir():
            if p.is_file() and p.suffix in ('.lua','.json','.jsonl','.tsv','.csv','.log'):
                add(p,d.name+'/'+p.name)
        if d.name.startswith('nes-bg707-step'):
            for pattern in ('map-*.bin','expected-*.bin','colors636-*.bin'):
                for p in d.glob(pattern):add(p,d.name+'/'+p.name)
        pixels[d.name]={p.name:sha(p) for p in d.glob('frame-*.rgb')}
    for p in a.probe.iterdir():
        if p.is_file() and p.suffix in ('.py','.json','.log'):add(p,'probe/'+p.name)
    for name,d in [('long',a.probe.parent/'nes-longrun694/arm01/src'),('normal',a.probe.parent/'nes-trial704/arm704-02/src')]:
        for n in ('nes_native_sink165.c','nes_plan_service200.c','nes_sink_window184.c'):
            add(d/n,'ARM/'+name+'/'+n)
        for n in ('firmware.stm','sd2snes.elf','sd2snes.map'):
            add(d/'obj-nes-100'/n,'ARM/'+name+'/'+n)
    for n in ('sink165.sfc','build.json','labels.json','body.bin'):
        add(a.probe.parent/'nes-longrun694/client01'/n,'client/'+n)
    board=a.temp/'nes-bg707-board04'
    add(board/'inputs707.json','board/inputs707.json')
    old=json.loads((ROOT/'analysis/credit710-verification.json').read_text())
    for n,digest in old['boards']['707D']['reports'].items():
        p=board/'output_files'/n;assert sha(p)==digest;add(p,'board/'+n)
    for p in ROOT.glob('tools/*deadline711.py'):add(p,'tools/'+p.name)
    for n in ('deadline711-budget.json','credit710-verification.json','bg707-verification.json','bg707-archive.json','longrun694-verification.json'):
        add(ROOT/'analysis'/n,'analysis/'+n)
    add(ROOT/'docs/nes-deadline711-results.ko.md','docs/nes-deadline711-results.ko.md')
    pp=a.out/'pixels.json';pp.write_text(json.dumps(pixels,indent=2)+'\n');add(pp,'pixels.json')
    inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
    ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n')
    zp=a.out/'evidence.zip'
    with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
    with zipfile.ZipFile(zp) as z:
        for n,m in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==m['SHA256']
    r=dict(stage=711,location='WORKSPACE/probes/nes-deadline711/'+a.out.name,files=len(inventory),
        SHA256=sha(zp),inventory_SHA256=sha(ip),all_verified=True,original_game_ROM=False,license=False,
        private_derived_fixture=True,pixel_hashes_only=True,completed_CPU_runs=report['receiver_runs'],
        interrupted_controls=2,source_707D_archive='analysis/bg707-archive.json')
    (ROOT/'analysis/deadline711-archive.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(r))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
