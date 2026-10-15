/* SPDX-License-Identifier: MIT */
/* Included in the paired sink translation unit, sharing packet_wire's full
 * token/status/signature validation and terminal fault policy. */
bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){
 if(s->state!=NES_SINK165_BUILD)return false;
 if(!d||d[0]!=1||d[1]>1)return fail(s,4);
 unsigned kind=d[1],length=d[2]|((unsigned)d[3]<<8);
 unsigned offset=d[4]|((unsigned)d[5]<<8),gen=d[6]|((unsigned)d[7]<<8);
 unsigned unit=kind?32u:16u,limit=kind?4096u:16384u;
 /* FFFFFFFF is exhausted, never a valid193 ownership token. Zero is legal. */
 if(gen!=s->generation||!length||length>2048||length%unit||offset%unit||
    offset>=limit||length>limit-offset||offset/unit!=(kind?s->obj_next:s->bg_next)||
    (d[8]==255&&d[9]==255&&d[10]==255&&d[11]==255))return fail(s,4);
 if(!packet_wire(s,7,kind,offset,d+8,4,length))return false;
 /* packet_wire deliberately keeps op7 off the async enqueue path. */
 if(kind)s->obj_next+=(uint16_t)(length/32);else s->bg_next+=(uint16_t)(length/16);
 return true;
}
