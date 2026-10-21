# SPDX-License-Identifier: MIT
"""Incremental native tile dispatch with an immutable, checked early H2."""
from nes_native289 import prepare as previous
from nes_delta231 import once


def prepare(d):
    previous(d)
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'!r->open||!r->prepared||s->state','!r->open||s->state')
    s=once(s,'static unsigned staged289;', 'static unsigned staged289;\nstatic unsigned at290,used290,kind290,first290;')
    s=s.replace('staged289=0;}','staged289=0;at290=used290=kind290=first290=0;}')
    s=once(s,'sink289.state!=NES_SINK165_IDLE||!p->valid','sink289.state!=NES_SINK165_BUILD||!p->valid')
    a=s.index('unsigned produce289(void){');body=s[a:]
    body=once(body,'unsigned produce289(void){\n if(!nes_sink212_begin(&sink289,&resident285))return 0;\n unsigned at=0,used=0,kind=0,first=0;', '''unsigned begin_native290(void){
 if(input285.state!=NES_NATIVE165_COMMITTED||resident285.fault||dirty285.fault||!dirty285.open||staged289)return 0;
 at290=used290=kind290=first290=0;return nes_sink212_begin(&sink289,&resident285);
}
unsigned tiles290(unsigned final){
 if(input285.state!=NES_NATIVE165_COMMITTED||sink289.state!=NES_SINK165_BUILD||resident285.fault||dirty285.fault||staged289||at290>output_size285)return 0;
 unsigned at=at290,used=used290,kind=kind290,first=first290;''')
    body=once(body,' if(used&&!bulk289(kind,first,used))return 0;', ''' at290=at;used290=used;kind290=kind;first290=first;
 if(!final)return 1;
 if(!resident285.prepared||!dirty285.prepared||!video285.valid)return 0;
 if(used&&!bulk289(kind,first,used))return 0;used290=0;''')
    s=s[:a]+body;p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned h2(', 'extern uint8_t certificate286[32];\nstatic unsigned started290;\nstatic unsigned h2(')
    s=once(s,'return send(48);','if(started290){for(unsigned i=0;i<32;i++)if(c[i]!=certificate286[i])return fail(19);return 1;}return send(48);')
    s=once(s,'extern unsigned prepare289(void),produce289(void);','extern unsigned prepare289(void),begin_native290(void),tiles290(unsigned);')
    a=s.index('static unsigned frame_core284(');b=s.index('void reset259(',a)
    s=s[:a]+'''unsigned start290(uint32_t serial,unsigned generation){
 if(started290||!serial||serial==0xffffffffu||serial<=state259.serial)return fail(11);
 const uint8_t *c=certificate286;
 if(u32(c+8)!=serial||u16(c+12)!=generation||c[3]!=((serial-1)&1))return fail(13);
 if(!drain())return 0;
 state259.serial=serial;state259.generation=generation;state259.bank=(serial-1)&1;state259.sequence=0;state259.token=0;
 begin=seal=requirements264=0;
 for(unsigned i=1;i<=48;i++)wire259[i]=0;
 wire259[1]=13;wire259[2]=5;w16(wire259+13,32);
 for(unsigned i=0;i<32;i++)wire259[17+i]=c[i];
 scroll274=u16(c+14);raw274=c[20];
 if(!send(48)||!begin_native290())return fail(18);
 started290=1;return 1;
}
static unsigned frame_core284(const uint8_t *plan,unsigned bytes,uint32_t serial,unsigned generation){
 (void)plan;(void)bytes;
 if(!started290||serial!=state259.serial||generation!=state259.generation)return fail(11);
 if(!prepare289()||u32(seal289+4)!=serial||u16(seal289+8)!=generation)return fail(13);
 if(!h2(seal289)||!tiles290(1)||!begin||!seal)return fail(18);
 started290=0;trace259(1,serial);return 1;
}
'''+s[b:]
    s=once(s,'void reset259(void){','void reset259(void){started290=0;')
    p.write_text(s,encoding='utf-8',newline='\n')
