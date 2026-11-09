"""Freeze all683 candidates, original failed attempts, binaries and raw traces."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from check_nes_fault641 import digest


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','probe','out','report'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);files={}
    for root in a.traces.glob('nes-pair683-*'):
        if not root.is_dir():continue
        for f in root.rglob('*'):
            if f.is_file() and not any(k in f.parts for k in ('work','__pycache__','db','incremental_db')):
                files['runs/'+root.name+'/'+f.relative_to(root).as_posix()]=f
    for f in a.probe.rglob('*'):
        if not f.is_file() or a.out in f.parents:continue
        relative=f.relative_to(a.probe)
        if relative.parts[0].startswith(('archive','repro-')):continue
        if any(k in f.name.lower() for k in ('license','wrapper')):continue
        if len(relative.parts)==1 or relative.parts[0].startswith('client') or f.suffix in ('.c','.h','.su','.log','.ld','.mk','.json') or f.name in ('Makefile','firmware.stm','sd2snes.elf','sd2snes.map'):
            if '__pycache__' not in f.parts:files['candidate/'+relative.as_posix()]=f
    for f in Path('tools').glob('*683.py'):files['tools/'+f.name]=f
    for f in Path('analysis').glob('pair683-*verification.json'):files[f.as_posix()]=f
    assert not any(any(word in name.lower() for word in ('license','wrapper','float-private')) for name in files)
    manifest={name:dict(bytes=f.stat().st_size,SHA256=digest(f)) for name,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    archive=a.out/'evidence.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for name,f in sorted(files.items()):z.write(f,name)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(manifest)
        for name,v in manifest.items():
            data=z.read(name);assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['SHA256'],name
    a.report.write_text(json.dumps(dict(stage=683,location='WORKSPACE/probes/nes-pair683/'+a.out.name,
        files=len(files),bytes=archive.stat().st_size,SHA256=digest(archive),manifest_SHA256=digest(a.out/'manifest.json'),
        all_extracted_bytes_verified=True,private=True,license_files_included=False),indent=2)+'\n',newline='\n')
