/* SPDX-License-Identifier: MIT
 * Candidate canonical N5 -> planner adapter. The history remains speculative
 * until both checksums and input commit succeed. No early output lease here.
 */
#include "nes_decode280.c"
uint8_t history286[4910],certificate286[32];
unsigned expansion_error286;
extern bool geometry286(const struct nes_native165 *,const uint16_t *,struct nes_native_video165 *,struct nes_resident211 *,struct nes_dirty231 *);
extern bool start286(void);
extern unsigned step286(void),context_size286(void);
extern void cancel286(void);
static unsigned bad286(unsigned n){expansion_error286=n;input285.state=NES_NATIVE165_FAILED;return 0;}
static void need286(unsigned tag,unsigned kind){input285.required[tag/4]|=(uint8_t)(kind<<((tag%4)*2));}
unsigned block286(const uint8_t *p,unsigned n,unsigned check){return block280(history286,p,n,check);}
unsigned geometry_ready286(void){return receiver280.phase==2||receiver280.valid;}
unsigned expand286(void){
 struct nes_native165 *s=&input285;const uint8_t *p=history286;
 if(!geometry_ready286())return bad286(1);
 /* This adapter owns the planner view. Every planner-visible array below
  * is written completely; packet receiver bookkeeping is not its lifetime. */
 s->state=NES_NATIVE165_FAILED;expansion_error286=0;s->generation=receiver280.generation;
 for(unsigned i=0;i<6;i++)s->counts[i]=u16(p+4385+i*2);
 if(!s->counts[0]||s->counts[0]>1056||s->counts[0]%33||s->counts[1]!=224||s->counts[2]>128||s->counts[3]>128||s->counts[4]!=224||(s->counts[5]!=32&&s->counts[5]!=64)||p[4397]>2)return bad286(2);
 s->patch_count=p[4397];
 memcpy(s->maps,p,2112);memcpy(s->rows,p+2112,224);memcpy(s->objects,p+2336,1024);memcpy(s->exceptions,p+3360,512);memcpy(s->palette,p+4321,64);
 memset(s->required,0,sizeof s->required);
 for(unsigned i=0;i<s->counts[0];i++){if(s->maps[i]&0x8000)return bad286(3);need286(s->maps[i]&8191,1);}
 for(unsigned i=0;i<s->counts[2];i++){if(s->objects[i]>>49)return bad286(4);need286((unsigned)s->objects[i]&8191,2);}
 for(unsigned i=0;i<s->counts[3];i++)need286(s->exceptions[i]>>19,1);
 unsigned raw=0,palettes=s->counts[5]/32,mask=p[4320];
 if(mask!=0x18&&mask!=0x1e)return bad286(5);
 for(unsigned y=0;y<224;y++){
  unsigned v=u16(p+3872+y*2);
  if(v&0xc000)return bad286(6);
  if(v&1024){
   if((v&1023)||((v>>11)&7)!=raw||raw>=s->patch_count)return bad286(7);
   s->raster[y]=(UINT64_C(1)<<49)|((uint64_t)raw++<<50);
  }else{
   if((v&0x3800)||((v>>9)&1)>=palettes)return bad286(8);
   s->raster[y]=(v&31)|((uint64_t)(v&32)<<5)|((uint64_t)((v>>6)&7)<<30)|((uint64_t)mask<<36)|((uint64_t)((v>>9)&1)<<44);
  }
 }
 if(raw!=s->patch_count)return bad286(9);
 s->ntiles=0;
 for(unsigned byte=0;byte<2048;byte++){
  unsigned bits=s->required[byte];if(!bits)continue;
  for(unsigned lane=0;lane<4;lane++){
   unsigned kind=(bits>>(lane*2))&3;
   if(kind){if(s->ntiles==512)return bad286(10);s->tiles[s->ntiles].tag=(uint16_t)(byte*4+lane);s->tiles[s->ntiles++].kind=(uint8_t)kind;}
  }
 }
 s->state=NES_NATIVE165_PREPARED;return 1;
}
unsigned geometry_plan286(void){return geometry286(&input285,palette285,&video285,&resident285,&dirty285);}
unsigned input_commit286(void){
 if(!receiver280.valid||receiver280.phase||input285.state!=NES_NATIVE165_PREPARED||input285.generation!=receiver280.generation)return bad286(11);
 memcpy(input285.raw_pixels,history286+4398,input285.patch_count*256u);
 input285.state=NES_NATIVE165_COMMITTED;return 1;
}
static void put286(uint8_t *p,unsigned v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void long286(uint8_t *p,uint32_t v){put286(p,v);put286(p+2,v>>16);}
unsigned h2early286(void){
 if(input285.state!=NES_NATIVE165_PREPARED)return 0;
 uint8_t tables[249]={0};unsigned offset=0,raw=input285.patch_count,mask=video285.display_mask;
 if(raw){
  for(unsigned y=0;y<224;){
   unsigned r=(input285.raster[y]>>49)&1,n=y+1;
   while(n<224&&n-y<127&&((input285.raster[n]>>49)&1)==r)n++;
   if(offset+6>81)return 0;
   for(unsigned b=0;b<2;b++){uint8_t *t=tables+b*81+offset;t[0]=(uint8_t)(n-y);t[1]=r?3:0;t[3]=(uint8_t)((r?0x38:0x31)+b*0x20);}
   uint8_t *t=tables+162+offset;t[0]=(uint8_t)(n-y);t[1]=r?1:17;t[3]=!r&&mask==0x18?17:0;
   offset+=5;y=n;
  }
  for(unsigned i=0;i<3;i++)tables[243+i*2]=(uint8_t)(offset+1);
 }
 uint8_t *c=certificate286;memset(c,0,32);c[0]='H';c[1]='2';c[2]=2;c[3]=resident285.target;
 long286(c+4,resident285.epoch);long286(c+8,resident285.serial);put286(c+12,input285.generation);put286(c+14,video285.hdma_size);
 c[19]=(uint8_t)mask;c[20]=(uint8_t)raw;unsigned digest=65535;
 for(unsigned i=0;i<video285.hdma_size;i++)digest=crc(digest,video285.hdma[i]);
 if(raw){for(unsigned i=0;i<3;i++)c[16+i]=(uint8_t)(offset+1);unsigned block=65535;
  for(unsigned i=0;i<249;i++){block=crc(block,tables[i]);if(i%16==15||i==248){digest=crc(digest,block&255);digest=crc(digest,block>>8);block=65535;}}
 }
 put286(c+22,digest);put286(c+24,video285.hdma_size+(raw?249:0));long286(c+26,resident285.serial>2?resident285.serial-2:0);
 unsigned check=65535;for(unsigned i=0;i<30;i++)check=crc(check,c[i]);put286(c+30,check);return 1;
}
unsigned begin_step286(void){return start286();}
unsigned next_step286(void){unsigned result=step286();if(!result)cancel286();if(result==2&&!flush285())return 0;return result;}
void stop286(void){cancel286();reset280();nes_resident211_abort(&resident285);nes_dirty231_abort(&dirty285);input285.state=NES_NATIVE165_FAILED;}
