# SPDX-License-Identifier: MIT
"""Immutable403 raw evidence, without private license logs or rebuildable DB."""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',nargs='+',required=True);a=p.parse_args();saved=[]
 for run in a.runs:
  assert re.fullmatch(r'(trace|ram)[0-9]+',run)
  src=Path('C:/Users/mohallo/AppData/Local/Temp')/('nes-scope403-'+run);dst=BASE/'probes/nes-scope403'/run;assert src.is_dir();dst.mkdir(parents=True,exist_ok=True);files={}
  for q in src.rglob('*'):
   rel=q.relative_to(src)
   if not q.is_file()or any(x in('work','db','incremental_db','.simulator')for x in rel.parts):continue
   if q.suffix.lower()in('.wlf','.rdb','.qdb','.bak')or q.name=='modelsim.ini':continue
   n=q.name.lower()
   if 'license'in n or 'private'in n or n=='server.log'or n.startswith('lmgrd'):continue
   out=dst/rel;out.parent.mkdir(parents=True,exist_ok=True)
   if out.exists():assert sha(out)==sha(q),str(out)
   else:shutil.copyfile(q,out)
   files[rel.as_posix()]=dict(bytes=out.stat().st_size,sha256=sha(out))
  text=json.dumps(dict(run=run,files=files,raw_logs_unfiltered=True),indent=2)+'\n';m=dst/'archive403.json'
  if m.exists():assert m.read_text()==text
  else:m.write_text(text,newline='\n')
  saved.append(dict(run=run,files=len(files),bytes=sum(v['bytes']for v in files.values())))
 print(json.dumps(saved))
if __name__=='__main__':main()
