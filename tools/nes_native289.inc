/* SPDX-License-Identifier: MIT
 * Native output is produced from committed planner state, not packet fixtures.
 * The caller finishes the checked EA/display retirement before commit285.
 */
extern struct nes_native_video165 video285;
extern struct nes_native165 input285;
extern struct nes_resident211 resident285;
extern struct nes_dirty231 dirty285;
extern uint8_t output285[];
extern unsigned output_size285;
static struct nes_native_sink165 sink289;
uint8_t seal289[206];
static unsigned staged289;
unsigned commit_ready289(void){return staged289&&sink289.state==NES_SINK165_BUILD&&resident285.open&&resident285.prepared&&!resident285.fault&&dirty285.open&&dirty285.prepared&&!dirty285.fault;}
void reset289(void){memset(&sink289,0,sizeof sink289);memset(mapstale247,255,sizeof mapstale247);staged289=0;}
void abort289(void){sink289.state=NES_SINK165_FAULT;memset(mapstale247,255,sizeof mapstale247);staged289=0;}
unsigned commit289(void){
 if(!staged289||sink289.state!=NES_SINK165_BUILD||resident285.open||dirty285.open||resident285.fault||dirty285.fault)return 0;
 memset(mapstale247[resident285.target],0,256);sink289.last_generation=sink289.generation;
 sink289.displayed=true;sink289.state=NES_SINK165_IDLE;staged289=0;return 1;
}
unsigned prepare289(void){
 const struct nes_native_video165 *p=&video285;const struct nes_resident211 *r=&resident285;const struct nes_dirty231 *d=&dirty285;
 if(staged289||sink289.state!=NES_SINK165_IDLE||!p->valid||!r->open||!r->prepared||r->fault||!d->open||!d->prepared||d->fault||input285.state!=NES_NATIVE165_COMMITTED||p->generation!=r->generation||d->generation!=r->generation||d->serial!=r->serial||d->target!=r->target)return 0;
 memset(seal289,0,sizeof seal289);seal289[0]=3;
 for(unsigned i=0;i<4;i++)seal289[4+i]=(uint8_t)(r->serial>>(i*8));
 put16(seal289+8,r->generation);put16(seal289+12,190);
 uint8_t *x=seal289+16;
 unsigned sizes[6]={p->bg_count*16u,p->obj_count*32u,4096,512,544,p->patch_count?3418u:p->hdma_size};
 for(unsigned i=0;i<6;i++)put16(x+i*2,sizes[i]);
 put16(x+12,p->hofs[0]);put16(x+14,p->vofs[0]);put16(x+16,4192);put16(x+18,p->display_mask);put16(x+20,0x2472);put16(x+22,p->patch_count);
 memcpy(x+24,r->used,144);memcpy(x+168,d->stale[d->target]+32,22);return 1;
}
static bool bulk289(unsigned kind,unsigned slot,unsigned count){
 static const uint8_t token[4]={0};
 return packet_wire(&sink289,7,kind,slot*(kind?32u:16u),token,4,count);
}
unsigned produce289(void){
 if(!nes_sink212_begin(&sink289,&resident285))return 0;
 unsigned at=0,used=0,kind=0,first=0;
 /* Match the actual tile producer's contiguous aperture ownership across
  * encoded E9 batches. No converted tile buffer or metadata copy is needed. */
 while(at<output_size285){
  if(output_size285-at<3)return 0;
  unsigned size=output285[at]|(unsigned)output285[at+1]<<8,count=output285[at+2];at+=3;
  if(!count||count>15||size>240||size>output_size285-at)return 0;
  unsigned end=at+size;
  while(count--){
   if(at>=end)return 0;const uint8_t *p=output285+at;unsigned k=p[0]&3,n;
   if(k==3||((p[0]&128)?p[0]>130:p[0]>2))return 0;
   if(end-at<((p[0]&128)?3u:16u))return 0;
   if(p[0]&128)n=k==0?7:k==1?8:3;
   else{n=16;for(unsigned mask=p[1];mask;mask>>=1)n+=(mask&1)*2;}
   if(n>end-at)return 0;
   unsigned genpos=(p[0]&128)?1:2;
   if((p[genpos]|(unsigned)p[genpos+1]<<8)!=resident285.generation)return 0;
   unsigned pos=(p[0]&128)?3:4,slot=k==2?0:p[pos]|(unsigned)p[pos+1]<<8;
   unsigned nextkind=k==1,unit=nextkind?32:16;
   if(slot>=(nextkind?128u:1024u))return 0;
   if(used&&(kind!=nextkind||slot!=first+used/unit||used+unit>2048)){
    if(!bulk289(kind,first,used))return 0;used=0;
   }
   if(!used){kind=nextkind;first=slot;}used+=unit;at+=n;
  }
  if(at!=end)return 0;
 }
 if(used&&!bulk289(kind,first,used))return 0;
 if(!nes_sink231_seal(&sink289,&video285,&resident285,&dirty285))return 0;
 staged289=1;return 1;
}
