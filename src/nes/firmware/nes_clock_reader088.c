/* SPDX-License-Identifier: MIT */
#include <string.h>
#include "config.h"
#include "bits.h"
#include "snes.h"
#include "fpga.h"
#include "nes_menu_return.h"
#include "nes_clock_reader088.h"
extern int sd_offload,ff_sd_offload,during_blocktrans;
extern int fpga_get_done(void);
#define MODE088 ((3u<<6)|(3u<<8)|(3u<<10))
#define OUT088 ((1u<<3)|(1u<<5))
static bool owned088,active088;
static uint32_t mode088,output088,cr1088;
static struct clock_report088 *report088;

static uint32_t le32(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static bool fault088(enum clock_result088 reason,enum nes_diag_error error) {
 report088->result=reason;snes_reset(1);nes_return_fail(error);return false;
}
static bool context088(void) {
 return nes_diag_active()&&!nes_return_failed()&&!nes_return_log_allowed()&&
  !sd_offload&&!ff_sd_offload&&!during_blocktrans&&get_snes_reset()&&fpga_get_done()&&
  !(NVIC->ISER[OTG_FS_IRQn>>5]&(1u<<(OTG_FS_IRQn&31)));
}
static bool check088(void) {
 if(!context088()||!nes_return_io_step())return fault088(CLOCK088_IO_ERROR,NES_DIAG_SPI);
 if((uint32_t)(nes_diag_ticks()-report088->started)>=450) {
  report088->result=CLOCK088_NO_PROGRESS;return false;
 }
 return true;
}
static bool pause088(unsigned us) {
 if(!check088())return false;
 if(!nes_return_delay(us,false))return fault088(CLOCK088_IO_ERROR,NES_DIAG_TIMER);
 return check088();
}
static void park088(void) {
 /* Safe CS cancellation only, also when a timer/shared fault prevents waits. */
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);CLEAR_BIT(GPIOB,3);
}
static bool begin088(void) {
 if(!check088())return false;
 if(owned088)return fault088(CLOCK088_IO_ERROR,NES_DIAG_SPI);
 for(unsigned n=0;SPI1->SR&SPI_SR_BSY;n++) {
  if(n==1000)return fault088(CLOCK088_IO_ERROR,NES_DIAG_SPI);
  if(!pause088(1))return false;
 }
 if(!(SPI1->SR&SPI_SR_TXE))return fault088(CLOCK088_IO_ERROR,NES_DIAG_SPI);
 cr1088=SPI1->CR1;mode088=GPIOB->MODER&MODE088;output088=GPIOB->ODR&OUT088;
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);SPI1->CR1=cr1088&~SPI_CR1_SPE;
 CLEAR_BIT(GPIOB,3);CLEAR_BIT(GPIOB,5);
 GPIOB->MODER=(GPIOB->MODER&~MODE088)|(1u<<6)|(1u<<10);owned088=true;
 return pause088(2);
}
static void end088(bool ok) {
 if(!owned088)return;
 park088();
 /* A shared fault keeps hardware SPI disabled and pins parked, not restored
  * to unknown saved AF output. Only clean observation completion returns it. */
 if(ok&&!nes_return_failed()) {
  if(output088&(1u<<3))SET_BIT(GPIOB,3);
  if(output088&(1u<<5))SET_BIT(GPIOB,5);else CLEAR_BIT(GPIOB,5);
  GPIOB->MODER=(GPIOB->MODER&~MODE088)|mode088;SPI1->CR1=cr1088;
 }
 owned088=false;
}
static bool frame088(uint8_t command,uint8_t *data,unsigned length) {
 if(!owned088||!check088())return false;
 CLEAR_BIT(GPIOB,3);CLEAR_BIT(FPGA_SSREG,FPGA_SSBIT);
 if(!pause088(2))goto fail;
 for(unsigned i=0;i<=length;i++) {
  uint8_t tx=i?0:command,value=0;
  for(unsigned bit=0;bit<8;bit++) {
   if(!check088())goto fail;
   if(tx&(0x80u>>bit))SET_BIT(GPIOB,5);else CLEAR_BIT(GPIOB,5);
   if(!pause088(2))goto fail;
   SET_BIT(GPIOB,3);
   if(!pause088(2))goto fail;
   value=(uint8_t)((value<<1)|(BITBAND(GPIOB->IDR,4)&1u));
   CLEAR_BIT(GPIOB,3);
  }
  if(i)data[i-1]=value;
  if(!pause088(2))goto fail;
 }
 if(!pause088(2))goto fail;
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);
 if(!pause088(2))goto fail;
 report088->frames++;return true;
fail:
 park088();return false;
}
static bool schema088(const uint8_t *s) {
 uint32_t seq=le32(s+2),count=le32(s+6);
 if(s[0]!=0x87||(s[1]&0xf0)||le32(s+10)!=8000000||s[14]!=16||s[15]||
    seq==UINT32_MAX||count>4000000||
    (!(s[1]&1)&&(seq||count||(s[1]&8)))||((s[1]&1)&&!seq))
  return fault088(CLOCK088_PROTOCOL_ERROR,NES_DIAG_SPI);
 return true;
}
bool nes_clock_collect088(struct clock_report088 *out) {
 if(!out)return false;
 /* Do not overwrite an active call's report or saved GPIO state on reentry. */
 if(active088){snes_reset(1);nes_return_fail(NES_DIAG_SPI);return false;}
 active088=true;memset(out,0,sizeof(*out));report088=out;out->started=nes_diag_ticks();
 bool ok=false;uint8_t id=0,a[16],b[16];uint32_t previous=0,initial=0;bool first=true,discontinuous=false;
 if(!begin088()||!frame088(0xcf,&id,1))goto done;
 if(id!=0x87){fault088(CLOCK088_PROTOCOL_ERROR,NES_DIAG_SPI);goto done;}
 for(unsigned n=0;n<512;n++) {
  out->elapsed=(uint32_t)(nes_diag_ticks()-out->started);
  if(out->elapsed>=450)break; /* 100Hz ticks, one budget across all frames. */
  out->attempts++;
  if(!frame088(0xc0,a,16)||!schema088(a)||!frame088(0xc0,b,16)||!schema088(b))goto done;
  uint32_t sa=le32(a+2),sb=le32(b+2);
  if(sb<sa||(!first&&sa<previous)){fault088(CLOCK088_PROTOCOL_ERROR,NES_DIAG_SPI);goto done;}
  if(sa==sb) {
   /* Count/sequence/window/ID are immutable within a completed window. Live
    * and ever-gap can change while reading, so use the second observation. */
   if(memcmp(a+2,b+2,14)||((a[1]^b[1])&9)||((a[1]&4)&&!(b[1]&4))) {
    fault088(CLOCK088_PROTOCOL_ERROR,NES_DIAG_SPI);goto done;
   }
   if(first){memcpy(out->initial,b,16);initial=sb;previous=sb;first=false;}
   else if(sb>previous) {
    if(sb!=previous+1)discontinuous=true;
    previous=sb;
    /* Discard the startup window: its gap flag includes synchronizer fill. */
    if(sb>=2&&sb>initial) {
     memcpy(out->sample[out->captured++],b,16);
     if(out->captured==2) {
      bool active=true,absent=true;
      for(unsigned i=0;i<2;i++) {
       const uint8_t *s=out->sample[i];uint32_t count=le32(s+6);
       active=active&&((s[1]&11)==3)&&count>0;
       absent=absent&&!(s[1]&2)&&!count;
      }
      out->result=discontinuous?CLOCK088_UNSTABLE:active?CLOCK088_ACTIVE:absent?CLOCK088_ABSENT:CLOCK088_UNSTABLE;
      ok=true;goto done;
     }
    }
   }
  }
  if(!pause088(10000))goto done;
 }
 out->result=CLOCK088_NO_PROGRESS;ok=true;
done:
 out->elapsed=(uint32_t)(nes_diag_ticks()-out->started);
 if(out->result==CLOCK088_NO_PROGRESS&&!nes_return_failed())ok=true;
 end088(ok);active088=false;return ok;
}
