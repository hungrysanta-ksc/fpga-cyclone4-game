# SPDX-License-Identifier: MIT
"""Bind the original native producer to the checked ARM output dispatcher."""
from nes_delta231 import BASE,ROOT,once,sha


def prepare(d):
    old=BASE/'probes/nes-wholepath247/jointdecode-host01'
    for name in ('nes_native_sink165.h','nes_sink_bulk195.h'):
        (d/name).write_bytes((old/name).read_bytes())
    s=(old/'nes_native_sink165.c').read_text()
    s=s.replace('#include "nes_sink_trace168.h"','extern unsigned dispatch289(const uint8_t *,unsigned);')
    s=s.replace(' memset(&nes_sink_trace168,0,sizeof(nes_sink_trace168));','')
    s=s.replace('uint8_t b[256]={0},ack[12]={0};','uint8_t b[256]={0};').replace('!s->exchange||','')
    a=s.index(' if(s->enqueue &&');b=s.index('\n}\nstatic bool packet(',a)
    s=s[:a]+''' if(!dispatch289(b,n+16))return fail(s,2);
 s->sequence++;s->state=old;return true;'''+s[b:]
    s=s.replace('r->prepared||s->state!=NES_SINK165_IDLE','!r->prepared||s->state!=NES_SINK165_IDLE')
    s=once(s,'static uint8_t maplast247[4096],mapstale247[2][256];static bool mapstarted247;', '''static uint8_t mapstale247[2][256];
void map_change289(unsigned at){if(at<4096){unsigned w=at/2;mapstale247[0][w/8]|=1u<<(w%8);mapstale247[1][w/8]|=1u<<(w%8);}}''')
    a=s.index('static bool manifest247(');b=s.index('static bool dirty_span231(',a)
    s=s[:a]+'''static bool manifest247(struct nes_native_sink165 *s,unsigned bank){
 const uint8_t *map=mapstale247[bank];
 unsigned cost=0,used=1;
 /* Count the exact packet cost without retaining a second encoded bitmap. */
 for(unsigned at=0;at<256;){
  unsigned end=at+1;bool zero=map[at]==0;
  while(end<256&&end-at<128&&(map[end]==0)==zero)end++;
  unsigned n=1+(zero?0:end-at);
  if(used+n>240){cost+=used+19;used=1;}used+=n;at=end;
 }
 cost+=used+19;
 if(cost>=294)return packet(s,10,2,0,map,240)&&packet(s,10,2,240,map+240,16);
 uint8_t b[240];unsigned start=0;used=1;b[0]=3;
 for(unsigned at=0;at<256;){
  unsigned end=at+1;bool zero=map[at]==0;
  while(end<256&&end-at<128&&(map[end]==0)==zero)end++;
  unsigned n=1+(zero?0:end-at);
  if(used+n>240){if(!packet(s,11,2,start,b,used))return false;start=at;used=1;}
  b[used++]=(uint8_t)((zero?128:0)+end-at-1);
  if(!zero){memcpy(b+used,map+at,end-at);used+=end-at;}
  at=end;
 }
 return packet(s,11,2,start,b,used);
}

'''+s[b:]
    a=s.index(' if(!mapstarted247)');b=s.index(' uint8_t b[240]={3};',a);s=s[:a]+s[b:]
    a=s.index(' uint8_t descriptor[190];');b=s.index(' s->last_generation=',a)
    s=s[:a]+''' extern uint8_t seal289[206];
 if(!packet(s,3,0,0,seal289+16,190))return false;
 /* Neither map state nor resident ownership commits on queue drain. */
 return true;
}
/* Unreachable legacy commit tail deliberately removed. */
'''+s[s.index('#include "nes_sink_bulk195.h"',b):]
    # Descriptor production has moved to the one shared prelude below.
    s=s.replace(' uint16_t budget=4192;','')
    s=s.replace(' s->last_generation=s->generation;s->displayed=true;s->state=NES_SINK165_IDLE;return true;','')
    s += '\n'+(ROOT/'tools/nes_native289.inc').read_text()
    (d/'nes_native289.c').write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_planner211.c';s=p.read_text();s=once(s,'static void map_word185(', 'extern void map_change289(unsigned);\nstatic void map_word185(')
    s=once(s,'{p->map_dirty|=','{map_change289(at);p->map_dirty|=');p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_planner285.c';s=p.read_text();s='extern void reset289(void);\nextern unsigned commit289(void),commit_ready289(void);\n'+s
    s=once(s,'void reset285(void){','void reset285(void){reset289();')
    s=once(s,'unsigned commit285(void){','unsigned commit285(void){\n if(!commit_ready289())return 0;')
    s=once(s,'resident285.target,true);','resident285.target,true)&&commit289();')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_input286.inc';s=p.read_text();s='extern void abort289(void);\n'+s
    s=once(s,'void stop286(void){','void stop286(void){abort289();');p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_output264.c';s=p.read_text();a=s.index('static unsigned frame_core284(');b=s.index('void reset259(',a)
    oldbody=s[a:b];a_body=oldbody.index('  if(n!=16+u16(p+12)',oldbody.index(' unsigned at=0,begin=0'))
    end=oldbody.index('\n }\n if(!begin||!seal)');body=oldbody[a_body:end].replace('continue;','return 1;')
    s=s[:a]+'''extern uint8_t seal289[206];
extern unsigned prepare289(void),produce289(void);
static unsigned begin,seal,requirements264;
unsigned dispatch289(const uint8_t *p,unsigned n){
 if(state259.error||n<16||n>256)return fail(12);
 unsigned serial=state259.serial,generation=state259.generation;
 const uint8_t *seal262=seal289;
'''+body+'''
 return 1;
}
static unsigned frame_core284(const uint8_t *plan,unsigned bytes,uint32_t serial,unsigned generation){
 (void)plan;(void)bytes;
 if(!serial||serial==0xffffffffu||serial<=state259.serial)return fail(11);
 if(!prepare289()||u32(seal289+4)!=serial||u16(seal289+8)!=generation)return fail(13);
 if(!drain())return 0;
 state259.serial=serial;state259.generation=generation;state259.bank=(serial-1)&1;state259.sequence=0;state259.token=0;
 begin=seal=requirements264=0;
 if(!h2(seal289)||!produce289()||!begin||!seal)return fail(18);
 trace259(1,serial);return 1;
}
'''+s[b:];p.write_text(s,encoding='utf-8',newline='\n')
    return {str(old/'nes_native_sink165.c'):sha(old/'nes_native_sink165.c')}
