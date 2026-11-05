"""Preserve private reproducible evidence; never archive license wrappers or servers."""
import argparse,json,zipfile
from pathlib import Path
from check_nes_wire600 import ROOT,sha,read

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','out','report'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);files={}
    inputs=read(a.traces/'nes-board611-candidate01/inputs611.json')
    for name in ('nes-board611-candidate01','nes-cdc576-board01'):
        folder=a.traces/name
        names=set(inputs)|{'inputs611.json','cdc611.sdc','review611.tcl','paths611.tsv','raw-paths611.tsv',
                         'second-paths611.tsv','review611.log','review611-allcorners.log','review611-original.log',
                         'setup611.rpt','recovery611.rpt','second611.rpt'}
        for n in names:
            if (folder/n).is_file():files[name+'/'+n]=folder/n
        for f in (folder/'output_files').iterdir():
            if f.suffix in ('.rpt','.summary','.smsg'):files[name+'/output_files/'+f.name]=f
    for name in ('nes-board611-sim01','nes-board611-life01',*[f'nes-board611-{x}{i}' for x in ('run','ref') for i in (1,2)]):
        folder=a.traces/name
        for f in folder.iterdir():
            if f.is_file() and f.suffix in ('.sv','.log','.json','.jsonl','.csv','.rgb','.bin','.sfc','.lua','.txt','.tsv','.hex','.palette','.cfg'):
                files[name+'/'+f.name]=f
        log=a.traces/(name+'.log')
        if log.is_file():files[name+'.log']=log
    inventory={n:dict(bytes=f.stat().st_size,sha256=sha(f)) for n,f in sorted(files.items())}
    (a.out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    with zipfile.ZipFile(a.out/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for n,f in sorted(files.items()):z.write(f,n)
    with zipfile.ZipFile(a.out/'evidence.zip') as z:assert z.testzip() is None
    a.report.write_text(json.dumps(dict(stage=611,location='WORKSPACE/probes/nes-board611/archive01',
        files=len(files),uncompressed_bytes=sum(v['bytes'] for v in inventory.values()),
        archive_bytes=(a.out/'evidence.zip').stat().st_size,archive_sha256=sha(a.out/'evidence.zip'),
        inventory_sha256=sha(a.out/'inventory.json'),private=True,license_files_included=False),indent=2)+'\n',newline='\n')
