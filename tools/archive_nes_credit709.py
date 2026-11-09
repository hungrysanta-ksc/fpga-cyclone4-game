"""Archive709 raw failures, actual ARM/RTL builds and matched timing evidence."""
import argparse,difflib,hashlib,json,zipfile
from pathlib import Path
from nes_raw506 import sha

ROOT=Path(__file__).resolve().parents[1]
def run(a):
    a.out.mkdir(parents=True,exist_ok=False);files={}
    def add(p,n):
        assert p.is_file(),p
        assert p.suffix.lower() not in ('.nes','.chr','.prg','.dat'),p
        assert 'license' not in n.lower() and n not in files,n
        files[n]=p
    for p in a.probe.iterdir():
        if p.is_file() and p.suffix in ('.json','.log','.ps1') and 'license' not in p.name:add(p,'probe/'+p.name)
    for name in ('arm01','arm-normal01','arm-needed01','arm-needed-normal01'):
        d=a.probe/name
        for p in d.glob('*.log'):add(p,name+'/'+p.name)
        for n in ('nes_sink_window184.c','nes_sink_window184.h'):add(d/'src'/n,name+'/src/'+n)
        for n in ('firmware.stm','sd2snes.elf','sd2snes.map','nes_sink_window184.su'):
            add(d/'src/obj-nes-100'/n,name+'/obj/'+n)
    for name in ('board01','board02','board03'):
        d=a.temp/('nes-credit709-'+name)
        for n in ('inputs709.json','nes_sink_spi165.sv','nes_sink_bridge165.sv','board.qsf','board.sdc'):
            if (d/n).exists():add(d/n,name+'/'+n)
        for p in (d/'output_files').iterdir():
            if p.suffix in ('.rpt','.summary','.sof'):add(p,name+'/output_files/'+p.name)
    for name in ('rtl02','rtl03','rtl04'):
        d=a.temp/('nes-credit709-'+name)
        for p in d.iterdir():
            if p.is_file() and p.suffix in ('.sv','.json','.log','.hex'):add(p,name+'/'+p.name)
    for name in ('nes-bg707-step1','nes-bg707-step2','nes-credit709-step1','nes-credit709-step2','nes-credit709-needed1','nes-credit709-needed2'):
        d=a.temp/name
        for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv','progress680.csv'):
            add(d/n,name+'/'+n)
    for p in ROOT.glob('tools/*credit709*.py'):add(p,'tools/'+p.name)
    add(ROOT/'tools/check_nes_status689_rtl.py','tools/check_nes_status689_rtl.py')
    for n in ('credit709-verification.json','bg707-verification.json','bg707-archive.json'):
        add(ROOT/'analysis'/n,'analysis/'+n)
    add(ROOT/'docs/nes-credit709-results.ko.md','docs/nes-credit709-results.ko.md')
    diffs={}
    for name,old,new in [('ARM',a.probe.parent/'nes-longrun694/arm01/src/nes_sink_window184.c',a.probe/'arm01/src/nes_sink_window184.c'),
        ('RTL_A',a.temp/'nes-bg707-board04/nes_sink_spi165.sv',a.temp/'nes-credit709-board01/nes_sink_spi165.sv'),
        ('RTL_B',a.temp/'nes-bg707-board04/nes_sink_spi165.sv',a.temp/'nes-credit709-board02/nes_sink_spi165.sv'),
        ('RTL_C',a.temp/'nes-bg707-board04/nes_sink_spi165.sv',a.temp/'nes-credit709-board03/nes_sink_spi165.sv'),
        ('ARM_needed',a.probe.parent/'nes-longrun694/arm01/src/nes_sink_window184.c',a.probe/'arm-needed01/src/nes_sink_window184.c')]:
        p=a.out/(name+'.patch');p.write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='base/'+old.name,tofile=name+'/'+new.name)),encoding='utf8',newline='\n')
        add(p,p.name);diffs[name]=sha(p)
    inventory={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(files.items())}
    ip=a.out/'inventory.json';ip.write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf8',newline='\n')
    zp=a.out/'evidence.zip'
    with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
    with zipfile.ZipFile(zp) as z:
        for n,m in inventory.items():assert hashlib.sha256(z.read(n)).hexdigest()==m['SHA256']
    r=dict(stage=709,location='WORKSPACE/probes/nes-credit709/'+a.out.name,files=len(inventory),SHA256=sha(zp),inventory_SHA256=sha(ip),patches=diffs,all_verified=True,raw_ROM=False,license=False)
    (ROOT/'analysis/credit709-archive.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
