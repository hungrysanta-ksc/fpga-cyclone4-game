"""Preserve the full links, schedule traces and STOP fixtures that back 735."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from nes_raw506 import sha


def archive(probe, temp, out):
    root=Path(__file__).resolve().parents[1]
    proof=root/'analysis/tail735-verification.json'
    verified=json.loads(proof.read_text())
    out.mkdir(exist_ok=False)
    files={'analysis/tail735-verification.json':proof}
    files['docs/nes-tail735-results.ko.md']=root/'docs/nes-tail735-results.ko.md'
    for f in (root/'tools').glob('*735*.py'):
        files['tools/'+f.name]=f
    for f in probe.iterdir():
        if f.is_file() and f.suffix in ('.ps1','.json','.log'):
            files['probe/'+f.name]=f
    for name in ('arm01','normal01','arm02','normal02'):
        build=probe/name
        for f in [*build.glob('*.log'),build/'src/nes_native_sink165.c',
                  *(build/'src/obj-nes-100'/n for n in ('sd2snes.elf','sd2snes.map','firmware.stm'))]:
            files[name+'/'+f.name]=f
    for tag,folder_stem,stop_dir in [('A','nes-tail735-a','stop06'),('B','nes-tail735-b','stop-obj')]:
        for ph in ('1','2'):
            folder=temp/(folder_stem+ph)
            pins=verified['variants'][tag]['phases'][ph]['pins']
            assert all(sha(folder/k)==v for k,v in pins.items())
            for f in folder.iterdir():
                if f.suffix in ('.json','.jsonl','.csv','.lua','.log','.tsv'):
                    files[folder.name+'/'+f.name]=f
        fixture=Path((probe/stop_dir/'fixture-path.txt').read_text().strip())
        for f in fixture.glob('*/*'):
            if f.suffix in ('.lua','.log','.json'):
                files[stop_dir+'/'+f.parent.name+'/'+f.name]=f
        files[stop_dir+'/result.json']=probe/stop_dir/'result.json'
    for failed in ('stop01','stop02','stop04'):
        for f in (probe/failed).glob('*/*'):
            if f.suffix in ('.lua','.log'):
                files['earlier-fixtures/'+failed+'/'+f.parent.name+'/'+f.name]=f
    inventory={n:dict(bytes=f.stat().st_size,SHA256=sha(f)) for n,f in sorted(files.items())}
    index=out/'inventory.json'
    index.write_text(json.dumps(inventory,indent=2)+'\n')
    zip_path=out/'evidence.zip'
    with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED) as z:
        for n,f in sorted(files.items()):
            z.write(f,n)
    with zipfile.ZipFile(zip_path) as z:
        for n,r in inventory.items():
            assert hashlib.sha256(z.read(n)).hexdigest()==r['SHA256']
    summary=dict(stage=735,files=len(files),SHA256=sha(zip_path),inventory_SHA256=sha(index),
                 location='WORKSPACE/probes/nes-tail735/'+out.name,all_verified=True,new_CPU_frames=212)
    (root/'analysis/tail735-archive.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('probe','temp','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    archive(a.probe,a.temp,a.out)
