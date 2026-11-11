"""Preserve the full links, schedule traces and STOP fixtures that back 736."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from nes_raw506 import sha


def archive(probe, temp, out, *, stage=736, name='prefix736',
            builds=('arm05','normal05','arm06','normal06'), tags=('a','b'),
            stops=('stop','warm-stop'), frame_count=212):
    root=Path(__file__).resolve().parents[1]
    proof=root/f'analysis/{name}-verification.json'
    verified=json.loads(proof.read_text())
    out.mkdir(exist_ok=False)
    files={f'analysis/{name}-verification.json':proof}
    doc=f'docs/nes-{name}-results.ko.md'
    files[doc]=root/doc
    for f in (root/'tools').glob(f'*{stage}*.py'):
        files['tools/'+f.name]=f
    for f in probe.iterdir():
        if f.is_file() and f.suffix in ('.ps1','.json','.log'):
            files['probe/'+f.name]=f
    for build in sorted(probe.iterdir()):
        if (build / 'size.log').is_file():
            for log in build.glob('*.log'):
                files[build.name + '/' + log.name] = log
    for build_name in builds:
        build=probe/build_name
        for f in [*build.glob('*.log'),build/'src/nes_native_sink165.c',
                  *(build/'src/obj-nes-100'/n for n in ('sd2snes.elf','sd2snes.map','firmware.stm'))]:
            files[build_name+'/'+f.name]=f
    for tag in tags:
        folder_stem=f'nes-{name}-{tag}'
        for ph in ('1','2'):
            folder=temp/(folder_stem+ph)
            pins=verified['trials'][tag][ph]['pins']
            assert all(sha(folder/k)==v for k,v in pins.items())
            for f in folder.iterdir():
                if f.suffix in ('.json','.jsonl','.csv','.lua','.log','.tsv'):
                    files[folder.name+'/'+f.name]=f
        for case in stops:
            stop_dir=f'nes-{name}-{case}-{tag}'
            fixture=temp/stop_dir
            for f in fixture.glob('*/*'):
                if f.suffix in ('.lua','.log','.json'):
                    files[stop_dir+'/'+f.parent.name+'/'+f.name]=f
            files[stop_dir+'/result.json']=fixture/'result.json'
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
    summary=dict(stage=stage,files=len(files),SHA256=sha(zip_path),inventory_SHA256=sha(index),
                 location=f'WORKSPACE/probes/nes-{name}/'+out.name,all_verified=True,new_CPU_frames=frame_count)
    (root/f'analysis/{name}-archive.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('probe','temp','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    archive(a.probe,a.temp,a.out)
