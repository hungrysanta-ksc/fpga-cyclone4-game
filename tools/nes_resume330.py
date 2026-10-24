# SPDX-License-Identifier: MIT
"""Resumable tile decode; first map packet uses released manifest scratch."""
import os
from nes_joint327 import native as previous
from nes_delta231 import once


def native(d):
    previous(d)
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'static unsigned at290,used290,kind290,first290,bg_seen295;',
        'static unsigned at290,used290,kind290,first290,bg_seen295;\nstatic unsigned end330,left330;\nstatic void reset_map330(void);')
    s=s.replace('at290=used290=kind290=first290=bg_seen295=0;',
        'at290=used290=kind290=first290=bg_seen295=end330=left330=0;reset_map330();')
    a=s.index('unsigned tiles290(unsigned final){');b=s.index('\nunsigned metadata_ready317',a)
    s=s[:a]+'''unsigned tiles290(unsigned final){
 if(input285.state!=NES_NATIVE165_COMMITTED||sink289.state!=NES_SINK165_BUILD||resident285.fault||dirty285.fault||staged289||at290>output_size285)return 0;
 unsigned steps=0;
 while(at290<output_size285){
  if(!final&&steps==16)return 1;
  if(!left330){
   if(output_size285-at290<3)return 0;
   unsigned size=output285[at290]|(unsigned)output285[at290+1]<<8;
   unsigned count=output285[at290+2];
   if(!count||count>15||size>240||size>output_size285-at290-3)return 0;
   at290+=3;end330=at290+size;left330=count;
  }
  if(at290>=end330)return 0;
  const uint8_t *p=output285+at290;unsigned k=p[0]&3,n;
  if(p[0]==0x87){
   if(bg_seen295||left330!=1||end330-at290!=3||(p[1]|(unsigned)p[2]<<8)!=resident285.generation)return 0;
   if(used290&&!bulk289(kind290,first290,used290))return 0;
   used290=0;bg_seen295=1;n=3;
  }else{
   if(k==3||((p[0]&128)?p[0]>130:p[0]>2)||(bg_seen295?k!=1:k==1))return 0;
   if(end330-at290<((p[0]&128)?3u:16u))return 0;
   if(p[0]&128)n=k==0?7:k==1?8:3;
   else{n=16;for(unsigned mask=p[1];mask;mask>>=1)n+=(mask&1)*2;}
   if(n>end330-at290)return 0;
   unsigned genpos=(p[0]&128)?1:2;
   if((p[genpos]|(unsigned)p[genpos+1]<<8)!=resident285.generation)return 0;
   unsigned pos=(p[0]&128)?3:4,slot=k==2?0:p[pos]|(unsigned)p[pos+1]<<8;
   unsigned nextkind=k==1,unit=nextkind?32:16;
   if(slot>=(nextkind?128u:1024u))return 0;
   if(used290&&(kind290!=nextkind||slot!=first290+used290/unit||used290+unit>2048)){
    if(!bulk289(kind290,first290,used290))return 0;used290=0;
   }
   if(!used290){kind290=nextkind;first290=slot;}used290+=unit;
  }
  /* Commit only a checked record and successful preceding bulk submission.
   * An ambiguous SPI failure remains terminal; it is never retried. */
  at290+=n;left330--;steps++;
  if((left330==0)!=(at290==end330))return 0;
 }
 if(left330)return 0;
 if(!final)return 1;
 if(!bg_seen295||!resident285.prepared||!dirty285.prepared||!video285.valid)return 0;
 if(used290&&!bulk289(kind290,first290,used290))return 0;used290=0;
 if(!nes_sink231_seal(&sink289,&video285,&resident285,&dirty285))return 0;
 staged289=1;return 1;
}
''' +s[b:]
    if os.environ.get('NES330_MAP','1')=='0':
        s+='\nstatic void reset_map330(void){}\n'
        p.write_text(s,newline='\n');return
    s=once(s,'static bool map247(', 'static const uint8_t *take_map330(unsigned *,unsigned *);\nstatic bool map247(')
    s=once(s,' uint8_t b[240]={3};unsigned used=1,w=0;', ''' uint8_t b[240]={3};unsigned used=1,w=0,cached_size=0;
 const uint8_t *cached=take_map330(&w,&cached_size);
 if(cached&&cached_size>1&&!packet(s,9,2,0,cached,cached_size))return false;''')
    s=once(s,'  if(!(mapstale247[bank][w/8]&(1u<<(w%8)))){w++;continue;}',
        '  if(!(w&7)&&!mapstale247[bank][w/8]){w+=8;continue;}\n  if(!(mapstale247[bank][w/8]&(1u<<(w%8)))){w++;continue;}')
    s+='''
/* The209B metadata buffer is writable only after its successful E1 issue.
 * No second payload array; state adds20B, tile continuation adds8B. */
extern uint8_t *map_scratch330(void);
static unsigned map_w330,map_start330,map_n330,map_used330,map_state330;
static void reset_map330(void){map_w330=map_start330=map_n330=map_used330=map_state330=0;}
__attribute__((noinline)) unsigned prepare_map330(void){
 if(map_state330>=2||!metadata_ready317())return 1;
 uint8_t *b=map_scratch330();if(!b)return 1;
 if(!map_state330){b[0]=3;map_used330=1;map_state330=1;}
 const uint8_t *bits=mapstale247[resident285.target];
 for(unsigned step=0;step<16;step++){
  unsigned dirty=map_w330<2048&&(bits[map_w330/8]&(1u<<(map_w330&7)));
  if(map_n330&&(!dirty||map_n330==32)){
   unsigned size=3+2*map_n330;
   if(map_used330+size>208){map_w330=map_start330;map_state330=2;return 1;}
   put16(b+map_used330,map_start330*2);b[map_used330+2]=map_n330;
   memcpy(b+map_used330+3,video285.map+map_start330*2,map_n330*2);
   map_used330+=size;map_n330=0;
  }
  if(map_w330==2048){map_state330=2;return 1;}
  if(dirty){if(!map_n330)map_start330=map_w330;map_n330++;map_w330++;}
  else if(!(map_w330&7)&&!bits[map_w330/8])map_w330+=8;
  else map_w330++;
 }
 return 1;
}
static const uint8_t *take_map330(unsigned *next,unsigned *size){
 if(map_state330!=2||!metadata_ready317())return 0;
 uint8_t *b=map_scratch330();if(!b)return 0;
 *next=map_w330;*size=map_used330;map_state330=3;return b;
}
'''
    p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text();s+='''
uint8_t *map_scratch330(void){return map_issued327&&!seal&&!state259.error?metadata317:0;}
''';p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'static int work302(void){','extern unsigned prepare_map330(void);\nstatic int work302(void){')
    s=once(s,' }return 1;\n}\nstatic int poll267', '''  for(unsigned slices330=0;slices330<16&&work_pending302()&&!pending302()&&!supply303()&&!progress302();slices330++){
   if(!prepare_map330()){plan_error267=8;return 0;}
  }
 }return 1;
}
static int poll267''')
    p.write_text(s,newline='\n')
