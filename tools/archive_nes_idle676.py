"""Preserve stage676 raw timing, linked binaries and RTL evidence privately."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from check_nes_fault641 import digest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','probe','out','report'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);files={}
    for tag in ('input','joint'):
        for phase in (1,2):
            folder=a.traces/f'nes-idle676-{tag}{phase}'
            for f in folder.iterdir():
                if f.is_file():files[f'{tag}/phase{phase}/'+f.name]=f
    for f in a.probe.iterdir():
        if f.is_file() and f.name not in ('float-private.log',a.out.name+'.log'):files['checks/'+f.name]=f
    for tag in ('input','joint'):
        root=a.probe/(tag+'01')
        for f in root.rglob('*'):
            if f.is_file() and (f.suffix in ('.c','.h','.su','.log','.ld','.mk') or f.name in ('Makefile','firmware.stm','sd2snes.elf','sd2snes.map')):
                files[tag+'/candidate/'+f.relative_to(root).as_posix()]=f
    root=a.traces/'nes-tail676-rtl01'
    for f in root.rglob('*'):
        if f.is_file() and f.suffix in ('.sv','.log','.json','.do','.ps1'):
            files['RTL/'+f.relative_to(root).as_posix()]=f
    for f in Path('tools').glob('*676.py'):files['tools/'+f.name]=f
    files['analysis/idle676-verification.json']=Path('analysis/idle676-verification.json')
    files['analysis/idle676-input-verification.json']=Path('analysis/idle676-input-verification.json')
    assert not any('license' in name.lower() or 'float-private' in name.lower() for name in files)
    manifest={k:dict(bytes=f.stat().st_size,SHA256=digest(f)) for k,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for k,f in sorted(files.items()):z.write(f,k)
    with zipfile.ZipFile(zpath) as z:
        assert set(z.namelist())==set(manifest)
        for k,v in manifest.items():
            data=z.read(k);assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['SHA256'],k
    a.report.write_text(json.dumps(dict(stage=676,location='WORKSPACE/probes/nes-idle676/'+a.out.name,
        files=len(files),bytes=zpath.stat().st_size,SHA256=digest(zpath),manifest_SHA256=digest(a.out/'manifest.json'),
        all_extracted_bytes_verified=True,private=True,license_files_included=False),indent=2)+'\n')
