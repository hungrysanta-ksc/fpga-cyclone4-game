/* SPDX-License-Identifier: MIT */
/* Test-only held queue. Actual SNES CPU owns packet reads, display and ACKs.
 * Events are replayed through the actual RTL/bus afterwards, byte for byte.
 * File scheduling is not a cycle-accurate three-processor performance model. */
#include "nes_sink_window184.h"
static struct nes_sink_window184 window;
static uint8_t slots[4][256],last_ack[12];
static unsigned sizes[4],accepted,retired,max_used,calls,guards;
static bool queue_fault,ack_valid;
static FILE *events;
static uint8_t c8(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}
static uint16_t c16(uint16_t c,uint8_t b){c^=(uint16_t)b<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&0x8000?(c<<1)^0x1021:c<<1);return c;}
static void hex(const uint8_t *b,unsigned n){for(unsigned i=0;i<n;i++)fprintf(events,"%02x",b[i]);}
static void harvest(void){
 while(retired<accepted&&!queue_fault){
  char path[80];snprintf(path,sizeof(path),"ack-%04u.bin",retired+1);FILE *f=fopen(path,"rb");if(!f)break;
  assert(fread(last_ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);unsigned slot=retired%4;uint8_t *b=slots[slot];
  fprintf(events,"A %u ",sizes[slot]);hex(b,sizes[slot]);fputc(' ',events);hex(last_ack,12);fputc('\n',events);
  ack_valid=true;
  queue_fault=last_ack[0]!=(b[0]==3?1:0)||last_ack[1]!=b[0]||memcmp(last_ack+2,b+2,8)||last_ack[10]!=0x65||last_ack[11]!=0x9a;
  if(!queue_fault)retired++;
 }
}
static bool queued_guard(void *ctx){(void)ctx;guards++;return true;}
static bool queued_transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;harvest();memset(rx,0,n);calls++;
 if(tx[0]==0xe1){
  assert(!queue_fault&&accepted-retired<4&&n>=19&&n<=259);unsigned size=n-3;
  uint16_t c=0xffff;for(unsigned i=0;i<n-2;i++)c=c16(c,tx[i]);assert(c==((unsigned)tx[n-2]<<8|tx[n-1]));
  assert(size==16u+get16(tx+13));
  unsigned slot=accepted%4;sizes[slot]=size;memcpy(slots[slot],tx+1,size);accepted++;ordinal=accepted;wire_bytes+=n;
  if(accepted-retired>max_used)max_used=accepted-retired;
  char tmp[80],path[80];snprintf(tmp,sizeof(tmp),"req-%04u.tmp",accepted);snprintf(path,sizeof(path),"req-%04u.bin",accepted);
  FILE *f=fopen(tmp,"wb");assert(f&&fwrite(tx+1,1,size,f)==size);fclose(f);assert(rename(tmp,path)==0);
 }else{
  assert(tx[0]==0xe0&&n==20);
  rx[1]=0xf7;rx[2]=(queue_fault?128:0)|(accepted!=retired?1:0)|(ack_valid?2:0)|(accepted-retired==4?4:0);
  rx[3]=(uint8_t)(accepted>>8);rx[4]=(uint8_t)accepted;rx[5]=(uint8_t)(retired>>8);rx[6]=(uint8_t)retired;
  memcpy(rx+7,last_ack,12);for(unsigned i=1;i<19;i++)rx[19]=c8(rx[19],rx[i]);
 }
 fprintf(events,"T %u ",n);hex(tx,n);fputc(' ',events);hex(rx,n);fputc('\n',events);fflush(events);
 if(tx[0]==0xe0)Sleep(1);
 return true;
}
