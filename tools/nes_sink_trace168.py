# SPDX-License-Identifier: MIT
"""Add bounded first-error ACK evidence to the deployed167 MCU; FPGA unchanged."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def sink_source(s):
 s=s.replace('#include "nes_native_sink165.h"','#include "nes_native_sink165.h"\n#include "nes_sink_trace168.h"')
 a=' memset(s,0,sizeof(*s));s->exchange=fn;s->ctx=ctx;'
 assert s.count(a)==1;s=s.replace(a,a+'\n memset(&nes_sink_trace168,0,sizeof(nes_sink_trace168));')
 a=' if(!s->exchange(s->ctx,b,n+16,ack))return fail(s,2);'
 assert s.count(a)==1;s=s.replace(a,' if(!s->exchange(s->ctx,b,n+16,ack)){nes_sink168_capture(b,ack,false,0);return fail(s,2);}')
 a=' if(ack[0]!=(op==3?1:0)||ack[1]!=op||memcmp(ack+2,b+2,8)||ack[10]!=0x65||ack[11]!=0x9a)return fail(s,3);'
 assert s.count(a)==1;s=s.replace(a,' uint8_t mismatch=nes_sink168_mismatch(b,ack);\n if(mismatch){nes_sink168_capture(b,ack,true,mismatch);return fail(s,3);}')
 return s

def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='783a3c831385c4dde009e6fe4b787bc6629f85db6afd317cb144ab2fe8bc86b0'
 original=json.loads((prior/'preparation-pacing167.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 pins=original['copied']|original['changed']|original['added'];prep=dict(copied={},changed={},added={});diff=[]
 for n,h in pins.items():
  f=prior/n;assert sha(f)==h,n;d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,d);prep['copied'][n]=h
 def edit(n,s):
  f=out/n;old=f.read_text();assert old!=s,n;f.write_text(s,encoding='utf8',newline='\n');prep['changed'][n]=sha(f)
  diff.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='167/'+n,tofile='168/'+n))
 for e in ['c','h']:
  n='src/nes_sink_trace168.'+e;shutil.copyfile(ROOT/'src/nes/firmware'/Path(n).name,out/n);prep['added'][n]=sha(out/n)
 edit('src/nes_native_sink165.c',sink_source((out/'src/nes_native_sink165.c').read_text()))
 f=out/'src/Makefile';s=f.read_text();assert s.count('nes_native_sink165.c')==1;edit('src/Makefile',s.replace('nes_native_sink165.c','nes_native_sink165.c nes_sink_trace168.c'))
 f=out/'src/nes_menu_diagnostic.c';s=f.read_text();s=s.replace('#include "nes_trace166.h"','#include "nes_trace166.h"\n#include "nes_sink_trace168.h"')
 a=' memset(&nes_trace166,0,sizeof(nes_trace166));';assert s.count(a)==1;s=s.replace(a,a+'\n memset(&nes_sink_trace168,0,sizeof(nes_sink_trace168));')
 a=' printf("%s",text);';assert s.count(a)==1
 s=s.replace(a,' int extra=nes_sink168_format(text+n,4096-(unsigned)n);\n if(extra<0)return;\n n+=extra;\n'+a)
 for a,b in [('NES-GAME-167','NES-GAME-168'),('GAME 167','GAME 168'),('game167.nes','game168.nes'),('fpga_n167.bi3','fpga_n168.bi3'),('last-167.txt','last-168.txt')]:s=s.replace(a,b)
 edit('src/nes_menu_diagnostic.c',s)
 f=out/'src/nes_checkpoint112.c';edit('src/nes_checkpoint112.c',f.read_text().replace('NES167 seq=','NES168 seq=').replace('nes-progress-167.txt','nes-progress-168.txt'))
 f=out/'src/VERSION';edit('src/VERSION',f.read_text().replace('NES-GAME167-DEV','NES-GAME168-DEV'))
 prep.update(scope='MCU-only32B first failed packet/ACK; same validation and fail-stop; no fix claim. Reuse167 FPGA/SNES.',prior_preparation_sha256=sha(prior/'preparation-pacing167.json'))
 for n in ['preparation-sink168.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(prep,indent=2)+'\n')
 (out/'changes-sink168.diff').write_text(''.join(diff),encoding='utf8');return prep
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();q=prepare(a.prior,a.out);print(json.dumps({k:len(q[k]) for k in ['copied','changed','added']}))
