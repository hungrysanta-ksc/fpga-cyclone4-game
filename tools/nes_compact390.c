/* SPDX-License-Identifier: MIT */
/* Uses192B bounded scratch. Input is the current target-bank dirty bitmap,
 * not future geometry. The live caller charges a separate209B SPI buffer. */
#include <stdint.h>
extern unsigned map_byte327(unsigned);
static struct {unsigned scan,run,start,ranges,words,columns,cost,done;} plan390;
static void p16_390(uint8_t *p,unsigned v){p[0]=v;p[1]=v>>8;}
void reset_plan390(void){plan390=(__typeof__(plan390)){0};}
static void range390(uint8_t *b){
 if(!plan390.run)return;
 if(plan390.ranges<7){p16_390(b+144+4*plan390.ranges,plan390.start);p16_390(b+146+4*plan390.ranges,plan390.run);}
 plan390.ranges++;plan390.run=0;
}
unsigned step_plan390(uint8_t *b){
 if(plan390.done)return plan390.done;
 if(!plan390.scan)for(unsigned c=0;c<64;c++){b[16+2*c]=32;b[17+2*c]=0;}
 /* Bounded16 bitmap bytes,then16 column budgets per foreground visit. */
 for(unsigned steps=0;steps<16&&plan390.scan<320;steps++,plan390.scan++){
  unsigned g=plan390.scan;
  if(g<256){
   unsigned bits=map_byte327(g);
   if(!bits){range390(b);continue;}
   for(unsigned i=0;i<8;i++){
    unsigned w=g*8+i;
    if(bits&(1u<<i)){
     unsigned col=(w&31)+(w/1024)*32,row=(w/32)&31;
     if(b[16+col*2]>row)b[16+col*2]=row;
     if(b[17+col*2]<row)b[17+col*2]=row;
     if(!plan390.run)plan390.start=w;
     plan390.run++;plan390.words++;
     if(plan390.run==32)range390(b);
    }else range390(b);
   }
  }else{
   if(g==256)range390(b);
   unsigned c=g-256,lo=b[16+2*c],hi=b[17+2*c];
   if(lo<32){plan390.columns++;plan390.cost+=1280+(hi-lo+1)*16;}
  }
 }
 if(plan390.scan!=320)return 0;
 unsigned sparse=1280*plan390.ranges+16*plan390.words;
 unsigned mode=plan390.cost<34048?1:2;
 if(plan390.ranges<=7&&sparse<=plan390.cost&&sparse<=34048)mode=0;
 unsigned length=mode==0?16+4*plan390.ranges:mode==1?144:16;
 if(!mode)for(unsigned i=0;i<4*plan390.ranges;i++)b[16+i]=b[144+i];
 b[0]='M';b[1]='P';b[2]=1;b[3]=mode;b[5]=0;
 p16_390(b+12,plan390.ranges);p16_390(b+14,plan390.words);
 plan390.done=length;return length;
}
