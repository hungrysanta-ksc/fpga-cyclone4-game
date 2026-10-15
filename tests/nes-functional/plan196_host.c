/* SPDX-License-Identifier: MIT */
#include "nes_plan_wire196.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void output(FILE *f,const struct nes_plan191 *q){
 uint8_t b[32];uint16_t c;unsigned n=nes_plan196_encode(q,b,&c);assert(n);
 fprintf(f,"%02x",n);for(unsigned i=0;i<n;i++)fprintf(f," %02x",b[i]);fprintf(f," %04x\n",c);
}
static void zero(struct nes_plan191 *q){memset(q,0,sizeof(*q));for(unsigned i=0;i<8;i++)q->alt[i]=65535;}
int main(int argc,char **argv){
 assert(argc==2);unsigned plans=0,bytes=0,checks=0;
 for(unsigned scene=0;scene<8;scene++){
  char path[1024];snprintf(path,sizeof(path),"%s/scene%u.plans",argv[1],scene);FILE *in=fopen(path,"r");assert(in);
  snprintf(path,sizeof(path),"scene%u.wire",scene);FILE *out=fopen(path,"w");assert(out);
  unsigned v[29];while(fscanf(in,"%u",&v[0])==1){
   for(unsigned i=1;i<29;i++)assert(fscanf(in,"%u",&v[i])==1);
   struct nes_plan191 q={0};q.kind=(uint8_t)v[0];q.generation=(uint16_t)v[1];q.slot=(uint16_t)v[2];q.tag=(uint16_t)v[3];q.mask=(uint8_t)v[4];
   for(unsigned i=0;i<16;i++)q.row[i]=(uint8_t)v[5+i];
   for(unsigned i=0;i<8;i++)q.alt[i]=(uint16_t)v[21+i];
   output(out,&q);uint8_t b[32];uint16_t crc;bytes+=nes_plan196_encode(&q,b,&crc);plans++;
  }
  struct nes_plan191 end;zero(&end);end.kind=3;end.generation=(uint16_t)(100+scene);output(out,&end);
  fclose(in);fclose(out);
 }
 /* Every alternate-row bitmap, including32B maximum and field maxima. */
 FILE *out=fopen("boundary.wire","w");assert(out);
 for(unsigned mask=0;mask<256;mask++){
  struct nes_plan191 q;zero(&q);q.kind=0;q.generation=65535;q.slot=1023;q.tag=8191;q.mask=255;
  for(unsigned i=0;i<16;i++)q.row[i]=(uint8_t)((i*5)&7);
  for(unsigned i=0;i<8;i++)if(mask&(1u<<i))q.alt[i]=(uint16_t)(8191-i);
  output(out,&q);checks++;
 }
 fclose(out);
 for(unsigned bad=0;bad<12;bad++){
  struct nes_plan191 q;zero(&q);q.kind=0;q.slot=1;q.mask=255;
  switch(bad){case 0:q.kind=4;break;case 1:q.slot=1024;break;case 2:q.tag=8192;break;
   case 3:q.row[15]=8;break;case 4:q.alt[0]=8192;break;case 5:q.slot=0;break;
   case 6:q.mask=254;break;case 7:q.kind=1;q.slot=128;break;case 8:q.kind=1;q.mask=0;break;
   case 9:q.kind=1;q.alt[7]=1;break;case 10:q.kind=2;break;case 11:q.kind=3;break;}
  uint8_t b[32];uint16_t crc;assert(!nes_plan196_encode(&q,b,&crc));checks++;
 }
 assert(plans==97&&bytes==1580);printf("PASS PLAN196 plans=%u bytes=%u boundaries=%u\n",plans,bytes,checks);return 0;
}
