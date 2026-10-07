/* SPDX-License-Identifier: GPL-2.0-only */
#include "nes_report_boot080.h"
/* Pinned legacy embedded streams end with FF; the original caller discards
 * that terminal decoded byte. Preserve those exact output bytes, while
 * rejecting truncated/zero runs and bounding every input and output access. */
bool report_decode080(const uint8_t *s,unsigned size,unsigned expected,
                      report_sink080 sink,void *ctx) {
 unsigned at=0,out=0;
 if(!s||size<2||s[size-1]!=255||!expected||!sink)return false;
 while(at<size-1) {
  unsigned token=s[at++],value=token,count=1;
  if(token==0x9b||token==0x5b||token==0x77) {
   if(at>=size-1)return false;
   value=s[at++];
   if(token!=0x9b) {
    if(at>=size-1)return false;
    count=s[at++];
    if(token==0x77) {if(at>=size-1)return false;count|=(unsigned)s[at++]<<8;}
    if(!count)return false;
   }
  }
  if(count>expected-out)return false;
  for(unsigned i=0;i<count;i++) {if(!sink(ctx,(uint8_t)value))return false;out++;}
 }
 return out==expected;
}
