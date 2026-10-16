/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN_WIRE199_H
#define NES_PLAN_WIRE199_H
#include "nes_plan_wire196.h"
/* Lossless common-form encoding, NOT a cross-frame cache.
 * 80 BG: generationLE16,slotLE16,tagLE16 (7 bytes, identity rows).
 * 81 OBJ: same plus mask (8 bytes, identity rows).
 * 82 zero / 83 END: generationLE16 (3 bytes).
 * Non-identity rows or alternate tags retain the full196 form.
 * Full validation happens before shortening; CRC belongs to batch framing. */
static unsigned nes_plan199_encode(const struct nes_plan191 *q,uint8_t out[32]){
 uint16_t crc;unsigned n=nes_plan196_encode(q,out,&crc);
 if(!n)return 0;
 if(q->kind<2){
  for(unsigned i=0;i<16;i++)if(q->row[i]!=i/2)return n;
  for(unsigned i=0;i<8;i++)if(q->alt[i]!=UINT16_MAX)return n;
 }
 out[0]=(uint8_t)(0x80|q->kind);out[1]=(uint8_t)q->generation;out[2]=(uint8_t)(q->generation>>8);
 if(q->kind>=2)return 3;
 out[3]=(uint8_t)q->slot;out[4]=(uint8_t)(q->slot>>8);out[5]=(uint8_t)q->tag;out[6]=(uint8_t)(q->tag>>8);
 if(q->kind==1){out[7]=q->mask;return 8;}
 return 7;
}
#endif
