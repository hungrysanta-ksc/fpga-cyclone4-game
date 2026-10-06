/* SPDX-License-Identifier: MIT */
/* Compile the actual materialized044 + appended056 binding against the mock
 * platform. This is lifecycle/model evidence, not physical MCU execution. */
#include "mcu_loader_platform.h"
#include "nes_rom_spi.h"
#include "nes_mcu_loader.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
MockGPIO mock_a,mock_b;
MockSPI mock_spi;
FRESULT file_res;
const uint8_t *fpga_config;
enum fault {
 NONE, OPEN, HEADER, CONTENT, SHORT_FIRST, READ_FIRST, SEEK, CONFIG, DONE,
 OWN_BUSY, ID, SPI_ID, LOST_ACK, READ_SECOND, SHORT_SECOND, CHANGE_HEADER,
 CHANGE_DATA, CLOSE, BASE_CONFIG, BASE_BUSY, BASE_TXE, BASE_TOKEN, STICKY
};
static enum fault fault;
static uint8_t rom[98320],loaded[98304],tx[8],reply[8];
static unsigned length,original_length,irq,reset_held,configs,closes,pass;
static unsigned bits,count,total,flags,begin_count,end_count,stop_count,frames,samples;
static unsigned protocol_error,done,ack_lost,read_calls;
static uint32_t mode_before,output_before,cr1_before;
static unsigned long long ns,previous;
static FILE *wave;
static void record(int expect) {
 if(wave)fprintf(wave,"%llu %u %u %u %d\n",ns-previous,
  !!(mock_a.ODR&16),!!(mock_b.ODR&8),!!(mock_b.ODR&32),expect);
 previous=ns;
}
unsigned NVIC_GetEnableIRQ(int n){assert(n==OTG_FS_IRQn);return irq;}
void NVIC_DisableIRQ(int n){assert(n==OTG_FS_IRQn);irq=0;}
void NVIC_EnableIRQ(int n){assert(n==OTG_FS_IRQn);assert(!configs||configs==2);irq=1;}
void snes_reset(int asserted){assert(asserted==1);reset_held=1;}
int get_snes_reset(void){return reset_held;}
tick_t getticks(void){return (tick_t)(ns/10000000);}
void delay_ms(unsigned v){ns+=(unsigned long long)v*1000000;}
void delay_us(unsigned v) {
 ns+=(unsigned long long)v*1000;
 if(!(mock_a.ODR&16) && (mock_b.ODR&8)) {
  assert(v==2 && bits>0);
  unsigned b=bits-1;
  bool val=(reply[b/8]>>(7-b%8))&1;
  mock_b.IDR=val?16:0;
  record(b<8?-2:val);samples++;
 }
}
static void commit(void) {
 assert(bits==16||bits==64);frames++;
 if(bits==16){assert(tx[0]==0xf0||tx[0]==0xf1);return;}
 assert(tx[0]!=NES_ROM_START); /* Also reject accidental legacy E8. */
 uint8_t crc=0;
 for(unsigned i=0;i<6;i++)for(unsigned b=0;b<8;b++) {
  unsigned top=((crc>>7)^((tx[i]>>(7-b))&1))&1;
  crc=(uint8_t)(crc<<1);if(top)crc^=7;
 }
 assert(crc==tx[6] && (unsigned)tx[4]+tx[5]==255 && tx[7]==0xa5);
 unsigned offset=((unsigned)tx[1]<<16)|((unsigned)tx[2]<<8)|tx[3];
 if(tx[0]==NES_ROM_STATUS)return;
 assert(!protocol_error);
 if(tx[0]==NES_ROM_BEGIN){assert(!count&&!flags);total=tx[4]?98304:81920;flags=1;begin_count++;return;}
 assert(offset==count);
 switch(tx[0]) {
  case NES_ROM_DATA:
   assert(flags==1 && count<total);loaded[count++]=tx[4];flags=count==total?0:1;
   if(fault==STICKY && count==1)protocol_error=2;
   break;
  case NES_ROM_END:assert(count==total&&!flags);end_count++;flags=2;break;
  case NES_ROM_STOP:stop_count++;flags=0;count=0;break;
  default:assert(0);
 }
}
void mock_pin(MockGPIO *port,unsigned pin,bool high) {
 assert(!irq && reset_held);
 unsigned old=port->ODR;
 if(high)port->ODR|=1u<<pin;else port->ODR&=~(1u<<pin);
 record(-1);
 if(port==GPIOA && pin==4 && !!(old&16)!=high) {
  if(!high){bits=0;memset(tx,0,8);memset(reply,0,8);}
  else commit();
 }
 if(port==GPIOB && pin==3 && high && !(old&8) && !(mock_a.ODR&16)) {
  assert(bits<64);tx[bits/8]=(uint8_t)((tx[bits/8]<<1)|!!(mock_b.ODR&32));bits++;
  if(bits==8) {
   if(tx[0]==0xf0)reply[1]=fault==ID?0:0xa5;
   else if(tx[0]==0xf1)reply[1]=0x44;
   else {
    reply[1]=fault==SPI_ID?0:0x54;
    reply[2]=(uint8_t)(flags|(protocol_error?8:0));reply[3]=(uint8_t)protocol_error;
    reply[4]=(uint8_t)(count>>16);reply[5]=(uint8_t)(count>>8);reply[6]=(uint8_t)count;
    if(fault==LOST_ACK && tx[0]==NES_ROM_STATUS && count==1 && !ack_lost){reply[1]=0;ack_lost=1;}
   }
  }
 }
}
void fpga_pgm(uint8_t *path) {
 assert(!irq && reset_held && (mock_a.ODR&16));
 configs++;done=1;file_res=FR_OK;fpga_config=path;
 if(configs==1) {
  assert(strcmp((const char *)path,"approved-test-image") == 0);
  if(fault==CONFIG)file_res=1;
  if(fault==DONE)done=0;
  if(fault==OWN_BUSY)mock_spi.SR|=SPI_SR_BSY;
 } else {
  assert(configs==2 && !strcmp((const char *)path,(const char *)FPGA_BASE));
  assert(mock_b.MODER==mode_before && mock_b.ODR==output_before && mock_spi.CR1==cr1_before);
  mock_spi.SR=SPI_SR_TXE;
  if(fault==BASE_CONFIG)file_res=1;
  if(fault==BASE_BUSY)mock_spi.SR=SPI_SR_BSY;
  if(fault==BASE_TXE)mock_spi.SR=0;
 }
}
int fpga_get_done(void){return done;}
unsigned fpga_test(void){assert(!irq&&configs==2&&reset_held);return fault==BASE_TOKEN?0:FPGA_TEST_TOKEN;}
FRESULT f_open(FIL *f,const char *path,unsigned mode) {
 assert(mode==FA_READ && !irq && reset_held && !strcmp(path,"fixture"));
 f->fsize=length;f->pos=0;return fault==OPEN?1:FR_OK;
}
FRESULT f_read(FIL *f,void *dest,UINT wanted,UINT *got) {
 assert(!irq&&reset_held);read_calls++;
 if((fault==READ_FIRST&&!pass&&f->pos==272)||(fault==READ_SECOND&&pass&&f->pos==272)){*got=0;return 1;}
 *got=wanted;if(f->pos+*got>length)*got=length-f->pos;
 if((fault==SHORT_FIRST&&!pass&&f->pos==272)||(fault==SHORT_SECOND&&pass&&f->pos==272))(*got)--;
 memcpy(dest,rom+f->pos,*got);
 if(fault==CHANGE_HEADER && pass && f->pos==0)((uint8_t *)dest)[6]^=1;
 if(fault==CHANGE_DATA && pass && f->pos==16)((uint8_t *)dest)[0]^=1;
 f->pos+=*got;return FR_OK;
}
FRESULT f_lseek(FIL *f,uint32_t offset){assert(!irq&&offset==0);f->pos=offset;pass++;return fault==SEEK?1:FR_OK;}
FRESULT f_close(FIL *f){(void)f;assert(!irq);closes++;return fault==CLOSE?1:FR_OK;}
FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){(void)f;(void)p;(void)n;(void)got;assert(0);return 1;}
static void initialize(enum fault f,unsigned enabled) {
 fault=f;irq=enabled;reset_held=configs=closes=pass=0;
 bits=count=total=flags=begin_count=end_count=stop_count=frames=samples=0;
 protocol_error=ack_lost=read_calls=0;done=1;ns=previous=0;
 length=original_length;mock_a=(MockGPIO){0,16,0};
 mock_b=(MockGPIO){0x5a5a5a5a,0xdeadbeef,0};mock_spi=(MockSPI){SPI_SR_TXE,0x147};
 mode_before=mock_b.MODER;output_before=mock_b.ODR;cr1_before=mock_spi.CR1;
 memset(loaded,0,sizeof(loaded));
}
static void test(enum fault f,enum nes_mcu_load_result result,unsigned enabled) {
 initialize(f,enabled);
 struct nes_mcu_load_report r;
 if(f==HEADER)rom[6]^=4;
 if(f==CONTENT)rom[32]^=1;
 bool safe=nes_mcu_load_probe("fixture","approved-test-image",&r);
 if(f==HEADER)rom[6]^=4;
 if(f==CONTENT)rom[32]^=1;
 bool recovery_failure=f>=BASE_CONFIG&&f<=BASE_TOKEN;
 assert(safe==!recovery_failure);
 assert(r.result==result && reset_held && irq==(recovery_failure?0:enabled));
 assert(closes==(f==OPEN?0:1));
 assert(configs==0||configs==2);
 assert(r.recovery_attempted==(configs==2));
 assert(r.base_restored==(configs==2&&!recovery_failure));
 assert(mock_b.MODER==mode_before && mock_b.ODR==output_before && mock_spi.CR1==cr1_before);
 if(f==NONE || recovery_failure) {
  assert(r.end_accepted && end_count==1 && r.stop_ok && stop_count==1);
  assert(r.acknowledged_bytes==length-16 && !memcmp(loaded,rom+16,length-16));
 } else assert(!r.end_accepted && !end_count);
 if(f==READ_SECOND||f==SHORT_SECOND)assert(r.acknowledged_bytes==256 && stop_count==1);
 if(f==LOST_ACK)assert(r.acknowledged_bytes==0 && ack_lost && stop_count==1);
 if(f==STICKY)assert(r.acknowledged_bytes==0 && !r.stop_ok && !stop_count);
 printf("PASS lifecycle fault=%u chr=%u irq_before=%u bytes=%lu end=%u stop=%u safe=%u frames=%u samples=%u\n",
  f,r.chr_32k,enabled,(unsigned long)r.acknowledged_bytes,r.end_accepted,r.stop_ok,safe,frames,samples);
}
int main(int argc,char **argv) {
 assert(argc==3||argc==4);
 for(unsigned c=1;c<=2;c++) {
  FILE *input=fopen(argv[c],"rb");assert(input);
  original_length=(unsigned)fread(rom,1,sizeof(rom),input);assert(feof(input)||original_length==sizeof(rom));fclose(input);
  assert(original_length==(c==1?81936u:98320u));
  test(NONE,NES_MCU_LOAD_OK,1);test(NONE,NES_MCU_LOAD_OK,0);
 }
 const enum nes_mcu_load_result results[]={NES_MCU_LOAD_OK,NES_MCU_LOAD_OPEN,NES_MCU_LOAD_HEADER,
  NES_MCU_LOAD_CONTENT,NES_MCU_LOAD_READ,NES_MCU_LOAD_READ,NES_MCU_LOAD_SEEK,NES_MCU_LOAD_CONFIG,
  NES_MCU_LOAD_CONFIG,NES_MCU_LOAD_OWNERSHIP,NES_MCU_LOAD_ID,NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,
  NES_MCU_LOAD_READ,NES_MCU_LOAD_READ,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CLOSE,
  NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_SPI};
 for(unsigned f=OPEN;f<=STICKY;f++)test((enum fault)f,results[f],1);
 /* Exact header rejection covers NES2, mapper, trainer, reserved bytes and
  * unsupported sizes independently of CRC; no FPGA mutation on rejection. */
 unsigned rejected=0;
 for(unsigned index=0;index<16;index++) {
  initialize(NONE,1);rom[index]^=0x80;struct nes_mcu_load_report r;
  assert(nes_mcu_load_probe("fixture","approved-test-image",&r));
  assert(r.result==NES_MCU_LOAD_HEADER && !configs && irq==1);rom[index]^=0x80;rejected++;
 }
 for(int delta=-1;delta<=1;delta+=2) {
  initialize(NONE,1);length=(unsigned)((int)length+delta);struct nes_mcu_load_report r;
  assert(nes_mcu_load_probe("fixture","approved-test-image",&r));
  assert(r.result==NES_MCU_LOAD_HEADER&&!configs);rejected++;
 }
 if(argc==4) {
  wave=fopen(argv[3],"w");assert(wave);
  test(READ_SECOND,NES_MCU_LOAD_READ,1);fclose(wave);wave=0;
 }
 printf("PASS MCU LOADER lifecycle=26 header_rejections=%u no_start=1 no_sd_writes=1\n",rejected);
 return 0;
}
