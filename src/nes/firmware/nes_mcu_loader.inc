/* SPDX-License-Identifier: MIT */
/* Append to materialized044, sharing its existing static ownership helpers.
 * No edits to the frozen044 source, SPI setup or legacy H1 entry point. */
#include "nes_rom_spi.h"
#include "nes_mcu_loader.h"

static void load_select(void *ctx,bool active) {
 (void)ctx;
 if(active)CLEAR_BIT(FPGA_SSREG,FPGA_SSBIT);
 else SET_BIT(FPGA_SSREG,FPGA_SSBIT);
}
static void load_clock(void *ctx,bool high) {
 (void)ctx;
 if(high)SET_BIT(GPIOB,3);else CLEAR_BIT(GPIOB,3);
}
static void load_mosi(void *ctx,bool high) {
 (void)ctx;
 if(high)SET_BIT(GPIOB,5);else CLEAR_BIT(GPIOB,5);
}
static bool load_miso(void *ctx) {
 (void)ctx;return ((GPIOB->IDR>>4)&1u)!=0;
}
static uint32_t load_crc(uint32_t crc,const uint8_t *data,unsigned size) {
 while(size--) {
  crc^=*data++;
  for(unsigned b=0;b<8;b++)crc=(crc>>1)^((crc&1u)?0xedb88320u:0);
 }
 return crc;
}
static bool load_read(FIL *file,uint8_t *buf,UINT size,struct nes_mcu_load_report *r) {
 UINT got=0;
 r->file_result=f_read(file,buf,size,&got);
 if(r->file_result!=FR_OK || got!=size){r->result=NES_MCU_LOAD_READ;return false;}
 return true;
}

bool nes_mcu_load_probe(const char *path,const char *image,struct nes_mcu_load_report *r) {
 const struct nes_rom_spi_io io={0,load_select,load_clock,load_mosi,load_miso,wait_us};
 struct nes_rom_spi_status status={0};
 FIL file;
 uint8_t header[16],buffer[256];
 uint32_t total=0,expected_crc=0,crc=0xffffffffu;
 bool opened=false,changed_fpga=false,begin_sent=false;
 if(!r || !path || !image || !*path || !*image || gpio_owned)return false;
 memset(r,0,sizeof(*r));
 bool usb_irq_enabled=NVIC_GetEnableIRQ(OTG_FS_IRQn)!=0;
 NVIC_DisableIRQ(OTG_FS_IRQn);
 snes_reset(1);
 r->file_result=f_open(&file,path,FA_READ);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_OPEN;goto cleanup;}
 opened=true;
 if(!load_read(&file,header,sizeof(header),r))goto cleanup;
 /* Exact iNES1 diagnostic geometry: mapper4, no trainer/battery/NES2,
  * no extra flags or trailing data. CRC32 identifies the two original public
  * fixtures against accidental changes; it is not a security signature. */
 if(memcmp(header,"NES\032",4) || header[4]!=4 ||
    (header[5]!=2 && header[5]!=4) || header[6]!=0x40 || header[7]!=0) {
  r->result=NES_MCU_LOAD_HEADER;goto cleanup;
 }
 for(unsigned i=8;i<16;i++)if(header[i]){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}
 r->chr_32k=header[5]==4;
 total=65536u+(r->chr_32k?32768u:16384u);
 expected_crc=r->chr_32k?0x7a5a55c1u:0x5a226793u;
 if(f_size(&file)!=total+16u){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}
 crc=load_crc(crc,header,16);
 for(uint32_t offset=0;offset<total;offset+=sizeof(buffer)) {
  if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
  crc=load_crc(crc,buffer,sizeof(buffer));
 }
 if((crc^0xffffffffu)!=expected_crc){r->result=NES_MCU_LOAD_CONTENT;goto cleanup;}
 r->file_result=f_lseek(&file,0);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_SEEK;goto cleanup;}

 /* fpga_pgm uses its global handle; our independent read-only FIL remains
  * open. It may enter the existing platform panic on hardware failures. */
 changed_fpga=true;
 fpga_pgm((uint8_t *)image);
 if(!configured(image)){r->result=NES_MCU_LOAD_CONFIG;goto cleanup;}
 if(!slow_begin()){r->result=NES_MCU_LOAD_OWNERSHIP;goto cleanup;}
 for(unsigned i=0;i<2;i++) {
  uint8_t tx[2]={(uint8_t)(0xf0+i),0},rx[2]={0};
  if(!slow_transaction(0,tx,rx,2) || rx[1]!=(i?0x44:0xa5)) {
   r->result=NES_MCU_LOAD_ID;goto cleanup;
  }
 }
 if(!nes_rom_spi_query(&io,&status) || status.flags || status.count) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 begin_sent=true; /* Completion may be unknown on a failed response. */
 if(!nes_rom_spi_command(&io,NES_ROM_BEGIN,0,r->chr_32k,&status)) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 if(!load_read(&file,buffer,16,r))goto cleanup;
 if(memcmp(buffer,header,16)){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
 crc=load_crc(0xffffffffu,buffer,16);
 for(uint32_t offset=0;offset<total;offset+=sizeof(buffer)) {
  if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
  crc=load_crc(crc,buffer,sizeof(buffer));
  for(unsigned i=0;i<sizeof(buffer);i++) {
   if(!nes_rom_spi_command(&io,NES_ROM_DATA,offset+i,buffer[i],&status)) {
    r->result=NES_MCU_LOAD_SPI;goto cleanup;
   }
   r->acknowledged_bytes=offset+i+1;
  }
 }
 if(f_size(&file)!=total+16u || (crc^0xffffffffu)!=expected_crc) {
  r->result=NES_MCU_LOAD_CHANGED;goto cleanup;
 }
 /* Successful close is part of input validation; do not END after IO error. */
 r->file_result=f_close(&file);opened=false;
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_CLOSE;goto cleanup;}
 if(!nes_rom_spi_command(&io,NES_ROM_END,total,0,&status)) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 r->end_accepted=true;
 /* Deliberately no START: geometry binding/readback/board clocks/consumer
  * are still pending. END says length complete, not physical integrity. */
cleanup:
 if(opened) {
  unsigned close_result=f_close(&file);
  if(r->result==NES_MCU_LOAD_OK && close_result!=FR_OK) {
   r->file_result=close_result;r->result=NES_MCU_LOAD_CLOSE;
  }
 }
 if(gpio_owned && begin_sent) {
  /* Query current count after an uncertain DATA ack; never resend DATA.
   * If the protocol is faulted, base reconfiguration is the recovery path. */
  if(nes_rom_spi_query(&io,&status) && !(status.flags&4))
   r->stop_ok=nes_rom_spi_command(&io,NES_ROM_STOP,status.count,0,&status);
 }
 slow_end();
 if(changed_fpga) {
  r->recovery_attempted=true;
  fpga_pgm((uint8_t *)FPGA_BASE);
  if(!configured((const char *)FPGA_BASE) || (SPI1->SR&SPI_SR_BSY) ||
     !(SPI1->SR&SPI_SR_TXE) || fpga_test()!=FPGA_TEST_TOKEN)return false;
  r->base_restored=true;
 }
 if(usb_irq_enabled)NVIC_EnableIRQ(OTG_FS_IRQn);
 return true;
}
