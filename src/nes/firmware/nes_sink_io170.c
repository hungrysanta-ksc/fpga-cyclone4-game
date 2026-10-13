/* SPDX-License-Identifier: MIT */
#include "nes_sink_io170.h"
#include <string.h>
struct nes_sink_io170 nes_sink_io170;
_Static_assert(sizeof(struct nes_sink_io170)==20,"bounded first-failure transport trace");
bool nes_sink_io170_fail(unsigned reason,uint32_t polls,const uint8_t *rx){
 if(!nes_sink_io170.reason){
  nes_sink_io170.polls=polls;
  if(rx)memcpy(nes_sink_io170.status,rx+1,15);
  else memset(nes_sink_io170.status,0,15);
  nes_sink_io170.reason=(uint8_t)(reason|(rx?128:0));
 }
 return false;
}
int nes_sink_io170_format(char *text,unsigned capacity){
 static const char hex[]="0123456789abcdef",prefix[]="sink_io170=";
 const unsigned length=sizeof(prefix)-1+2+1+8+1+30+1;
 if(!text||capacity<=length)return -1;
 char *p=text;memcpy(p,prefix,sizeof(prefix)-1);p+=sizeof(prefix)-1;
 *p++=hex[nes_sink_io170.reason>>4];*p++=hex[nes_sink_io170.reason&15];*p++='/';
 for(unsigned i=0;i<8;i++)*p++=hex[(nes_sink_io170.polls>>(28-4*i))&15];
 *p++='/';
 for(unsigned i=0;i<15;i++){*p++=hex[nes_sink_io170.status[i]>>4];*p++=hex[nes_sink_io170.status[i]&15];}
 *p++='\n';*p=0;return (int)(p-text);
}
