/* SPDX-License-Identifier: MIT */
/* Host response model plus real C callback waveform prefix for RTL replay. */
#include "nes_rom_verify.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static FILE *wave;
static unsigned long long ns,previous;
static unsigned ss=1,sck,mosi,bit,frames,flags,total,next,proto,done_data,reads,acks,starts;
static unsigned scenario;
static uint8_t tx[8],reply[8];
static unsigned char value(unsigned a){return (unsigned char)((a*73)^(a>>7)^(a>>13)^0xa6);}
static void record(int expect){if(wave)fprintf(wave,"%llu %u %u %u %d\n",ns-previous,ss,sck,mosi,expect);previous=ns;}
static void select_pin(void *ctx,bool active){
 (void)ctx;ss=!active;record(-1);
 if(active){bit=0;memset(tx,0,8);memset(reply,0,8);return;}
 assert(bit==64);frames++;
 unsigned offset=((unsigned)tx[1]<<16)|((unsigned)tx[2]<<8)|tx[3];
 uint8_t check[8];nes_rom_spi_frame(check,tx[0],offset,tx[4]);assert(!memcmp(check,tx,8));
 if(proto)return;
 switch(tx[0]){
  case 0x65:case 0x6a:break;
  case 0x66:assert(flags==2&&offset==0);flags=0x22;next=0;break;
  case 0x67:assert(flags==0x22&&offset==next);reads++;flags=0x62;done_data=value(next);if(scenario==1&&next==7)done_data^=1;if(scenario==3&&next==7)flags=0x23;break;
  case 0x68:assert(flags==0x62&&offset==next&&tx[4]==done_data);acks++;next++;flags=0x22;break;
  case 0x69:assert(next==total&&offset==total);flags=0x82;break;
  case 0x63:assert(flags==0x82);flags=0x86;starts++;break;
  case 0x64:flags=0;total=0;next=0;break;
  default:assert(0);
 }
}
static void clock_pin(void *ctx,bool high){
 (void)ctx;sck=high;record(-1);
 if(high){
  assert(bit<64);tx[bit/8]=(uint8_t)((tx[bit/8]<<1)|mosi);bit++;
  if(bit==8){
   unsigned n=tx[0]==0x6a?next:total;
   reply[1]=(scenario==5?0x54:0x59);reply[2]=(uint8_t)flags;
   reply[3]=tx[0]==0x6a?(uint8_t)done_data:(uint8_t)proto;
   if(scenario==2&&next==7&&tx[0]==0x6a)n++;
   if(scenario==6&&next==7&&tx[0]==0x6a)reply[2]=0xe2;
   reply[4]=(uint8_t)(n>>16);reply[5]=(uint8_t)(n>>8);reply[6]=(uint8_t)n;
  }
 }
}
static void mosi_pin(void *ctx,bool high){(void)ctx;mosi=high;record(-1);}
static bool miso_pin(void *ctx){
 (void)ctx;unsigned b=bit-1;int expected=(reply[b/8]>>(7-b%8))&1;
 record(b<8?-2:expected);return expected!=0;
}
static void wait_us(void *ctx,unsigned delay){(void)ctx;ns+=(unsigned long long)delay*1000;}
static bool source(void *ctx,uint32_t a,uint8_t *data){(void)ctx;if((scenario==4&&a==7)||(scenario==7&&a==32))return false;*data=value(a);return true;}
static void fresh(unsigned size,unsigned s){scenario=s;total=size;flags=2;next=0;proto=0;done_data=0;reads=0;acks=0;starts=0;frames=0;ns=0;previous=0;ss=1;sck=0;mosi=0;}
int main(int argc,char **argv){
 assert(argc==2);struct nes_rom_spi_io io={0,select_pin,clock_pin,mosi_pin,miso_pin,wait_us};struct nes_verify_report r;
 for(unsigned size=0x14000;size<=0x18000;size+=0x4000){
  fresh(size,0);assert(nes_rom_verify(&io,size,source,0,&r)&&r.error==0&&r.compared==size);
  assert(reads==size&&acks==size&&starts==0);assert(nes_rom_verified_start(&io,size)&&starts==1);
 }
 const enum nes_verify_error errors[]={NES_VERIFY_OK,NES_VERIFY_DATA,NES_VERIFY_TAG,NES_VERIFY_TIMEOUT,NES_VERIFY_SOURCE,NES_VERIFY_PROTOCOL,NES_VERIFY_PROTOCOL};
 for(unsigned s=1;s<=6;s++){
  fresh(0x14000,s);assert(!nes_rom_verify(&io,total,source,0,&r));
  assert(r.error==errors[s]&&starts==0&&acks==(s==5?0:7));
  if(s!=5)assert(r.stop_ok&&flags==0);
 }
 fresh(0x14000,0);assert(!nes_rom_verify(&io,16,source,0,&r)&&r.error==NES_VERIFY_ARGUMENT&&frames==0);
 assert(!nes_rom_verify(&io,0x14000,0,0,&r)&&frames==0);
 assert(!nes_rom_verify(&io,0x14000,source,0,0)&&frames==0);
 assert(!nes_rom_verified_start(&io,16)&&frames==0);
 fresh(0x14000,7);wave=fopen(argv[1],"w");assert(wave);
 assert(!nes_rom_verify(&io,total,source,0,&r)&&r.error==NES_VERIFY_SOURCE&&r.compared==32&&r.stop_ok);
 fclose(wave);wave=0;
 printf("PASS MCU VERIFY full_bytes=180224 full_images=2 negative_cases=10 waveform_reads=%u waveform_acks=%u waveform_frames=%u no_start_on_error=1\n",reads,acks,frames);
 return 0;
}
