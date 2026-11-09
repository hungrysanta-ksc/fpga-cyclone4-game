"""Preserve stage675 raw timing, linked binaries and RTL evidence privately."""
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
    for phase in (1,2):
        folder=a.traces/f'nes-bg675-grant{phase}'
        for f in folder.iterdir():
            if f.is_file():files[f'phase{phase}/'+f.name]=f
    folder=a.traces/'nes-bg675-rtl01'
    for f in folder.iterdir():
        if f.is_file() and f.suffix in ('.sv','.svh','.log','.json'):
            files['rtl/'+f.name]=f
    for f in a.probe.iterdir():
        if f.is_file() and f.name!='float-private.log':files['checks/'+f.name]=f
    root=a.probe/'grant01'
    for f in root.rglob('*'):
        if f.is_file() and (f.suffix in ('.c','.h','.su','.log','.ld','.mk') or f.name in ('Makefile','firmware.stm','sd2snes.elf','sd2snes.map')):
            files['candidate/'+f.relative_to(root).as_posix()]=f
    for f in Path('tools').glob('*675.py'):files['tools/'+f.name]=f
    files['analysis/bg675-verification.json']=Path('analysis/bg675-verification.json')
    assert not any('license' in name.lower() or 'float-private' in name.lower() for name in files)
    manifest={k:dict(bytes=f.stat().st_size,SHA256=digest(f)) for k,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for k,f in sorted(files.items()):z.write(f,k)
    with zipfile.ZipFile(zpath) as z:
        assert set(z.namelist())==set(manifest)
        for k,v in manifest.items():
            data=z.read(k);assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['SHA256']
    a.report.write_text(json.dumps(dict(stage=675,location='WORKSPACE/probes/nes-bg675/archive01',
        files=len(files),bytes=zpath.stat().st_size,SHA256=digest(zpath),manifest_SHA256=digest(a.out/'manifest.json'),
        all_extracted_bytes_verified=True,private=True,license_files_included=False),indent=2)+'\n')
