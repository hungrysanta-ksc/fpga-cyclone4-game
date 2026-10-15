/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN_WIRE196_H
#define NES_PLAN_WIRE196_H
#include "nes_plan191.h"
/* One immutable16..32 byte plan; no pixel bytes. Header: kind,alt_mask,
 * generationLE16,slotLE16,tagLE16,mask,rows48LE,version1. Alternate tags
 * follow in ascending row order, LE16. Kind3 is END with generation/version.
 * CRC16/CCITT-FALSE covers payload, separate from transport framing.
 * Return0 on invalid input; never silently truncate address/row fields. */
static unsigned nes_plan196_encode(const struct nes_plan191 *q,uint8_t out[32],uint16_t *crc){
 if(!q||!out||!crc||q->kind>3||q->slot>1023||q->tag>8191)return 0;
 uint8_t am=0;for(unsigned i=0;i<8;i++){
  if(q->alt[i]!=UINT16_MAX){if(q->alt[i]>8191)return 0;am|=(uint8_t)(1u<<i);}
 }
 for(unsigned i=0;i<16;i++)if(q->row[i]>7)return 0;
 if((q->kind==0&&(!q->slot||q->mask!=255))||
    (q->kind==1&&(q->slot>=128||!q->mask||am))||
    (q->kind>=2&&(q->slot||q->tag||q->mask||am)))return 0;
 if(q->kind>=2)for(unsigned i=0;i<16;i++)if(q->row[i])return 0;
 for(unsigned i=0;i<32;i++)out[i]=0;
 out[0]=q->kind;out[1]=am;out[2]=(uint8_t)q->generation;out[3]=(uint8_t)(q->generation>>8);
 out[4]=(uint8_t)q->slot;out[5]=(uint8_t)(q->slot>>8);out[6]=(uint8_t)q->tag;out[7]=(uint8_t)(q->tag>>8);out[8]=q->mask;out[15]=1;
 for(unsigned i=0;i<16;i++){
  unsigned bit=i*3;out[9+bit/8]|=(uint8_t)(q->row[i]<<(bit%8));
  if(bit%8>5)out[10+bit/8]|=(uint8_t)(q->row[i]>>(8-bit%8));
 }
 unsigned n=16;for(unsigned i=0;i<8;i++)if(am&(1u<<i)){out[n++]=(uint8_t)q->alt[i];out[n++]=(uint8_t)(q->alt[i]>>8);}
 uint16_t c=0xffff;for(unsigned i=0;i<n;i++){c^=(uint16_t)out[i]<<8;for(unsigned j=0;j<8;j++)c=(uint16_t)(c&0x8000?(c<<1)^0x1021:c<<1);}
 *crc=c;return n;
}
#endif
