/* SPDX-License-Identifier: MIT */
#include "nes_native_sink165.h"
#include "nes_sink_trace168.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native_sink165 sink;
static unsigned calls,fail_op,status_code;
static uint8_t req[16],reply[12];
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t *a){
 (void)ctx;assert(n>=16&&sink.state==NES_SINK165_BUSY);calls++;
 a[0]=b[0]==3?1:0;a[1]=b[0];memcpy(a+2,b+2,8);a[10]=0x65;a[11]=0x9a;
 if(b[0]==fail_op){a[0]=(uint8_t)status_code;memcpy(req,b,16);memcpy(reply,a,12);return status_code!=256;}
 return true;
}
int main(void){
 uint8_t b[16]={0},a[12]={0};unsigned checks=0;
 for(unsigned op=1;op<=3;op++){
  b[0]=(uint8_t)op;for(unsigned i=2;i<16;i++)b[i]=(uint8_t)(i*23);
  a[0]=op==3?1:0;a[1]=(uint8_t)op;memcpy(a+2,b+2,8);a[10]=0x65;a[11]=0x9a;
  assert(nes_sink168_mismatch(b,a)==0);
  for(unsigned at=0;at<12;at++)for(unsigned value=0;value<256;value++){
   uint8_t old=a[at];a[at]=(uint8_t)value;
   bool prior=a[0]!=(op==3?1:0)||a[1]!=op||memcmp(a+2,b+2,8)||a[10]!=0x65||a[11]!=0x9a;
   uint8_t bit=at==0?1:at==1?2:at<4?4:at<8?8:at<10?16:32;
   assert(nes_sink168_mismatch(b,a)==(old==value?0:bit));
   assert(prior==(nes_sink168_mismatch(b,a)!=0));a[at]=old;checks++;
  }
 }
 for(fail_op=1;fail_op<=3;fail_op++)for(status_code=224;status_code<=256;status_code++){
  if(status_code>228&&status_code<256)continue;
  calls=0;nes_sink165_reset(&sink,exchange,NULL);assert(!nes_sink_trace168.valid);
  struct nes_native_video165 video={0};video.valid=true;video.generation=24;video.bg_count=1;video.hdma_size=1;
  uint8_t pattern[16]={0};bool ok=nes_sink165_begin(&sink,24);
  if(ok)ok=nes_sink165_pattern(&sink,0,0,pattern,16);
  if(ok)ok=nes_sink165_seal(&sink,&video,5000);
  assert(!ok&&sink.state==NES_SINK165_FAULT&&sink.error==(status_code==256?2:3));
  assert(nes_sink_trace168.valid&&nes_sink_trace168.ack_valid==(status_code!=256));
  assert(!memcmp(nes_sink_trace168.request,req,16));
  if(status_code!=256)assert(!memcmp(nes_sink_trace168.ack,reply,12)&&nes_sink_trace168.mismatch==1);
  else {uint8_t zero[12]={0};assert(!memcmp(nes_sink_trace168.ack,zero,12)&&!nes_sink_trace168.mismatch);}
  struct nes_sink_trace168 saved=nes_sink_trace168;unsigned before=calls;
  assert(!nes_sink165_begin(&sink,25)&&calls==before);
  nes_sink168_capture(b,a,true,63);assert(!memcmp(&saved,&nes_sink_trace168,sizeof saved));
 }
 fail_op=0;nes_sink165_reset(&sink,exchange,NULL);assert(!nes_sink_trace168.valid);
 assert(nes_sink165_begin(&sink,22));
 char text[256];memset(text,0x5a,sizeof text);int length=nes_sink168_format(text,sizeof text);assert(length>0&&text[length]==0&&text[length+1]==0x5a);
 assert(strstr(text,"sink_trace_valid=0\nsink_trace_ack_valid=0\nsink_trace_mismatch_hex=00\n"));
 nes_sink168_capture(b,a,true,63);length=nes_sink168_format(text,sizeof text);
 assert(strstr(text,"sink_trace_valid=1\nsink_trace_ack_valid=1\nsink_trace_mismatch_hex=3f\n"));
 for(unsigned cap=0;cap<=(unsigned)length;cap++){memset(text,0x5a,sizeof text);assert(nes_sink168_format(text,cap)==-1);for(unsigned i=0;i<sizeof text;i++)assert(text[i]==0x5a);}
 assert(nes_sink168_format(text,(unsigned)length+1)==length);
 printf("PASS mismatch_equivalence=%u operation_faults=18 trace_bytes=%u report_bytes=%d no_retry=1 first_failure=1 reset=1 bounded_format=1\n",checks,(unsigned)sizeof nes_sink_trace168,length);
 return 0;
}
