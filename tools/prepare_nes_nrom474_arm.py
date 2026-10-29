# SPDX-License-Identifier: MIT
"""474: exact same-frame BG-group reuse and guarded quiet status polling on471."""
import argparse, json, shutil
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha, once

p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
names=['nes_native165.c','nes_native_runtime165.c','nes_runtime_board165.inc','nes_game149_spi.inc',
       'nes_native165_bulk.inc','nes_budget210.c','nes_cost471.h','nes_cost471.c',
       'nes_planner211.c','nes_sink_window184.c','nes_sink_window184.h']
for n in names:shutil.copyfile(a.base/n,d/n)
for name,fn in [('nes_game149_spi.inc','nes_game149_transfer'),('nes_native165_bulk.inc','nes_native165_bulk')]:
 f=d/name;s=f.read_text();s=once(s,' uint32_t t=nes_cost471_now();bool ok='+fn+'_inner471(',
     ' unsigned opcode474=tx?tx[0]:255;uint32_t t=nes_cost471_now();bool ok='+fn+'_inner471(')
 s=once(s,'nes_cost471_op(tx?tx[0]:255,','nes_cost471_op(opcode474,');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_cost471.h';s=f.read_text();s=once(s,'#include <stdint.h>','#include <stdint.h>\n#include <stdbool.h>')
s=once(s,'#endif','''struct nes_cost474_wait {uint64_t cycles;uint32_t calls,progress,quiet,max_cycles;};
extern struct nes_cost474_wait nes_cost474_waits[3];
extern uint32_t nes_cost474_groups,nes_cost474_reused;
bool nes_cost474_pause(void *,bool (*)(void *),unsigned,bool);
#endif''');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_cost471.c';s=f.read_text();s=once(s,'static uint32_t active,old_trace,old_count;', '''struct nes_cost474_wait nes_cost474_waits[3];
uint32_t nes_cost474_groups,nes_cost474_reused;
static uint32_t active,old_trace,old_count;''')
s=once(s,'uint32_t nes_cost471_now(void){return REG471(0xe0001004u);}', '''uint32_t nes_cost471_now(void){
#ifdef NES_COST474_TEST
 extern uint32_t nes_cost474_test_now(void);return nes_cost474_test_now();
#else
 return REG471(0xe0001004u);
#endif
}''')
s=once(s,' nes_cost471_crc_errors=nes_cost471_transfer_stops=0;', ''' nes_cost471_crc_errors=nes_cost471_transfer_stops=0;
 memset(nes_cost474_waits,0,sizeof nes_cost474_waits);nes_cost474_groups=nes_cost474_reused=0;''')
s=once(s,'cost_schema=471','cost_schema=474')
s=once(s,' return n;\n}', ''' z=snprintf(text+n,size-(unsigned)n,"cost_group_total=%lu\\ncost_group_reused=%lu\\ncost_poll_fields=calls,progress,quiet,cycles_hi,cycles_lo,max_cycles\\ncost_poll_order=CREDIT,DRAIN,FINAL_ACK\\ncost_quiet_budget_us=128\\n",(unsigned long)nes_cost474_groups,(unsigned long)nes_cost474_reused);
 if(z<0||(unsigned)z>=size-(unsigned)n)return -1;
 n+=z;
 for(unsigned k=0;k<3;k++){
  const struct nes_cost474_wait *w=&nes_cost474_waits[k];
  z=snprintf(text+n,size-(unsigned)n,"cost_poll_%u=%lu,%lu,%lu,%lu,%lu,%lu\\n",k,(unsigned long)w->calls,(unsigned long)w->progress,(unsigned long)w->quiet,(unsigned long)(w->cycles>>32),(unsigned long)w->cycles,(unsigned long)w->max_cycles);
  if(z<0||(unsigned)z>=size-(unsigned)n)return -1;
  n+=z;
 }
 return n;
}''')
s+='''
/* Called only between complete SPI transactions. Immediate first status and
 * progress/completion checks stay in the window. Quiet work services the
 * original deadline/fault/observer guard; IRQ/service may extend128us. */
bool nes_cost474_pause(void *ctx,bool (*guard)(void *),unsigned reason,bool progress){
 if(reason>=3||!guard)return false;
 struct nes_cost474_wait *w=&nes_cost474_waits[reason];w->calls++;
 if(progress){w->progress++;return true;}
 if(!nes_cost471_available)return guard(ctx);
 w->quiet++;uint32_t began=nes_cost471_now(),elapsed;
 do {if(!guard(ctx))return false;elapsed=nes_cost471_now()-began;}while(elapsed<84u*128u);
 w->cycles+=elapsed;if(elapsed>w->max_cycles)w->max_cycles=elapsed;
 return true;
}
''';f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_sink_window184.h';s=f.read_text();s=once(s,' nes_window184_transfer transfer;',
 ' bool (*wait)(void *,bool (*)(void *),unsigned,bool);\n nes_window184_transfer transfer;');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_sink_window184.c';s=f.read_text();s=once(s,'static bool credit(struct nes_sink_window184 *s){','''static bool wait474(struct nes_sink_window184 *s,unsigned reason,bool progress){
 return !s->wait||s->wait(s->ctx,s->guard,reason,progress)||fail(s,2);
}
static bool credit(struct nes_sink_window184 *s){''')
s=once(s,'  if(!status(s,ack))return false;\n  if((uint16_t)(s->sent-s->retired)<4)return true;',
 '''  uint16_t before=s->retired;
  if(!status(s,ack))return false;
  bool done=(uint16_t)(s->sent-s->retired)<4;
  if(!wait474(s,0,done||s->retired!=before))return false;
  if(done)return true;''')
s=once(s,'  if(!status(s,ack))return false;\n  if(s->retired==s->sent){',
 '''  uint16_t before=s->retired;
  if(!status(s,ack))return false;
  if(s->retired==s->sent){''')
s=once(s,'   return true;\n  }\n }\n return fail(s,7);',
 '''   return wait474(s,s->last[0]==3?2:1,true);
  }
  if(!wait474(s,s->last[0]==3?2:1,s->retired!=before))return false;
 }
 return fail(s,7);''');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_native_runtime165.c';s=f.read_text();s=once(s,' nes_sink165_reset(&s->sink,',
 ' s->transport.wait=nes_cost474_pause;\n nes_sink165_reset(&s->sink,');f.write_text(s,encoding='utf8',newline='\n')
f=d/'nes_planner211.c';s=f.read_text();s='#include "nes_cost471.h"\n'+s
s=once(s,' for(unsigned g=0;g<groups;g++){\n  uint64_t exceptional=0;', ''' uint32_t reusable474=0;unsigned reused474=0;
 for(unsigned g=0;g<groups;g++){
  nes_cost474_groups++;
  uint64_t exceptional=0;''')
s=once(s,'  if(exceptional&1)exceptional=UINT64_C(0x1ffffffff);\n  for(unsigned x=0;x<33;x++){', '''  if(exceptional&1)exceptional=UINT64_C(0x1ffffffff);
  /* Exact reuse only inside this COMMITTED immutable frame. Earlier groups'
   * slots are already marked used and cannot be evicted. No cross-frame
   * hash/history or coverage shortcut; exceptional mappings never qualify. */
  unsigned reuse=g;
  /* Bound unproductive comparisons: after four different initial groups,
   * fall back to the original allocator for the rest of this frame. */
  if(!exceptional&&(g<4||reused474))for(unsigned h=0;h<g;h++){
   if((reusable474&(UINT32_C(1)<<h))&&
      !memcmp(&s->maps[(s->rows[first[g]]>>3)*33],&s->maps[(s->rows[first[h]]>>3)*33],66)){reuse=h;break;}
  }
  if(reuse!=g){
   unsigned old_column=column225(s->raster[first[reuse]]),new_column=column225(s->raster[first[g]]);
   for(unsigned x=0;x<33;x++){
    unsigned c=(old_column+x)&63u,old_at=((c/32)*1024+reuse*32+c%32)*2;
    unsigned word=(unsigned)p->map[old_at]|((unsigned)p->map[old_at+1]<<8);
    unsigned cell=s->maps[(s->rows[first[g]]>>3)*33+x];
    word=(word&~0x1c00u)|((bank[g]*4+(cell>>13))<<10);
    c=(new_column+x)&63u;map_word185(p,((c/32)*1024+g*32+c%32)*2,word);
   }
   reusable474|=UINT32_C(1)<<g;reused474++;nes_cost474_reused++;continue;
  }
  if(!exceptional)reusable474|=UINT32_C(1)<<g;
  for(unsigned x=0;x<33;x++){''');f.write_text(s,encoding='utf8',newline='\n')
r={'base':{n:sha(a.base/n) for n in names},'generated':{n:sha(d/n) for n in names},
   'scope':'same-frame exact nonexceptional group reuse; existing independent validation/4credit/ACK; guarded128us quiet after no-progress status; no FPGA or cross-frame history change'}
(d/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print('474 patch prepared',len(names),'files')
