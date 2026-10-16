# SPDX-License-Identifier: MIT
"""Extract actual board synthesis accounting; preserve raw reports alongside it."""
from pathlib import Path
import argparse,json,re
from nes_metadata203 import ROOT,BASE,sha

def report(path):
 s=path.read_text(errors='strict');a=s.index('; Compilation Hierarchy Node');b=s.index('; Analysis & Synthesis RAM Summary',a)
 entities=[]
 for line in s[a:b].splitlines():
  c=[x.strip() for x in line.split(';')]
  if len(c)>6 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   entities.append(dict(node=c[1],aluts=int(c[2].split()[0]),registers=int(c[3].split()[0]),memory_bits=int(c[4])))
 summary={}
 for key in ['Total logic elements','Total combinational functions','Total registers','Total memory bits']:
  m=re.search(r'; '+key+r'\s*; ([\d,]+)',s);assert m,key;summary[key]=int(m[1].replace(',',''))
 return dict(path=path.relative_to(BASE).as_posix(),sha256=sha(path),summary=summary,entities=entities)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 old=report(BASE/'probes/nes-window184-coupled/evidence/route02/output_files/board.map.rpt')
 new=report(BASE/'probes/nes-board204/map01/output_files/board.map.rpt')
 delta={k:new['summary'][k]-old['summary'][k] for k in old['summary']}
 r=dict(baseline=old,candidate=new,delta=delta,script_sha256=sha(Path(__file__)),
  scope='Synthesis estimates and hierarchical ALUT/register accounting, not fitted LE/LAB or timing. Parent counts include children; do not sum them.',
  next='Use actual FIT resource/routing result. Review tile191 duplicate 32B register tile versus bulk193 32B sealed RAM, variable row/tag selects, and duplicate endpoint descriptor/token state as one structural budget. Preserve atomic tile publication, source epoch, core priority and bounded STOP; do not lower clocks or serialize capture until display ACK.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(delta=delta)))
if __name__=='__main__':main()
