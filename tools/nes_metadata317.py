# SPDX-License-Identifier: MIT
"""Bounded immutable preparation and credit-checked requirements issue."""
import os
from nes_delta231 import once
from nes_slots312 import native as previous
import nes_prepare309 as prep

def native(d):
    previous(d)
    # Reuse the tested 40/16-byte preparation slices on the current ABI.
    prior=prep.previous;flag=os.environ.get('NES309_PREP')
    try:
        prep.previous=lambda d:None;os.environ['NES309_PREP']='1';prep.native(d)
    finally:
        prep.previous=prior
        if flag is None:os.environ.pop('NES309_PREP',None)
        else:os.environ['NES309_PREP']=flag
    p=d/'nes_native289.c';s=p.read_text()
    s+='''
unsigned metadata_ready317(void){
 return prepared309==207&&!staged289&&video285.valid&&resident285.prepared&&dirty285.prepared&&
 !resident285.fault&&!dirty285.fault&&resident285.open&&dirty285.open&&
 input285.state==NES_NATIVE165_COMMITTED&&resident285.serial==dirty285.serial&&
 resident285.generation==dirty285.generation&&resident285.target==dirty285.target&&
 (sink289.state==NES_SINK165_BUILD||sink289.state==NES_SINK165_BUSY);
}
''';p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    a=s.index('static unsigned send(unsigned n){');b=s.index('/* The ABI remains259',a)
    send=s[a:b].replace('static unsigned send(unsigned n){','static unsigned send317(unsigned n,uint8_t *wire317,unsigned direct317){').replace('wire259','wire317')
    send=once(send,'if(!io259(wire317,n+3))return fail(1);', '''if(direct317){
  extern int physical267(uint8_t *,unsigned);extern unsigned wait_armed284;
  if(!physical267(wire317,n+3)||!progress282(wire317,n+3))return fail(1);
  wait_armed284=0;
 }else if(!io259(wire317,n+3))return fail(1);''')
    s=s[:a]+send+'static unsigned send(unsigned n){return send317(n,wire259,0);}\n'+s[b:]
    # The encoded request gets its own lifetime; never clobber the pending DMA.
    a=s.index('   for(unsigned i=0;i<206;i++)wire259[i+1]=seal262[i];')
    b=s.index('requirements264=1;',a)+len('requirements264=1;')
    encode=s[a:b].replace('wire259','metadata317').replace('seal262','seal289').replace('send(encoded307)','send317(encoded307,metadata317,1)')
    block='''
extern unsigned metadata_ready317(void);
static uint8_t metadata317[209];
__attribute__((noinline)) unsigned issue_metadata317(void){
 extern uint8_t seal289[206];
 if(requirements264||!begin||seal||state259.error||!metadata_ready317())return !state259.error;
 if((uint16_t)(state259.sent-state259.retired)>=2)return 1;
'''+encode+'''
 return 1;
}
'''
    # Place after the existing begin/seal/requirements state declarations.
    pos=s.index('unsigned start290(')
    s=s[:pos]+block+s[pos:]
    s=once(s,'  if(requirements264&&p[0]!=10&&p[0]!=11)return fail(20);','  /* Requirements publication does not retire or forbid later DMA. */')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'extern unsigned prepare_slice309(void),preparation_pending309(void);',
        'extern unsigned prepare_slice309(void),preparation_pending309(void),issue_metadata317(void);')
    s=once(s,' }return 1;\n}\nstatic int poll267', '''  if(work_pending302()&&!pending302()&&!supply303()&&!progress302()){
   if(!issue_metadata317()){plan_error267=7;return 0;}
  }
 }return 1;
}
static int poll267''')
    p.write_text(s,newline='\n')
