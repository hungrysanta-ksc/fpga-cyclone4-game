# SPDX-License-Identifier: MIT
"""Paired1815: bounded long repeated-word DATA5 and constant-memory span planner.

DATA4 remains4..240; DATA5 expands242..4096 even bytes, physical payload2.
SNES validates section bounds first and services STOP/pad every64 output bytes.
No previous-frame cache, hash decision, larger frame buffer or physicalFPS claim.
"""
from pathlib import Path
import argparse, inspect, json
import nes_rawsteady181 as steady
import nes_sinkpack181 as packed
from nes_clip178 import replace

ROOT=Path(__file__).resolve().parents[1]


def source181(s):
    s=steady.source181(s)
    s=replace(s,"c.emit(0x29,255,0,0xc9,4,0);c.branch(0xf0,'packed_header181');",
        "c.emit(0x29,255,0,0xc9,4,0);c.branch(0xf0,'packed_header181');c.emit(0xc9,5,0);c.branch(0xf0,'packed_header181');")
    s=replace(s," c.emit(0xc9,4,0);cond(0xd0,'bad_packet');checkimm(0x120c,2)",""" c.emit(0xc9,5,0);cond(0xd0,'short_repeat1815');checkimm(0x120c,2)
 lda(0x120e);c.emit(0xc9,242,0);cond(0x90,'bad_packet');c.emit(0xc9,1,16);cond(0xb0,'bad_packet');c.jump('repeat_even1815')
 c.label('short_repeat1815');c.emit(0xc9,4,0);cond(0xd0,'bad_packet');checkimm(0x120c,2)""")
    s=replace(s," c.emit(0x89,1,0);cond(0xd0,'bad_packet');sta(0x120c)",
                   " c.label('repeat_even1815');c.emit(0x89,1,0);cond(0xd0,'bad_packet');sta(0x120c)")
    s=replace(s,"lda(0x1200);c.emit(0xc9,4);c.branch(0xd0,'literal1814')",
                   "lda(0x1200);c.emit(0xc9,4);c.branch(0xf0,'repeated1815');c.emit(0xc9,5);c.branch(0xd0,'literal1814');c.label('repeated1815')")
    s=replace(s," c.absolute(0xac,0x120c);c.label('repeat1814')",
                   " c.absolute(0xac,0x120c);c.emit(0xa2,32,0);c.label('repeat1814')")
    s=replace(s," c.emit(0x88,0x88);c.branch(0xd0,'repeat1814');c.emit(0xc2,0x20);c.jump('accepted')", """ c.emit(0x88,0x88);c.branch(0xf0,'repeat_done1815');c.emit(0xca);c.branch(0xd0,'repeat1814')
 call(c,'service');lda(0x1236);c.emit(0xc2,0x20);cond(0xd0,'stop_packet')
 c.emit(0xe2,0x20,0xa2,32,0);c.branch(0x80,'repeat1814')
 c.label('repeat_done1815');call(c,'service');lda(0x1236);c.emit(0xc2,0x20);cond(0xd0,'stop_packet');c.jump('accepted')""")
    return replace(s,'c.emit(0xc9,0x14,0x18)','c.emit(0xc9,0x15,0x18)')


def build(out):
    source=inspect.getsource(steady.build)
    ns=dict(steady.__dict__);ns['source181']=source181
    exec(compile(source,'stream181-build','exec'),ns)
    result=ns['build'](out)
    result.update(scope=__doc__,sink_version='1815',seal_version='1815',repeat_limit=4096,service_bytes=64)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


SPAN=r'''
/* Costs in eighth-bytes: header16 + minimum status/ACK35 +3*8us
 * at2.625MHz =471/8. Only compare wire cost; not a CPU/FPS measurement. */
static unsigned repeat_bytes(const uint8_t *b,unsigned n){
 unsigned i=2;if(n>4096)n=4096;
 while(i+1<n && b[i]==b[0] && b[i+1]==b[1])i+=2;
 return n<2?0:i;
}
static unsigned data_cost(const uint8_t *b,unsigned n){
 return 471+8*((n>=4 && !(n&1) && repeat_bytes(b,n)==n)?2:n);
}
static unsigned span_piece(const uint8_t *b,unsigned n){
 unsigned run=repeat_bytes(b,n);if(run>=64)return run;
 unsigned end=n<240?n:240;
 for(unsigned i=1;i<end;i++)if(repeat_bytes(b+i,n-i)>=64)return i;
 return end;
}
static bool span(struct nes_native_sink165 *s,unsigned section,unsigned offset,const uint8_t *b,unsigned n){
 if(!b||!n||n>4096)return fail(s,4);
 unsigned oldcost=0,newcost=0;
 for(unsigned at=0;at<n;){unsigned count=n-at;if(count>240)count=240;oldcost+=data_cost(b+at,count);at+=count;}
 for(unsigned at=0;at<n;){unsigned count=span_piece(b+at,n-at);newcost+=data_cost(b+at,count);at+=count;}
 /* Synchronous immutable source: the dry run retains no pointers/plan/cache.
  * Never split when the modeled total is equal or worse than legacy chunks. */
 for(unsigned at=0;at<n;){
  unsigned count=n-at;
  if(newcost<oldcost)count=span_piece(b+at,count);else if(count>240)count=240;
  bool ok=count>240?packet_wire(s,5,section,offset+at,b+at,2,count):packet(s,2,section,offset+at,b+at,count);
  if(!ok)return false;
  at+=count;
 }
 return true;
}
'''


def sink(s):
    s=packed.sink(s)
    s=replace(s,'static bool packet(struct nes_native_sink165 *s,unsigned op,unsigned section,unsigned at,const uint8_t *data,unsigned n){',
        'static bool packet_wire(struct nes_native_sink165 *s,unsigned op,unsigned section,unsigned at,const uint8_t *data,unsigned n,unsigned expanded){')
    s=replace(s,' b[0]=(uint8_t)op;', ''' if(op==5 && (!data||n!=2||expanded<242||expanded>4096||(expanded&1)))return fail(s,1);
 if(op!=5 && expanded)return fail(s,1);
 b[0]=(uint8_t)op;''')
    s=replace(s,'put16(b+8,s->generation);put16(b+10,at);',
                   'put16(b+8,s->generation);put16(b+10,at);put16(b+14,expanded);')
    s=replace(s,'bool nes_sink165_begin(', '''static bool packet(struct nes_native_sink165 *s,unsigned op,unsigned section,unsigned at,const uint8_t *data,unsigned n){
 return packet_wire(s,op,section,at,data,n,0);
}
'''+SPAN+'\nbool nes_sink165_begin(')
    s=replace(s,'if(!packet(s,2,kind,slot*(kind?32u:16u),b,n))',
                   'if(!span(s,kind,slot*(kind?32u:16u),b,n))')
    s=replace(s,''' for(unsigned k=2;k<6;k++)for(unsigned at=0;at<size[k];at+=240){
  unsigned n=size[k]-at;if(n>240)n=240;
  if(!packet(s,2,k,at,data[k-2]+at,n))return false;
 }''', ''' for(unsigned k=2;k<6;k++)if(!span(s,k,0,data[k-2],size[k]))return false;''')
    s=replace(s,'while(offset<1121){unsigned n=1121-offset;if(n>240)n=240;if(!packet(s,2,5,offset,zero,n))return false;offset+=n;}', '''while(offset<1121){
   unsigned n=1121-offset;
   if(n>240){n&=~1u;if(!packet_wire(s,5,5,offset,zero,2,n))return false;}
   else if(!packet(s,2,5,offset,zero,n))return false;
   offset+=n;
  }''')
    s=replace(s,'''  for(unsigned part=0;part<4;part++)for(unsigned at=0;at<lengths[part];at+=240){
   unsigned n=lengths[part]-at;if(n>240)n=240;
   if(!packet(s,2,5,offset,parts[part]+at,n))return false;
   offset+=n;
  }''', '''  for(unsigned part=0;part<4;part++){
   if(!span(s,5,offset,parts[part],lengths[part]))return false;
   offset+=lengths[part];
  }''')
    return replace(s,'put16(descriptor+20,0x1814)','put16(descriptor+20,0x1815)')


def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    (out/'nes_native_sink165.c').write_text(sink((ROOT/'src/nes/firmware/nes_native_sink181.c').read_text()),encoding='utf8',newline='\n')
    return build(out/'client')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().out),indent=2))
