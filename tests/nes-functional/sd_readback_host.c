/* SPDX-License-Identifier: MIT */
/* Compile the actual materialized044 + appended056 binding against the mock
 * platform. This is lifecycle/model evidence, not physical MCU execution. */
#include "mcu_loader_platform.h"
#include "nes_rom_spi.h"
#include "nes_sd_readback.h"
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
 CHANGE_DATA, CLOSE, BASE_CONFIG, BASE_BUSY, BASE_TXE, BASE_TOKEN, STICKY, THIRD_OPEN, THIRD_HEADER, THIRD_SIZE, THIRD_READ, THIRD_SHORT, THIRD_CHANGED, THIRD_CRC, THIRD_CLOSE, RB_DATA, RB_TAG, RB_TIMEOUT, RB_STATUS, RB_ACK_LOST, FINISH_LOST, STOP_FAILED
};
static enum fault fault;
static uint8_t rom[98320],loaded[98304],tx[8],reply[8];
static unsigned length,original_length,irq,reset_held,configs,closes,pass;
static unsigned bits,count,total,flags,begin_count,end_count,stop_count,frames,samples;
static unsigned protocol_error,done,ack_lost,read_calls;
static uint32_t mode_before,output_before,cr1_before;
static unsigned long long ns,previous;
static FILE *wave;static const char *wave_path;static unsigned opens,check_next,check_data,check_reads,check_acks,finishes;
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
 if(tx[0]==NES_ROM_STATUS||tx[0]==0x6a)return;
 /* Sticky059 SPI faults ignore commands until base/common reset. */
 if(protocol_error)return;
 if(tx[0]>=0x66) {
  switch(tx[0]) {
   case 0x66:assert(flags==2&&offset==0);flags=0x22;check_next=0;break;
   case 0x67:assert(flags==0x22&&offset==check_next);check_reads++;check_data=loaded[check_next];flags=0x62;
    if(fault==RB_DATA&&check_next==7)check_data^=1;
    if(fault==RB_TIMEOUT&&check_next==7)flags=0x23;
    break;
   case 0x68:assert(flags==0x62&&offset==check_next&&tx[4]==check_data);check_next++;check_acks++;flags=0x22;
    if(fault==RB_ACK_LOST&&check_next==8)protocol_error=8;
    break;
   case 0x69:assert(flags==0x22&&check_next==total&&offset==total&&closes==2);finishes++;flags=0x82;break;
   default:assert(0);
  }
  return;
 }
 assert(!protocol_error);
 if(tx[0]==NES_ROM_BEGIN){assert(!count&&!flags);total=tx[4]?98304:81920;flags=1;begin_count++;return;}
 assert(offset==count);
 switch(tx[0]) {
  case NES_ROM_DATA:
   assert(flags==1 && count<total);loaded[count++]=tx[4];flags=count==total?0:1;
   if(fault==STICKY && count==1)protocol_error=2;
   break;
  case NES_ROM_END:assert(count==total&&!flags);end_count++;flags=2;break;
  case NES_ROM_STOP:stop_count++;if(fault!=STOP_FAILED){flags=0;count=0;}break;
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
    reply[1]=fault==SPI_ID?0:0x59;
    reply[2]=(uint8_t)(flags|(protocol_error?8:0));reply[3]=(uint8_t)protocol_error;
    reply[4]=(uint8_t)(count>>16);reply[5]=(uint8_t)(count>>8);reply[6]=(uint8_t)count;
    if(fault==LOST_ACK && tx[0]==NES_ROM_STATUS && count==1 && !ack_lost){reply[1]=0;ack_lost=1;}
    if(tx[0]==0x6a) {
     unsigned tag=check_next+(fault==RB_TAG&&check_next==7);
     reply[3]=(uint8_t)check_data;reply[4]=(uint8_t)(tag>>16);reply[5]=(uint8_t)(tag>>8);reply[6]=(uint8_t)tag;
     reply[7]=(uint8_t)(protocol_error<<4);
     if(fault==RB_STATUS&&check_next==7)reply[2]|=0x80;
    }
    if(fault==FINISH_LOST&&finishes)reply[1]=0;
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
 opens++;if(opens==2)pass=2;
 if(wave_path&&opens==2){wave=fopen(wave_path,"w");assert(wave);previous=ns;}
 f->fsize=length+(fault==THIRD_SIZE&&pass==2);f->pos=0;
 return fault==OPEN||(fault==THIRD_OPEN&&pass==2)?1:FR_OK;
}
FRESULT f_read(FIL *f,void *dest,UINT wanted,UINT *got) {
 assert(!irq&&reset_held);read_calls++;
 if((fault==READ_FIRST&&!pass&&f->pos==272)||(fault==READ_SECOND&&pass==1&&f->pos==272)){*got=0;return 1;}
 if(fault==THIRD_READ&&pass==2&&f->pos==272){*got=0;return 1;}
 *got=wanted;if(f->pos+*got>length)*got=length-f->pos;
 if((fault==SHORT_FIRST&&!pass&&f->pos==272)||(fault==SHORT_SECOND&&pass==1&&f->pos==272))(*got)--;
 if(fault==THIRD_SHORT&&pass==2&&f->pos==272)(*got)--;
 memcpy(dest,rom+f->pos,*got);
 if(fault==THIRD_HEADER&&pass==2&&f->pos==0)((uint8_t *)dest)[6]^=1;
 if((fault==THIRD_CHANGED||fault==THIRD_CRC)&&pass==2&&f->pos==16){
  ((uint8_t *)dest)[0]^=1;if(fault==THIRD_CRC)loaded[0]^=1;
 }
 if(fault==CHANGE_HEADER && pass && f->pos==0)((uint8_t *)dest)[6]^=1;
 if(fault==CHANGE_DATA && pass && f->pos==16)((uint8_t *)dest)[0]^=1;
 f->pos+=*got;return FR_OK;
}
FRESULT f_lseek(FIL *f,uint32_t offset){assert(!irq&&offset==0);f->pos=offset;pass++;return fault==SEEK?1:FR_OK;}
FRESULT f_close(FIL *f){(void)f;assert(!irq);closes++;return fault==CLOSE||(fault==THIRD_CLOSE&&closes==2)?1:FR_OK;}
FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){(void)f;(void)p;(void)n;(void)got;assert(0);return 1;}
static void initialize(enum fault f,unsigned enabled) {
 fault=f;irq=enabled;reset_held=configs=closes=pass=0;
 bits=count=total=flags=begin_count=end_count=stop_count=frames=samples=0;
 opens=check_next=check_data=check_reads=check_acks=finishes=0;protocol_error=ack_lost=read_calls=0;done=1;ns=previous=0;
 length=original_length;mock_a=(MockGPIO){0,16,0};
 mock_b=(MockGPIO){0x5a5a5a5a,0xdeadbeef,0};mock_spi=(MockSPI){SPI_SR_TXE,0x147};
 mode_before=mock_b.MODER;output_before=mock_b.ODR;cr1_before=mock_spi.CR1;
 memset(loaded,0,sizeof(loaded));
}

static void test(enum fault f,enum nes_mcu_load_result expected,unsigned enabled) {
 initialize(f,enabled);struct nes_sd_readback_report report;struct nes_mcu_load_report *r=&report.load;
 if(f==HEADER)rom[6]^=4;
 if(f==CONTENT)rom[32]^=1;
 bool safe=nes_sd_readback_probe("fixture","approved-test-image",&report);
 if(f==HEADER)rom[6]^=4;
 if(f==CONTENT)rom[32]^=1;
 bool recovery_failure=f>=BASE_CONFIG&&f<=BASE_TOKEN;
 assert(safe==!recovery_failure);
 assert(r->result==expected&&reset_held&&irq==(recovery_failure?0:enabled));
 assert(configs==0||configs==2);
 assert(r->recovery_attempted==(configs==2)&&r->base_restored==(configs==2&&!recovery_failure));
 assert(mock_b.MODER==mode_before&&mock_b.ODR==output_before&&mock_spi.CR1==cr1_before);
 bool success=f==NONE||recovery_failure||f==STOP_FAILED;
 assert(report.verified==success);
 if(success) {
  assert(r->end_accepted&&end_count==1&&finishes==1&&closes==2);
  assert(report.verify.compared==length-16&&check_reads==length-16&&check_acks==length-16);
  assert(r->acknowledged_bytes==length-16&&!memcmp(loaded,rom+16,length-16));
  assert(r->stop_ok==(f!=STOP_FAILED)&&stop_count==1);
 } else assert(finishes==(f==FINISH_LOST?1u:0u));
 if(f==THIRD_CRC||f==THIRD_CLOSE)assert(report.verify.compared==length-17&&check_acks==length-17);
 if(f==THIRD_READ||f==THIRD_SHORT)assert(report.verify.compared==256&&check_acks==256&&report.verify.stop_ok);
 if(f==RB_DATA)assert(report.verify.error==NES_VERIFY_DATA&&check_acks==7);
 if(f==RB_TAG)assert(report.verify.error==NES_VERIFY_TAG&&check_acks==7);
 if(f==RB_TIMEOUT)assert(report.verify.error==NES_VERIFY_TIMEOUT&&check_acks==7);
 if(f==RB_ACK_LOST)assert(check_acks==8&&!r->stop_ok);
 if(f==FINISH_LOST)assert(!report.verified&&!r->stop_ok);
 if(f==LOST_ACK)assert(r->acknowledged_bytes==0&&ack_lost&&stop_count==1);
 if(f==STICKY)assert(r->acknowledged_bytes==0&&!r->stop_ok&&!stop_count);
 printf("PASS SD lifecycle fault=%u chr=%u irq=%u loaded=%lu compared=%lu verified=%u stop=%u safe=%u reads=%u closes=%u\n",
  f,r->chr_32k,enabled,(unsigned long)r->acknowledged_bytes,(unsigned long)report.verify.compared,report.verified,r->stop_ok,safe,read_calls,closes);
}
int main(int argc,char **argv) {
 setvbuf(stdout,0,_IONBF,0);
 assert(argc==5);
 for(unsigned c=1;c<=2;c++) {
  FILE *input=fopen(argv[c],"rb");assert(input);original_length=(unsigned)fread(rom,1,sizeof(rom),input);fclose(input);
  assert(original_length==(c==1?81936u:98320u));
  test(NONE,NES_MCU_LOAD_OK,1);test(NONE,NES_MCU_LOAD_OK,0);
 }
 const enum nes_mcu_load_result results[]={NES_MCU_LOAD_OK,NES_MCU_LOAD_OPEN,NES_MCU_LOAD_HEADER,
  NES_MCU_LOAD_CONTENT,NES_MCU_LOAD_READ,NES_MCU_LOAD_READ,NES_MCU_LOAD_SEEK,NES_MCU_LOAD_CONFIG,
  NES_MCU_LOAD_CONFIG,NES_MCU_LOAD_OWNERSHIP,NES_MCU_LOAD_ID,NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,
  NES_MCU_LOAD_READ,NES_MCU_LOAD_READ,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CLOSE,
  NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_OK,NES_MCU_LOAD_SPI,
  NES_MCU_LOAD_OPEN,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_READ,NES_MCU_LOAD_READ,
  NES_MCU_LOAD_SPI,NES_MCU_LOAD_CHANGED,NES_MCU_LOAD_CLOSE,NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,
  NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,NES_MCU_LOAD_SPI,NES_MCU_LOAD_OK};
 for(unsigned f=OPEN;f<=STOP_FAILED;f++)test((enum fault)f,results[f],1);
 unsigned rejected=0;
 for(unsigned i=0;i<16;i++) {
  initialize(NONE,1);rom[i]^=0x80;struct nes_sd_readback_report r;
  assert(nes_sd_readback_probe("fixture","approved-test-image",&r));
  assert(r.load.result==NES_MCU_LOAD_HEADER&&!configs&&irq==1);rom[i]^=0x80;rejected++;
 }
 for(int delta=-1;delta<=1;delta+=2) {
  initialize(NONE,1);length=(unsigned)((int)length+delta);struct nes_sd_readback_report r;
  assert(nes_sd_readback_probe("fixture","approved-test-image",&r));
  assert(r.load.result==NES_MCU_LOAD_HEADER&&!configs);rejected++;
 }
 wave_path=argv[3];test(THIRD_READ,NES_MCU_LOAD_READ,1);fclose(wave);wave=0;
 wave_path=0;wave=fopen(argv[4],"w");assert(wave);
 test(READ_SECOND,NES_MCU_LOAD_READ,1);fclose(wave);wave=0;
 printf("PASS SD READBACK lifecycle=41 header_rejections=%u no_start=1 no_sd_writes=1\n",rejected);
 return 0;
}
