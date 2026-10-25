# SPDX-License-Identifier: MIT
"""Read-only committed-bank deficit hints, never a new tile/display permission."""
from nes_raw352 import decoder as previous
from nes_delta231 import once
def decoder(batch_size=2):
 assert batch_size in (2,5)
 s=previous();s='#include "nes_resident211.h"\n'+s
 s=once(s,'uint32_t source_groups352;', '''uint32_t source_groups352;
uint8_t packet360[18];
static uint16_t cursor360,seen360[5];static uint8_t count360;
unsigned hint_done360;
''')
 s+='''
void hint_reset360(void){cursor360=0;count360=0;hint_done360=0;}
unsigned hint360(const struct nes_resident211 *r,unsigned epoch,unsigned prior_serial,unsigned immutable){
 State *s=&receiver280;
 if(!immutable||hint_done360||prior_serial<2||s->cold||(s->phase!=1&&s->phase!=2)||
    !r->displayed||r->open||r->prepared||r->fault||r->active>1||r->bg_slots>1024||
    r->epoch!=epoch||s->epoch!=epoch||r->serial!=prior_serial||prior_serial==UINT32_MAX||prior_serial+1!=s->serial)return 0;
 unsigned target=1-r->active,n=0,steps=0;
 while(cursor360<r->bg_slots&&steps<16&&n<2&&count360<5){
  unsigned i=cursor360++,tag=r->bg[i];steps++;
  if(tag>=8192||!(r->resident[r->active][i/8]&(1u<<(i%8)))||
     (r->resident[target][i/8]&(1u<<(i%8))))continue;
  unsigned j;for(j=0;j<count360;j++)if(seen360[j]==tag)break;
  if(j<count360)continue;
  seen360[count360++]=(uint16_t)tag;packet360[12+2*n]=(uint8_t)tag;packet360[13+2*n]=(uint8_t)(tag>>8);n++;
 }
 hint_done360=cursor360==r->bg_slots||count360==5;
 if(!n)return 0;
 packet360[0]=0xea;packet360[1]=(uint8_t)n;
 packet360[2]=(uint8_t)s->generation;packet360[3]=(uint8_t)(s->generation>>8);
 for(unsigned i=0;i<4;i++){packet360[4+i]=(uint8_t)(s->epoch>>(8*i));packet360[8+i]=(uint8_t)(s->serial>>(8*i));}
 unsigned len=12+2*n;uint16_t c=65535;for(unsigned i=0;i<len;i++)c=crc(c,packet360[i]);packet360[len]=(uint8_t)c;packet360[len+1]=(uint8_t)(c>>8);return len+2;
}
'''
 return s.replace('packet360[18]',f'packet360[{14+2*batch_size}]').replace('&&n<2&&',f'&&n<{batch_size}&&')
