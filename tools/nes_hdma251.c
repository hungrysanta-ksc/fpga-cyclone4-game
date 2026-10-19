/* SPDX-License-Identifier: MIT */
/* Experimental pre-seal planner check; transport binding is NOT implemented.
 * Uses the existing candidate, with no persistent allocation or frame copy. */
#include "nes_native_video165.h"
static unsigned word(const uint8_t *p) {return p[0]|((unsigned)p[1]<<8);}
bool nes_hdma251_validate(const struct nes_native_video165 *p) {
 unsigned i,total=0,raw=0;
 if(p->display_mask!=0x18&&p->display_mask!=0x1e)return false;
 if(p->patch_count>7||!p->hdma_size||p->hdma_size>1121)return false;
 for(i=0;i<1121;i+=5){
  unsigned n=p->hdma[i];
  if(!n)break;
  if(n>=128)return false;
  total+=n;
 }
 if(i>=1121||total!=224||i+1!=p->hdma_size)return false;
 if(!p->patch_count)return true;
 total=0;
 for(i=0;i<81;i+=5){
  const uint8_t *a=p->patch.mode[0]+i,*b=p->patch.mode[1]+i,*e=p->patch.enable+i;
  unsigned n=a[0],mode,map,enable,window;
  if(!n)break;
  if(i+4>=81||n>=128||b[0]!=n||e[0]!=n)return false;
  total+=n;if(total>224)return false;
  mode=word(a+1);
  if(mode==3){raw+=n;map=0x38;enable=1;window=0;}
  else if(mode==0){map=0x31;enable=17;window=p->display_mask==0x18?17:0;}
  else return false;
  if(word(b+1)!=mode||word(a+3)!=map||word(b+3)!=map+0x20||word(e+1)!=enable||word(e+3)!=window)return false;
 }
 if(i>=81||total!=224||raw!=p->patch_count||p->patch.mode[1][i]||p->patch.enable[i])return false;
 return p->patch.size[0]==i+1&&p->patch.size[1]==i+1&&p->patch.size[2]==i+1;
}
