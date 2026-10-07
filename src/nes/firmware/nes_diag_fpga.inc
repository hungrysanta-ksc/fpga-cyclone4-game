/* SPDX-License-Identifier: MIT */
/* Appended to pinned fpga.c; legacy programmer stays byte-for-byte intact. */
#include "nes_diag_runtime.h"
struct nes_diag_input {FIL file;uint8_t bytes[256];UINT used,filled;uint32_t consumed;bool eof;};
static int nes_diag_byte(struct nes_diag_input *in) {
 if(in->used==in->filled){
  if(in->eof)return -1;
  UINT got=0;FRESULT res=f_read(&in->file,in->bytes,sizeof(in->bytes),&got);
  if(res!=FR_OK){nes_diag_fail(NES_DIAG_FPGA_READ);return -2;}
  in->used=0;in->filled=got;in->eof=got<sizeof(in->bytes);
  if(!got)return -1;
 }
 in->consumed++;return in->bytes[in->used++];
}
static bool nes_diag_pin_wait(unsigned pin,bool level,enum nes_diag_error error) {
 struct nes_diag_wait wait=nes_diag_wait_start(100,50000000u);
 for(;;){
  bool value=pin==0?!!BITBAND(FPGA_PROGBREG->GPIO_I,FPGA_PROGBBIT):pin==1?!!fpga_get_initb():!!fpga_get_done();
  if(value==level)return true;
  if(!nes_diag_wait_step(&wait)){nes_diag_fail(error);return false;}
 }
}
bool nes_diag_fpga_pgm(const uint8_t *filename) {
 struct nes_diag_input in={0};bool ok=false,masked=false;
 uint32_t produced=0,remaining=0;int data=0;
 FRESULT res=f_open(&in.file,(const char *)filename,FA_READ);
 if(res!=FR_OK){file_res=res;nes_diag_fail(NES_DIAG_FPGA_OPEN);return false;}
 if(!f_size(&in.file)||f_size(&in.file)>1048576u){nes_diag_fail(NES_DIAG_FPGA_LIMIT);goto close;}
 fpga_init();fpga_config=0;gbc_spi_pacing=0;
 fpga_set_prog_b(0);
 if(!nes_diag_pin_wait(0,false,NES_DIAG_FPGA_PROG))goto close;
 fpga_set_prog_b(1);
 if(!nes_diag_pin_wait(1,true,NES_DIAG_FPGA_INIT)||!nes_diag_pin_wait(2,false,NES_DIAG_FPGA_DONE))goto close;
 FPGA_DIN_MASK();masked=true;
 struct nes_diag_wait stream=nes_diag_wait_start(3000,2097152u);
 for(;;){
  if(!remaining){
   int token=nes_diag_byte(&in);
   if(token==-1){ok=produced!=0&&in.consumed==f_size(&in.file);if(!ok)nes_diag_fail(NES_DIAG_FPGA_FORMAT);break;}
   if(token<0)break;
   data=token;remaining=1;
   if(token==RLE_ESC||token==RLE_RUN||token==RLE_RUNLONG){
    data=nes_diag_byte(&in);if(data<0){nes_diag_fail(NES_DIAG_FPGA_FORMAT);break;}
    if(token!=RLE_ESC){
     int lo=nes_diag_byte(&in),hi=token==RLE_RUNLONG?nes_diag_byte(&in):0;
     if(lo<0||hi<0||!(lo|(hi<<8))){nes_diag_fail(NES_DIAG_FPGA_FORMAT);break;}
     remaining=(uint32_t)(lo|(hi<<8));
    }
   }
  }
  if(!nes_diag_wait_step(&stream)){nes_diag_fail(NES_DIAG_FPGA_LIMIT);break;}
  FPGA_SEND_BYTE_SERIAL((uint8_t)data);remaining--;produced++;
 }
 FPGA_DIN_UNMASK();masked=false;
 if(ok){
  CCLK();CCLK();CCLK();
  ok=nes_diag_pin_wait(2,true,NES_DIAG_FPGA_DONE);
 }
close:
 if(masked)FPGA_DIN_UNMASK();
 res=f_close(&in.file);
 if(res!=FR_OK){nes_diag_fail(NES_DIAG_FPGA_CLOSE);ok=false;}
 file_res=ok?FR_OK:FR_DISK_ERR;
 if(ok){fpga_config=filename;fpga_postinit();}
 return ok;
}
