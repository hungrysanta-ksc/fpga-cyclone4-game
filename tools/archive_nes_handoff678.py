"""Freeze stage678 raw traces and linked artifacts, then verify every archived byte."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from check_nes_fault641 import digest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','probe','out','report'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);files={}
    for tag in ('input','multi','credit'):
        for n in (1,2):
            for f in (a.traces/f'nes-handoff678-{tag}{n}').iterdir():
                if f.is_file():files[f'{tag}/phase{n}/'+f.name]=f
    for f in a.probe.iterdir():
        if f.is_file() and f.name!=a.out.name+'.log':files['checks/'+f.name]=f
    for tag in ('input','multi','credit'):
        root=a.probe/(tag+'01')
        for f in root.rglob('*'):
            if f.is_file() and (f.suffix in ('.c','.h','.su','.log','.ld','.mk') or f.name in ('Makefile','firmware.stm','sd2snes.elf','sd2snes.map')):
                files[tag+'/candidate/'+f.relative_to(root).as_posix()]=f
    for f in Path('tools').glob('*678.py'):files['tools/'+f.name]=f
    files['analysis/handoff678-verification.json']=Path('analysis/handoff678-verification.json')
    files['analysis/handoff678-input-verification.json']=Path('analysis/handoff678-input-verification.json')
    files['analysis/handoff678-multi-verification.json']=Path('analysis/handoff678-multi-verification.json')
    assert not any('license' in n.lower() or 'float-private' in n.lower() for n in files)
    manifest={k:dict(bytes=f.stat().st_size,SHA256=digest(f)) for k,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    archive=a.out/'evidence.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for k,f in sorted(files.items()):z.write(f,k)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(manifest)
        for k,v in manifest.items():
            b=z.read(k);assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['SHA256'],k
    a.report.write_text(json.dumps(dict(stage=678,location='WORKSPACE/probes/nes-handoff678/'+a.out.name,files=len(files),
        bytes=archive.stat().st_size,SHA256=digest(archive),manifest_SHA256=digest(a.out/'manifest.json'),
        all_extracted_bytes_verified=True,private=True,license_files_included=False),indent=2)+'\n',newline='\n')
