# SPDX-License-Identifier: MIT
"""Bounded tentative raw-CHR hint producer; never changes source commit/display permission."""
from nes_raw352 import decoder as previous
from nes_delta231 import once

def decoder():
 s=previous()
 declarations=r'''
static uint32_t maps359;
static uint8_t rows359[28],exceptions359[16],attempted359;
uint8_t packet359[48];
static void changed359(unsigned at){
 if(at<2112)maps359|=UINT32_C(1)<<(at/66);
 else if(at<2336){unsigned y=at-2112;rows359[y/8]|=1u<<(y%8);}
 else if(at>=3360&&at<3872){unsigned i=(at-3360)/4;exceptions359[i/8]|=1u<<(i%8);}
 else if(at>=3872&&at<4320){unsigned y=(at-3872)/2;rows359[y/8]|=1u<<(y%8);}
}
static unsigned tags359;
static int tag359(unsigned tag){
 if(tag>=8192)return 0;
 for(unsigned i=0;i<tags359;i++)if(u16(packet359+12+2*i)==tag)return 1;
 if(tags359==17)return 0;
 packet359[12+2*tags359]=(uint8_t)tag;packet359[13+2*tags359]=(uint8_t)(tag>>8);tags359++;return 1;
}
unsigned prefetch359(const uint8_t *base,unsigned displayed_epoch,unsigned displayed_serial){
 State *s=&receiver280;
 if(attempted359||s->cold||s->phase!=1||s->last<59||displayed_epoch!=s->epoch||displayed_serial+1!=s->serial)return 0;
 attempted359=1;tags359=0;
 for(unsigned i=0;i<128;i++)if(exceptions359[i/8]&(1u<<(i%8))){
  unsigned e=u32(base+3360+i*4),y=((e>>6)&8191)/33;
  if(y<224){rows359[y/8]|=1u<<(y%8);if(!tag359(e>>19))return 0;}
 }
 uint32_t groups=maps359;
 for(unsigned y=0;y<224;y++)if(rows359[y/8]&(1u<<(y%8))){unsigned g=base[2112+y]>>3;if(g>=32)return 0;groups|=UINT32_C(1)<<g;}
 for(unsigned g=0;g<32;g++)if(groups&(UINT32_C(1)<<g))for(unsigned x=0;x<33;x++){
  unsigned cell=u16(base+g*66+x*2);if(cell&32768||!tag359(cell&8191))return 0;
 }
 if(!tags359)return 0;
 packet359[0]=0xea;packet359[1]=(uint8_t)tags359;
 packet359[2]=(uint8_t)s->generation;packet359[3]=(uint8_t)(s->generation>>8);
 for(unsigned i=0;i<4;i++){packet359[4+i]=(uint8_t)(s->epoch>>(8*i));packet359[8+i]=(uint8_t)(s->serial>>(8*i));}
 unsigned n=12+tags359*2;uint16_t c=65535;for(unsigned i=0;i<n;i++)c=crc(c,packet359[i]);packet359[n]=(uint8_t)c;packet359[n+1]=(uint8_t)(c>>8);return n+2;
}
'''
 s=once(s,'uint32_t source_groups352;', 'uint32_t source_groups352;\n'+declarations)
 s=once(s,'s->last=-1;s->phase=1;take=ci=20;', 'maps359=0;attempted359=0;for(unsigned i=0;i<28;i++)rows359[i]=0;for(unsigned i=0;i<16;i++)exceptions359[i]=0;\n   s->last=-1;s->phase=1;take=ci=20;')
 s=once(s,'if(p[1]==1){for', 'if(!s->cold)maps359|=UINT32_C(1)<<index;\n    if(p[1]==1){for')
 s=once(s,'base[at+i]=value;', 'if(!s->cold&&s->phase==1&&base[at+i]!=value)changed359(at+i);\n     base[at+i]=value;')
 return s
