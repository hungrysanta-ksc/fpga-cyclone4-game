# SPDX-License-Identifier: MIT
"""Preserve first plan-status predicate/raw E8 without weakening200 checks."""
from pathlib import Path
import argparse,json,shutil
from nes_runtime213 import ROOT,BASE,sha,once
from nes_board181 import copy_pins

def service(s):
 s=once(s,'#include "nes_plan_service200.h"','#include "nes_plan_service200.h"\n#include "nes_plan215.h"\nstruct nes_plan215 nes_plan215;')
 s=once(s,'static bool valid(','''static bool status215(struct nes_plan200 *p,uint8_t phase,uint8_t reason,const uint8_t rx[20]){
 if(!nes_plan215.valid){
  nes_plan215.sent=p->sent;nes_plan215.generation=p->generation;nes_plan215.bytes=p->bytes;
  nes_plan215.count=p->count;nes_plan215.phase=phase;nes_plan215.reason=reason;
  memcpy(nes_plan215.reply,rx,20);nes_plan215.valid=1;
 }
 return fail(p,4);
}
static bool valid(''')
 s=once(s,'static bool poll(struct nes_plan200 *p,uint8_t *flags){','static bool poll(struct nes_plan200 *p,uint8_t *flags,uint8_t phase){')
 s=once(s,''' if(rx[1]!=0xd7||rx[2]!=4||rx[18]||crc8(rx+1,18)!=rx[19]||(rx[3]&0xfc)||
    (unsigned)rx[4]*256+rx[5]!=p->sent||rx[6]>1)return fail(p,4);''',''' if(rx[1]!=0xd7||rx[2]!=4)return status215(p,phase,NES_PLAN215_HEADER,rx);
 if(rx[18])return status215(p,phase,NES_PLAN215_RESERVED,rx);
 if(crc8(rx+1,18)!=rx[19])return status215(p,phase,NES_PLAN215_CRC,rx);
 if(rx[3]&0xfc)return status215(p,phase,NES_PLAN215_FLAGS,rx);
 if((unsigned)rx[4]*256+rx[5]!=p->sent)return status215(p,phase,NES_PLAN215_COUNT,rx);
 if(rx[6]>1)return status215(p,phase,NES_PLAN215_DESCRIPTOR,rx);''')
 s=once(s,'for(unsigned i=7;i<18;i++)if(rx[i])return fail(p,4);','for(unsigned i=7;i<18;i++)if(rx[i])return status215(p,phase,NES_PLAN215_EMPTY,rx);\n  if(phase==NES_PLAN215_FLUSH&&(rx[3]&2))return status215(p,phase,NES_PLAN215_EARLY_END,rx);')
 s=once(s,'''  if(!poll(p,&flags))return false;
  if(flags&2)return fail(p,4);''','''  if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;''')
 s=once(s,'if(!poll(p,&flags))return false;','if(!poll(p,&flags,NES_PLAN215_FINISH))return false;')
 s=once(s,'''  if(rx[1]!=0xd7||rx[2]!=4||crc8(rx+1,18)!=rx[19]||(rx[3]&0xf8))return fail(p,4);
  for(unsigned k=6;k<19;k++)if(rx[k])return fail(p,4);''','''  uint8_t phase=sent?NES_PLAN215_REARM:NES_PLAN215_RETIRE;
  if(rx[1]!=0xd7||rx[2]!=4)return status215(p,phase,NES_PLAN215_HEADER,rx);
  if(crc8(rx+1,18)!=rx[19])return status215(p,phase,NES_PLAN215_CRC,rx);
  if(rx[3]&0xf8)return status215(p,phase,NES_PLAN215_FLAGS,rx);
  for(unsigned k=6;k<19;k++)if(rx[k])return status215(p,phase,NES_PLAN215_EMPTY,rx);''')
 s=once(s,'if(rx[3]!=2||accepted!=p->sent)return fail(p,4);','if(rx[3]!=2||accepted!=p->sent)return status215(p,phase,NES_PLAN215_RETIRE_STATE,rx);')
 s=once(s,'else if((rx[3]!=2&&rx[3]!=6)||accepted!=p->sent)return fail(p,4);','else if((rx[3]!=2&&rx[3]!=6)||accepted!=p->sent)return status215(p,phase,NES_PLAN215_REARM_STATE,rx);')
 return s

def prepare(out):
 prior=BASE/'probes/nes-startup214/arm02';p=json.loads((prior/'preparation-startup214.json').read_bytes());pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);src=out/'src'
 shutil.copyfile(ROOT/'src/nes/firmware/nes_plan215.h',src/'nes_plan215.h')
 f=src/'nes_plan_service200.c';f.write_text(service(f.read_text()),encoding='utf8')
 f=src/'nes_boot214.inc';s=once(f.read_text(),'#include "nes_boot214.h"','#include "nes_boot214.h"\n#include "nes_plan215.h"');s=once(s,'nes_boot214=(struct nes_boot214){0};','nes_plan215=(struct nes_plan215){0};\n nes_boot214=(struct nes_boot214){0};');f.write_text(s,encoding='utf8')
 f=src/'nes_budget210.c';s=once(f.read_text(),'#include "nes_boot214.h"','#include "nes_boot214.h"\n#include "nes_plan215.h"');s=s.replace('budget_schema=214','budget_schema=215')
 s=once(s,' for(unsigned i=0;i<12;i++){',r''' int cause=snprintf(text+n,size-(unsigned)n,
  "plan_schema=215\nplan_valid=%u\nplan_phase=%u\nplan_reason=%u\nplan_expected_sent=%u\nplan_generation=%u\nplan_buffer_bytes=%u\nplan_buffer_count=%u\nplan_reply_hex=",
  (unsigned)nes_plan215.valid,(unsigned)nes_plan215.phase,(unsigned)nes_plan215.reason,
  (unsigned)nes_plan215.sent,(unsigned)nes_plan215.generation,(unsigned)nes_plan215.bytes,(unsigned)nes_plan215.count);
 if(cause<0||(unsigned)cause>=size-(unsigned)n)return -1;
 n+=cause;
 for(unsigned i=0;i<20;i++){
  int hex=snprintf(text+n,size-(unsigned)n,"%02x",(unsigned)nes_plan215.reply[i]);
  if(hex<0||(unsigned)hex>=size-(unsigned)n)return -1;
  n+=hex;
 }
 if(size-(unsigned)n<2)return -1;
 text[n++]='\n';text[n]=0;
 for(unsigned i=0;i<12;i++){''');f.write_text(s,encoding='utf8')
 for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  f=src/name;s=f.read_text()
  for x,y in [('NES-GAME-214','NES-GAME-215'),('GAME 214','GAME 215'),('game214.nes','game215.nes'),('fpga_n214.bi3','fpga_n215.bi3'),('last-214.txt','last-215.txt'),('NES214','NES215'),('nes-progress-214.txt','nes-progress-215.txt'),('nes-budget-214.txt','nes-budget-215.txt'),('NES-GAME214-DEV','NES-GAME215-DEV')]:s=s.replace(x,y)
  f.write_text(s,encoding='utf8')
 changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h};added={'src/nes_plan215.h':sha(src/'nes_plan215.h')}
 sources=['tools/nes_plan215.py','src/nes/firmware/nes_plan215.h']
 result=dict(copied=pins,changed=changed,added=added,public_sources={n:sha(ROOT/n) for n in sources},new_fpga=False,root_cause_fixed=False)
 (out/'preparation-plan215.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.out)['changed']))
