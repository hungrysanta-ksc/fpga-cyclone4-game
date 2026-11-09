"""Preserve694 integration and695/696 delivery evidence, excluding licensed tools."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):
    a.out.mkdir(parents=True,exist_ok=False);files={}
    banned={'work','db','incremental_db','__pycache__'}
    extensions={'.py','.ps1','.c','.h','.inc','.su','.ld','.mk','.log','.json','.csv','.tsv','.txt','.rpt','.summary','.smsg','.sv','.v','.qsf','.qpf','.sdc','.tcl','.hex','.mif','.sfc','.stm','.elf','.map','.bin','.rbf','.sof','.bi3','.lua','.jsonl','.md','.zip'}
    def collect(root,prefix,board=False):
        for f in root.rglob('*'):
            if not f.is_file() or a.out in f.parents:continue
            r=f.relative_to(root)
            if any(p.startswith('archive') or p in banned for p in r.parts):continue
            if any(n in f.name.lower() for n in ('license','wrapper','server','float-private')):continue
            if f.suffix not in extensions and f.name!='Makefile':continue
            if board and len(r.parts)>1 and r.parts[0]!='output_files':continue
            files[prefix+'/'+r.as_posix()]=f
    collect(a.probe,'candidate');collect(a.delivery,'delivery')
    for d in sorted(a.traces.glob('nes-longrun694-*')):
        if d.is_dir():collect(d,'runs/'+d.name,board='board' in d.name)
    for d in sorted(a.traces.glob('nes-trial696-*')):
        if d.is_dir():collect(d,'runs/'+d.name)
    for f in Path('tools').glob('*694*.py'):files[f.as_posix()]=f
    for f in Path('tools').glob('*695*.py'):files[f.as_posix()]=f
    for n in ('analysis/longrun694-verification.json','analysis/trial695-package.json','docs/nes-longrun694-results.ko.md','docs/nes-mmc695-696-trial.ko.md'):
        files[n]=Path(n)
    manifest={n:{'bytes':f.stat().st_size,'SHA256':sha(f)} for n,f in sorted(files.items())}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=a.out/'evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for n,f in sorted(files.items()):z.write(f,n)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(manifest)
        for n,v in manifest.items():
            b=z.read(n);assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['SHA256'],n
    result={'stage':694,'location':'WORKSPACE/probes/nes-longrun694/'+a.out.name,'files':len(files),'bytes':archive.stat().st_size,
        'SHA256':sha(archive),'manifest_SHA256':sha(a.out/'manifest.json'),'all_extracted_bytes_verified':True,'private':True,
        'license_files_included':False,'full_inventory':'manifest.json inside private archive directory',
        'selected':'694 arm01/client01/board01/step1+2/wrap03/boot02/bus01/plan01/exit02/stop01;695 arm695/arm696/checks02/trial02 (canonical LF reports)',
        'failed_and_intermediate_evidence_preserved':True}
    a.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print('PASS694 archive',len(files),archive.stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','delivery','traces','out','report'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
