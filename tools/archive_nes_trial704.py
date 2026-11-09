"""Preserve704/705 exact delivery, linked source, board and test evidence privately."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);files={}
    allowed={'.py','.ps1','.c','.h','.inc','.su','.ld','.mk','.log','.json','.csv','.tsv','.txt','.rpt','.summary','.smsg','.sv','.v','.qsf','.qpf','.sdc','.tcl','.hex','.mif','.sfc','.stm','.elf','.map','.bin','.rbf','.sof','.bi3','.md','.zip'}
    def collect(root,prefix):
        for f in root.rglob('*'):
            if not f.is_file() or a.out in f.parents:continue
            r=f.relative_to(root)
            if any(p in {'work','db','incremental_db','__pycache__','.git'} or p.startswith('archive') for p in r.parts):continue
            if any(n in f.name.lower() for n in ('license','wrapper','server','float-private')):continue
            if f.suffix not in allowed and f.name!='Makefile':continue
            files[prefix+'/'+r.as_posix()]=f
    collect(a.probe,'delivery')
    for d in sorted(a.temp.glob('nes-trial704-*')):
        if d.is_dir():collect(d,'runs/'+d.name)
    # The unchanged long board is already preserved by703; retain its pin/report proofs here.
    for n in ('analysis/bonus703-verification.json','analysis/bonus703-archive.json','analysis/trial704-package.json',
              'docs/nes-mmc704-705-trial.ko.md','docs/nes-trial704-results.ko.md'):
        files[n]=Path(n)
    for f in Path('tools').glob('*trial704.py'):files[f.as_posix()]=f
    manifest={n:{'bytes':f.stat().st_size,'SHA256':sha(f)} for n,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
    archive=a.out/'evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for n,f in sorted(files.items()):z.write(f,n)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(manifest)
        for n,v in manifest.items():
            b=z.read(n);assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['SHA256'],n
    result=dict(stage=704,location='WORKSPACE/probes/nes-trial704/'+a.out.name,files=len(files),bytes=archive.stat().st_size,
        SHA256=sha(archive),manifest_SHA256=sha(a.out/'manifest.json'),all_extracted_bytes_verified=True,private=True,
        license_files_included=False,game_ROM_included=False,selected='arm704-02/arm705/checks01/trial01; board01/image704/image705/romchecks',
        preserved_failure='First arm704 relative Out path failed before make after W: chdir; absolute-path arm704-02 passed; original directory preserved')
    a.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print('PASS704 archive',len(files),archive.stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out','report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
