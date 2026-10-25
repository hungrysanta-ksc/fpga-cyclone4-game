# SPDX-License-Identifier: MIT
"""Bounded seal preparation in an otherwise blocked foreground wait."""
import os
from nes_ingress307 import native as previous
from nes_delta231 import once

def native(d):
    previous(d)
    if os.environ.get('NES309_PREP')!='1':return
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'static unsigned staged289;','static unsigned staged289;\nstatic unsigned prepared309;')
    s=s.replace('staged289=0;', 'staged289=0;prepared309=0;')
    s=once(s,'unsigned begin_native290(void){','unsigned begin_native290(void){\n prepared309=0;')
    s=once(s,'unsigned prepare289(void){','__attribute__((noinline)) unsigned prepare_slice309(void){')
    s=once(s,'if(staged289||sink289.state!=NES_SINK165_BUILD||!p->valid',
        'if(staged289||(sink289.state!=NES_SINK165_BUILD&&sink289.state!=NES_SINK165_BUSY)||!p->valid')
    s=once(s,' memset(seal289,0,sizeof seal289);seal289[0]=3;', ''' if(prepared309==207)return 1;
 if(prepared309==0){
 memset(seal289,0,40);seal289[0]=3;''')
    s=once(s,' memcpy(x+24,r->used,144);memcpy(x+168,d->stale[d->target]+32,22);return 1;', ''' prepared309=1;return 1;
 }
 unsigned at=prepared309-1,end=at+16;if(end>166)end=166;
 for(;at<end;at++)seal289[40+at]=at<144?r->used[at]:d->stale[d->target][32+at-144];
 prepared309=end==166?207:end+1;return 1;''')
    pos=s.index('static bool bulk289(')
    s=s[:pos]+'''unsigned preparation_pending309(void){return prepared309!=207&&(sink289.state==NES_SINK165_BUILD||sink289.state==NES_SINK165_BUSY)&&video285.valid&&resident285.prepared&&dirty285.prepared;}
unsigned prepare289(void){
 if(sink289.state!=NES_SINK165_BUILD)return 0;
 do{if(!prepare_slice309())return 0;}while(preparation_pending309());return 1;
}
'''+s[pos:]
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'static int work302(void){','''extern unsigned prepare_slice309(void),preparation_pending309(void);
static int work302(void){''')
    s=once(s,' }return 1;\n}\nstatic int poll267', '''  /* No SPI recursion. Recheck DMA/credit, pending plan work and GPIO before
   * each bounded 40-byte header / 16-byte copy. Invalid preparation faults. */
  for(unsigned slices309=0;slices309<12&&work_pending302()&&!pending302()&&
      !supply303()&&preparation_pending309()&&!progress302();slices309++){
   if(!prepare_slice309()){plan_error267=6;return 0;}
  }
 }return 1;
}
static int poll267''')
    p.write_text(s,newline='\n')
