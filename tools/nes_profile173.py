# SPDX-License-Identifier: MIT
"""173 bounded timing counters, reducing the48-byte166 telemetry to40 bytes."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha

TRACE_H='''/* SPDX-License-Identifier: MIT */
#ifndef NES_TRACE166_H
#define NES_TRACE166_H
#include "nes_native165.h"
/*173 schema: 40B allocation (old48B), no frame log or live SD traffic.
 * Successful receive/build/seal calls only; ticks have10ms resolution.
 * Build includes pattern staging callbacks. Seal includes SNES display ACK.
 * Last display tick is relative to runtime start; not a measured FPS. */
struct nes_trace166 {
 uint32_t begins,ends,aborts,commits;
 uint32_t mark_tick,receive_ticks,build_ticks,seal_ticks,last_display_tick;
 uint16_t generation;
 uint8_t first_abort_reason,last_abort_reason;
};
extern struct nes_trace166 nes_trace166;
void nes_trace166_record(const struct nes_native165 *,unsigned,unsigned,unsigned,uint64_t);
#endif
'''
TRACE_C='''/* SPDX-License-Identifier: MIT */
#include "nes_trace166.h"
struct nes_trace166 nes_trace166;
void nes_trace166_record(const struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t value){
 (void)s;struct nes_trace166 *t=&nes_trace166;t->generation=(uint16_t)gen;
 if(kind!=7)return;
 switch(index){
 case 0:t->begins++;break;
 case 1:t->ends++;break;
 case 2:if(!t->aborts)t->first_abort_reason=(uint8_t)value;
  t->aborts++;t->last_abort_reason=(uint8_t)value;break;
 case 3:t->commits++;break;
 default:break;
 }
}
'''

def runtime(s):
 s=s.replace('#include <string.h>','#include <string.h>\n#include "nes_trace166.h"')
 a=' struct nes_native165 *r=s->receiver;';assert s.count(a)==1
 s=s.replace(a,a+'\n nes_trace166.mark_tick=s->ticks(s->ctx);')
 a=' if(r->state==NES_NATIVE165_COMMITTED){';assert s.count(a)==1
 s=s.replace(a,' nes_trace166.receive_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;\n'+a)
 # Keep the actual statement's original line break; no guard or ACK bypass.
 start=s.index('  if(!guard(s)||!nes_sink165_begin(');end=s.index('  if(!s->sink.displayed)',start)
 s=s[:start]+'''  nes_trace166.mark_tick=s->ticks(s->ctx);
  if(!guard(s)||!nes_sink165_begin(&s->sink,r->generation)||
     !nes_native_video165_build(r,s->palette,s->video,nes_sink165_pattern,&s->sink))
   return fail(s,NES_RUNTIME165_DISPLAY);
  nes_trace166.build_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;
  nes_trace166.mark_tick=s->ticks(s->ctx);
  if(!nes_sink165_seal(&s->sink,s->video,5000)||!guard(s))
   return fail(s,NES_RUNTIME165_DISPLAY);
  nes_trace166.seal_ticks+=s->ticks(s->ctx)-nes_trace166.mark_tick;
'''+s[end:]
 s=s.replace('  s->frames++;s->generation=r->generation;', '  s->frames++;s->generation=r->generation;\n  nes_trace166.last_display_tick=s->ticks(s->ctx)-s->started;')
 return s

def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='5ceea88b399093b76c5d1d45d49055a38f8cd5eb406025daa601f3b811918e03'
 out.mkdir(parents=True,exist_ok=False)
 m=json.loads((prior/'preparation-boot172.json').read_bytes());pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,p);r['copied'][n]=h
 def put(n,s):
  (out/n).write_text(s,encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-172','NES-GAME-173'),('GAME 172','GAME 173'),('game172.nes','game173.nes'),('fpga_n172.bi3','fpga_n173.bi3'),('last-172.txt','last-173.txt'),('NES172 seq=','NES173 seq='),('nes-progress-172.txt','nes-progress-173.txt'),('NES-GAME172-DEV','NES-GAME173-DEV')]:s=s.replace(a,b)
  put(n,s)
 put('src/nes_trace166.h',TRACE_H);put('src/nes_trace166.c',TRACE_C)
 n='src/nes_runtime_board165.inc';s=(out/n).read_text();old='nes_trace166.now=getticks();return nes_trace166.now;';assert s.count(old)==1
 put(n,s.replace(old,'return getticks();'))
 put('src/nes_native_runtime165.c',runtime((out/'src/nes_native_runtime165.c').read_text()))
 n='src/nes_menu_diagnostic.c';s=(out/n).read_text();start=s.index('  int used=snprintf(text+n,4096-(size_t)n,"trace_begins=');end=s.index('  n=used<0',start)
 s=s[:start]+'''  int used=snprintf(text+n,4096-(size_t)n,"trace_schema=173\\ntrace_begins=%lu\\ntrace_ends=%lu\\ntrace_aborts=%lu\\ntrace_commits=%lu\\ntrace_generation=%u\\ntrace_first_abort_reason=%u\\ntrace_last_abort_reason=%u\\nprofile_tick_ms=10\\nprofile_receive_ticks=%lu\\nprofile_build_stage_ticks=%lu\\nprofile_seal_ack_ticks=%lu\\nprofile_last_display_tick=%lu\\n",(unsigned long)nes_trace166.begins,(unsigned long)nes_trace166.ends,(unsigned long)nes_trace166.aborts,(unsigned long)nes_trace166.commits,nes_trace166.generation,nes_trace166.first_abort_reason,nes_trace166.last_abort_reason,(unsigned long)nes_trace166.receive_ticks,(unsigned long)nes_trace166.build_ticks,(unsigned long)nes_trace166.seal_ticks,(unsigned long)nes_trace166.last_display_tick);
'''+s[end:]
 # Release173 reuses the exact172 FPGA. Its PPU history schema must remain157.
 # The experimental A3 observer failed timing and is deliberately excluded.
 put(n,s)
 for n in ['preparation-profile173.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.prior,a.out)
