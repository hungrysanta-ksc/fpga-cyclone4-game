# SPDX-License-Identifier: MIT
"""Small MCU-only frame lifecycle trace. Existing165 FPGA protocol unchanged."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_runlease165 import prepare as parent_prepare

def receiver(s):
 a='  if(!record(s,kind,gen,index,value))return false;'
 assert s.count(a)==1
 return s.replace('#include "nes_native165.h"','#include "nes_native165.h"\n#include "nes_trace166.h"').replace(a,a+'\n  nes_trace166_record(s,kind,gen,index,value);')

def prepare(evidence,out):
 prep=parent_prepare(evidence,out);diff=[]
 def edit(n,s):
  p=out/n;old=p.read_text(encoding='utf8');assert old!=s,n
  p.write_text(s,encoding='utf8',newline='\n');prep['added' if n in prep['added'] else 'changed'][n]=sha(p)
  diff.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='165/'+n,tofile='166/'+n))
 for e in ['c','h']:
  n='src/nes_trace166.'+e;p=out/n;p.write_text((ROOT/'src/nes/firmware'/p.name).read_text(),encoding='utf8',newline='\n');prep['added'][n]=sha(p)
 edit('src/nes_native165.c',receiver((out/'src/nes_native165.c').read_text()))
 p=out/'src/Makefile';s=p.read_text();assert s.count('nes_native165.c')==1;edit('src/Makefile',s.replace('nes_native165.c','nes_native165.c nes_trace166.c'))
 p=out/'src/nes_runtime_board165.inc';s=p.read_text()
 s=s.replace('#include "nes_native_runtime165.h"','#include "nes_native_runtime165.h"\n#include "nes_trace166.h"')
 a='(void)ctx;return getticks();';assert s.count(a)==1;s=s.replace(a,'(void)ctx;nes_trace166.now=getticks();return nes_trace166.now;')
 edit('src/nes_runtime_board165.inc',s)
 p=out/'src/nes_menu_diagnostic.c';s=p.read_text()
 s=s.replace('#include "nes_native_runtime165.h"','#include "nes_native_runtime165.h"\n#include "nes_trace166.h"')
 a=' memset(&native_runtime165,0,sizeof(native_runtime165));';assert s.count(a)==1;s=s.replace(a,a+'\n memset(&nes_trace166,0,sizeof(nes_trace166));')
 a=' n=history165_format(text,4096,n);';assert s.count(a)==1
 fields=['begins','ends','aborts','commits','records','first_begin_tick','first_abort_tick','generation','index','first_abort_generation','first_abort_records','first_abort_bytes','max_records','kind','state','first_abort_reason','last_abort_reason']
 fmt=''.join('trace_'+k+'=%lu\\n' for k in fields)
 args=','.join('(unsigned long)nes_trace166.'+k for k in fields)
 block='\n if(n>0&&(size_t)n<4096){\n  int used=snprintf(text+n,4096-(size_t)n,"'+fmt+'",'+args+');\n  n=used<0||(size_t)used>=4096-(size_t)n?-1:n+used;\n }'
 s=s.replace(a,a+block)
 # Paths/candidate only; keep native165 type/function names and FPGA bytes.
 for x,y in [('NES-GAME-165','NES-GAME-166'),('GAME 165','GAME 166'),('game165.nes','game166.nes'),('fpga_n165.bi3','fpga_n166.bi3'),('last-165.txt','last-166.txt')]:s=s.replace(x,y)
 edit('src/nes_menu_diagnostic.c',s)
 n='src/nes_checkpoint112.c';s=(out/n).read_text()
 edit(n,s.replace('NES165 seq=','NES166 seq=').replace('nes-progress-165.txt','nes-progress-166.txt'))
 n='src/VERSION';s=(out/n).read_text();edit(n,s.replace('NES-GAME165-DEV','NES-GAME166-DEV'))
 prep.update(parent_preparation_sha256=sha(out/'preparation-runlease165.json'),scope='166 lifecycle observation only; original165 FPGA and receiver validation/timeout unchanged; no video fix claimed.')
 # Existing checker consumes this final materialization inventory.
 (out/'preparation-runlease165.json').write_text(json.dumps(prep,indent=2)+'\n')
 (out/'preparation-trace166.json').write_text(json.dumps(prep,indent=2)+'\n')
 (out/'changes-trace166.diff').write_text(''.join(diff),encoding='utf8')
 return prep
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.evidence,a.out);print(json.dumps(dict(copied=len(r['copied']),changed=len(r['changed']),added=len(r['added']))))
