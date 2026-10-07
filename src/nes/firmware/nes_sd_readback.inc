/* SPDX-License-Identifier: MIT */
/* Append after unchanged044+056; reuse ownership, CRC and platform helpers. */
#include "nes_sd_readback.h"
static bool sd_query(const struct nes_rom_spi_io *io,struct nes_rom_spi_status *s) {
 uint8_t tx[8],rx[8];nes_rom_spi_frame(tx,NES_ROM_STATUS,0,0);
 if(!nes_rom_spi_transfer(io,tx,rx)||rx[1]!=0x59||(rx[4]&0xfe)||rx[3]||rx[7]||(rx[2]&0x18))return false;
 s->flags=rx[2];s->count=((uint32_t)rx[4]<<16)|((uint32_t)rx[5]<<8)|rx[6];
 s->protocol_error=rx[3];s->loader_error=rx[7];return s->count<=0x18000;
}
static bool sd_command(const struct nes_rom_spi_io *io,uint8_t op,uint32_t offset,uint8_t arg,struct nes_rom_spi_status *s) {
 if(op!=NES_ROM_BEGIN&&op!=NES_ROM_DATA&&op!=NES_ROM_END&&op!=NES_ROM_STOP)return false;
 uint8_t tx[8],rx[8];nes_rom_spi_frame(tx,op,offset,arg);
 if(!nes_rom_spi_transfer(io,tx,rx)||!sd_query(io,s))return false;
 switch(op) {
  case NES_ROM_BEGIN:return s->flags==1&&s->count==0;
  case NES_ROM_DATA:return s->count==offset+1&&(s->flags==0||s->flags==1);
  case NES_ROM_END:return s->flags==2&&s->count==offset;
  case NES_ROM_STOP:return s->flags==0&&s->count==0;
  default:return false;
 }
}
struct sd_source_context {
 FIL *file;struct nes_mcu_load_report *report;bool *opened;
 uint32_t total,expected_crc,crc,next;uint8_t *buffer;
};
static bool sd_source(void *opaque,uint32_t address,uint8_t *data) {
 struct sd_source_context *c=opaque;struct nes_mcu_load_report *r=c->report;
 if(address!=c->next||address>=c->total||!*c->opened){r->result=NES_MCU_LOAD_CHANGED;return false;}
 if(!(address&255u)) {
  if(!load_read(c->file,c->buffer,256,r))return false;
  c->crc=load_crc(c->crc,c->buffer,256);
 }
 if(address==c->total-1) {
  if(f_size(c->file)!=c->total+16u||(c->crc^0xffffffffu)!=c->expected_crc){r->result=NES_MCU_LOAD_CHANGED;return false;}
  r->file_result=f_close(c->file);*c->opened=false;
  if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_CLOSE;return false;}
 }
 *data=c->buffer[address&255u];c->next++;return true;
}

bool nes_sd_readback_probe(const char *path,const char *image,struct nes_sd_readback_report *report) {
 struct nes_mcu_load_report *r=report?&report->load:0;
 const struct nes_rom_spi_io io={0,load_select,load_clock,load_mosi,load_miso,wait_us};
 struct nes_rom_spi_status status={0};
 FIL file;
 uint8_t header[16],buffer[256];
 uint32_t total=0,expected_crc=0,crc=0xffffffffu;
 bool opened=false,changed_fpga=false,begin_sent=false;
 if(!r || !path || !image || !*path || !*image || gpio_owned)return false;
 memset(report,0,sizeof(*report));
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
 if(!sd_query(&io,&status) || status.flags || status.count) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 begin_sent=true; /* Completion may be unknown on a failed response. */
 if(!sd_command(&io,NES_ROM_BEGIN,0,r->chr_32k,&status)) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 if(!load_read(&file,buffer,16,r))goto cleanup;
 if(memcmp(buffer,header,16)){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
 crc=load_crc(0xffffffffu,buffer,16);
 for(uint32_t offset=0;offset<total;offset+=sizeof(buffer)) {
  if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
  crc=load_crc(crc,buffer,sizeof(buffer));
  for(unsigned i=0;i<sizeof(buffer);i++) {
   if(!sd_command(&io,NES_ROM_DATA,offset+i,buffer[i],&status)) {
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
 if(!sd_command(&io,NES_ROM_END,total,0,&status)) {
  r->result=NES_MCU_LOAD_SPI;goto cleanup;
 }
 r->end_accepted=true;
 /* Third read is the approved comparison source; FINISH must not precede
  * full CRC and successful close. The last callback closes before returning. */
 r->file_result=f_open(&file,path,FA_READ);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_OPEN;goto cleanup;}
 opened=true;
 if(!load_read(&file,buffer,16,r))goto cleanup;
 if(memcmp(buffer,header,16)||f_size(&file)!=total+16u){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
 struct sd_source_context ctx={&file,r,&opened,total,expected_crc,load_crc(0xffffffffu,buffer,16),0,buffer};
 if(!nes_rom_verify(&io,total,sd_source,&ctx,&report->verify)) {
  if(r->result==NES_MCU_LOAD_OK)r->result=NES_MCU_LOAD_SPI;
  goto cleanup;
 }
 report->verified=true;
 /* No START: this entry only verifies and restores the base/menu path. */
cleanup:
 if(opened) {
  unsigned close_result=f_close(&file);
  if(r->result==NES_MCU_LOAD_OK && close_result!=FR_OK) {
   r->file_result=close_result;r->result=NES_MCU_LOAD_CLOSE;
  }
 }
 if(report->verify.stop_ok)r->stop_ok=true;
 if(gpio_owned && begin_sent && !r->stop_ok) {
  /* Query current count after an uncertain DATA ack; never resend DATA.
   * If the protocol is faulted, base reconfiguration is the recovery path. */
  if(sd_query(&io,&status) && !(status.flags&4))
   r->stop_ok=sd_command(&io,NES_ROM_STOP,status.count,0,&status);
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
