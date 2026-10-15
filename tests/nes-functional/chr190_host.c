/* SPDX-License-Identifier: MIT */
/* Host-only lossless expansion against the unchanged deployed C receiver.
 * This is not the proposed runtime (no sixteen-packet loop on SNES/MCU). */
#include "nes_native165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 reference, candidate;
static unsigned calls;
static void submit(struct nes_native165 *s,const unsigned char *p,unsigned n){
 if(p[0]==0xe0&&p[1]==3){assert(s->state==NES_NATIVE165_COMPLETE);s->state=NES_NATIVE165_PREPARED;}
 assert(nes_native165_packet(s,s->next_token,p,n));calls++;
}
int main(int argc,char **argv){
 assert(argc==3);
 static const unsigned widths[]={2,1,7,4,7,1,2,8};
 FILE *f=fopen(argv[1],"r");assert(f);unsigned x,n=0;unsigned char b[65536];
 while(fscanf(f,"%x",&x)==1){assert(n<sizeof b&&x<256);b[n++]=(unsigned char)x;}fclose(f);
 for(unsigned at=0;at<n;){unsigned k=b[at]>>5,len=widths[k]+4;assert(at+len<=n);submit(&reference,b+at,len);at+=len;}
 f=fopen(argv[2],"r");assert(f);n=0;
 while(fscanf(f,"%x",&x)==1){assert(n<sizeof b&&x<256);b[n++]=(unsigned char)x;}fclose(f);
 for(unsigned at=0;at<n;){
  unsigned k=b[at]>>5,len=k==6?22:widths[k]+4;assert(at+len<=n);
  unsigned char p[12];memcpy(p,b+at,4);
  if(k==6){
   assert(b[at+4]>=1&&b[at+4]<=3&&b[at+5]==0);
   for(unsigned lane=0;lane<16;lane++){
    p[4]=(unsigned char)((b[at+4]<<4)|lane);p[5]=b[at+6+lane];submit(&candidate,p,6);
   }
  }else{
   memcpy(p,b+at,len);
   if(k==7&&(p[0]&31)==0&&p[1]==0){assert(p[4]==0x19&&p[5]==1);p[4]=0x18;p[5]=0x13;}
   submit(&candidate,p,len);
  }
  at+=len;
 }
 assert(reference.state==NES_NATIVE165_COMMITTED);
 assert(memcmp(&reference,&candidate,sizeof reference)==0);
 printf("PASS CHR190C receiver_bytes=%u calls=%u tiles=%u\n",(unsigned)sizeof reference,calls,(unsigned)candidate.ntiles);
 return 0;
}
