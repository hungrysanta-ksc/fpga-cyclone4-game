# SPDX-License-Identifier: MIT
"""Preserve immutable 398 sources, raw diagnostics and measured event evidence.
Compiler caches and simulator work libraries are rebuildable and excluded.
No license/wrapper files are read by this tool.
"""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--temp',type=Path,default=Path('C:/Users/mohallo/AppData/Local/Temp'));p.add_argument('--runs',nargs='+',required=True);a=p.parse_args()
 saved=[]
 for name in a.runs:
  assert re.fullmatch(r'(?:build|map|host|exec|ea|live|hint|arm|armguard|owner|repeat|repeat32arm)[0-9]+',name),name
  src=a.temp/('nes-joint398-'+name);dst=BASE/'probes/nes-joint398'/name;assert src.is_dir(),src
  dst.mkdir(parents=True,exist_ok=True);inventory={}
  for q in src.rglob('*'):
   rel=q.relative_to(src)
   if not q.is_file()or any(x in ('work','db','incremental_db','.simulator')for x in rel.parts):continue
   if q.suffix.lower()in('.wlf','.rdb','.qdb','.bak')or q.name=='modelsim.ini':continue
   if any(x in q.name.lower()for x in ('license','private','server')):continue
   out=dst/rel;out.parent.mkdir(parents=True,exist_ok=True)
   if out.exists():assert sha(out)==sha(q),f'archive already differs: {out}'
   else:shutil.copyfile(q,out)
   inventory[rel.as_posix()]=dict(bytes=out.stat().st_size,sha256=sha(out))
  manifest=dst/'archive398.json';text=json.dumps(dict(run=name,files=inventory,raw_logs_unfiltered=True,excluded=['Questa work library','Quartus db/incremental_db','wave databases','license/private/server files']),ensure_ascii=False,indent=2)+'\n'
  if manifest.exists():assert manifest.read_text()==text
  else:manifest.write_text(text,newline='\n')
  saved.append(dict(run=name,files=len(inventory),bytes=sum(x['bytes']for x in inventory.values())))
 print(json.dumps(saved))
if __name__=='__main__':main()
