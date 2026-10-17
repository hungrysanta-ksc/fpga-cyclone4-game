/* SPDX-License-Identifier: MIT */
#include "nes_budget210.h"
#include <stdio.h>
#include <string.h>
struct nes_budget210 nes_budget210;
void nes_budget210_reset(void){memset(&nes_budget210,0,sizeof nes_budget210);}
void nes_budget210_attach(struct nes_budget210_cache *cache){
 if(cache)memset(cache,0,sizeof *cache);
 nes_budget210.cache=cache;
}
void nes_budget210_detach(void){nes_budget210.cache=NULL;}
void nes_budget210_frame(uint32_t elapsed){
 struct nes_budget210 *s=&nes_budget210;if(s->open)return;
 if(++s->serial==0){if(s->cache)memset(s->cache->seen,0,sizeof s->cache->seen);s->serial=1;}
 s->frame_start=elapsed;s->bin=(uint8_t)(elapsed/500<12?elapsed/500:11);s->open=true;
}
void nes_budget210_wire(unsigned op,unsigned n,bool ok){
 unsigned f=op>=0xd0&&op<=0xd3?B210_INGRESS:op==0xe8?B210_E8:op==0xe9?B210_E9:
  op==0xe0?B210_E0:op==0xe1?B210_E1:B210_OTHER;
 nes_budget210.bins[nes_budget210.bin][f]+=n;
 if(!ok)nes_budget210.failed_transfers++;
}
void nes_budget210_time(unsigned phase,uint32_t ticks){
 if(phase>=B210_RECEIVE&&phase<=B210_SEAL)nes_budget210.bins[nes_budget210.bin][phase]+=ticks;
}
void nes_budget210_plan(const struct nes_plan191 *q){
 struct nes_budget210 *s=&nes_budget210;uint32_t *b=s->bins[s->bin];
 unsigned bytes=q->kind==1?32:16;b[B210_PLANS]++;b[B210_OUTPUT]+=bytes;
 bool ordinary=q->kind<=2,identity=true;
 for(unsigned i=0;i<8;i++)if(q->alt[i]!=65535)ordinary=false;
 for(unsigned i=0;i<16;i++)if(q->row[i]!=i/2)identity=false;
 uint64_t key=((uint64_t)q->kind<<61)|q->tag;
 if(q->kind==0){
  if(q->mask!=255)ordinary=false;
  for(unsigned i=0;i<16;i++){if(q->row[i]>7)ordinary=false;key|=(uint64_t)q->row[i]<<(13+i*3);}
 }else if(q->kind==1){if(!identity)ordinary=false;key|=(uint64_t)q->mask<<13;}
 else if(q->kind==2)key=UINT64_C(2)<<61;
 if(!ordinary||!s->cache){b[B210_COMPLEX]+=bytes;return;}
 /* Hash collisions replace, never count as equality. Same-frame revisits
  * are not cross-frame reuse. Generation wraps do not affect serial stamps. */
 uint32_t h=(uint32_t)key^(uint32_t)(key>>32);h^=h>>16;h*=0x7feb352du;h^=h>>15;
 unsigned at=h&255;
 if(s->cache->seen[at]&&s->cache->seen[at]!=s->serial&&s->cache->keys[at]==key){
  b[B210_REUSE]+=bytes;b[B210_REUSE_PLAN]+=q->kind==2?3:q->kind==1?8:identity?7:16;
 }
 s->cache->keys[at]=key;s->cache->seen[at]=s->serial;
}
void nes_budget210_display(uint32_t elapsed,const struct nes_native_video165 *v){
 struct nes_budget210 *s=&nes_budget210;uint32_t *b=s->bins[s->bin];
 uint32_t gap=elapsed-s->last_display;if(gap>b[B210_MAX_GAP])b[B210_MAX_GAP]=gap;
 b[B210_FRAMES]++;b[B210_BG]+=v->bg_count;b[B210_OBJ]+=v->obj_count;
 uint64_t mask=v->map_dirty;while(mask){b[B210_MAP_DIRTY]++;mask&=mask-1;}
 s->last_display=elapsed;s->open=false;
}
int nes_budget210_format(char *text,unsigned size){
 int n=snprintf(text,size,"budget_schema=210\ntick_ms=10\nbin_ticks=500\nbin_basis=FRAME_START_NOT_SCENE\nmodel=ROM_SESSION_EXACT256_DIRECT_NO_SLOT_PROOF\nsource_reads_snes_vblank=UNMEASURED\nfailed_transfers=%lu\nopen=%u\ncolumns=frames,recv,plan,seal,maxgap,ingress,e8,e9,e0,e1,other,plans,out,reuse,reuseplan,complex,bg,obj,mapdirty\nvalues=HEX32\n",
  (unsigned long)nes_budget210.failed_transfers,nes_budget210.open?1u:0u);
 if(n<0||(unsigned)n>=size)return -1;
 for(unsigned i=0;i<12;i++){
  int used=snprintf(text+n,size-(unsigned)n,"b%02u=",i);if(used<0||(unsigned)used>=size-(unsigned)n)return -1;n+=used;
  for(unsigned f=0;f<B210_FIELDS;f++){
   used=snprintf(text+n,size-(unsigned)n,"%08lx%c",(unsigned long)nes_budget210.bins[i][f],f+1==B210_FIELDS?'\n':',');
   if(used<0||(unsigned)used>=size-(unsigned)n)return -1;
   n+=used;
  }
 }
 return n;
}
