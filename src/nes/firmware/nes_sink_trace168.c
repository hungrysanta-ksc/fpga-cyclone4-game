/* SPDX-License-Identifier: MIT */
#include "nes_sink_trace168.h"
#include <string.h>
struct nes_sink_trace168 nes_sink_trace168;
_Static_assert(sizeof(struct nes_sink_trace168)==32,"bounded trace");
uint8_t nes_sink168_mismatch(const uint8_t b[16],const uint8_t a[12]){
 return (uint8_t)((a[0]!=(b[0]==3?1:0)?1:0)|(a[1]!=b[0]?2:0)|
  (memcmp(a+2,b+2,2)?4:0)|(memcmp(a+4,b+4,4)?8:0)|
  (memcmp(a+8,b+8,2)?16:0)|(a[10]!=0x65||a[11]!=0x9a?32:0));
}
void nes_sink168_capture(const uint8_t b[16],const uint8_t a[12],bool valid,uint8_t mismatch){
 if(nes_sink_trace168.valid)return;
 memcpy(nes_sink_trace168.request,b,16);
 if(valid)memcpy(nes_sink_trace168.ack,a,12);
 else memset(nes_sink_trace168.ack,0,12);
 nes_sink_trace168.ack_valid=valid;nes_sink_trace168.mismatch=mismatch;
 nes_sink_trace168.valid=1;
}
int nes_sink168_format(char *text,unsigned capacity){
 static const char hex[]="0123456789abcdef";
 static const char header[]="sink_trace_valid=0\nsink_trace_ack_valid=0\nsink_trace_mismatch_hex=00\nsink_trace_request_hex=";
 static const char middle[]="\nsink_trace_ack_hex=";
 const unsigned size=sizeof(header)-1+32+sizeof(middle)-1+24+1;
 if(!text||capacity<=size)return -1;
 char *p=text;memcpy(p,header,sizeof(header)-1);p+=sizeof(header)-1;
 text[sizeof("sink_trace_valid=")-1]=(char)('0'+nes_sink_trace168.valid);
 text[sizeof("sink_trace_valid=0\nsink_trace_ack_valid=")-1]=(char)('0'+nes_sink_trace168.ack_valid);
 unsigned at=sizeof("sink_trace_valid=0\nsink_trace_ack_valid=0\nsink_trace_mismatch_hex=")-1;
 text[at]=hex[nes_sink_trace168.mismatch>>4];text[at+1]=hex[nes_sink_trace168.mismatch&15];
 for(unsigned i=0;i<16;i++){*p++=hex[nes_sink_trace168.request[i]>>4];*p++=hex[nes_sink_trace168.request[i]&15];}
 memcpy(p,middle,sizeof(middle)-1);p+=sizeof(middle)-1;
 for(unsigned i=0;i<12;i++){*p++=hex[nes_sink_trace168.ack[i]>>4];*p++=hex[nes_sink_trace168.ack[i]&15];}
 *p++='\n';*p=0;return (int)(p-text);
}
