/* SPDX-License-Identifier: MIT */
/* Inserted before sdn_read, after original command helpers. Single-block
 * buffered reads only; no offload, automatic reinitialization or retry. */
static void nes_diag_sd_error(enum nes_diag_error error){nes_diag_sd_fault=true;nes_diag_fail(error);}
void nes_diag_sd_reset(void){nes_diag_sd_fault=false;}
bool nes_diag_sd_failed(void){return nes_diag_sd_fault;}
static bool nes_diag_sd_response(unsigned command) {
 uint8_t crc=0;
 for(unsigned n=0;n<5;n++)crc=crc7update(crc,rsp[n]);
 uint32_t status=((uint32_t)rsp[1]<<24)|((uint32_t)rsp[2]<<16)|((uint32_t)rsp[3]<<8)|rsp[4];
 return rsp[0]==command && rsp[5]==(uint8_t)((crc<<1)|1) && !(status&0xfdffe008u);
}
static DRESULT nes_diag_sd_read(BYTE drv,BYTE *buffer,DWORD sector,UINT count) {
 if(drv>=MAX_CARDS||!buffer||!count||count>128u||sector>UINT32_MAX-(count-1u)||(!ccs&&sector+count-1u>0x7fffffu))return RES_PARERR;
 if(nes_diag_sd_fault||disk_state!=DISK_OK||!SDCARD_DETECT){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_NOTRDY;}
 if(sd_offload||ff_sd_offload){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_ERROR;}
 if(during_blocktrans!=TRANS_NONE){
  int stopped=cmd_fast(STOP_TRANSMISSION,0,0x61,NULL,rsp);
  during_blocktrans=TRANS_NONE;
  if(stopped!=6||nes_diag_sd_fault||!nes_diag_sd_response(STOP_TRANSMISSION)){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return RES_ERROR;}
 }
 for(UINT n=0;n<count;n++){
  uint32_t address=sector+n;
  if(address<sector||(!ccs&&address>0x7fffffu))return RES_PARERR;
  if(!ccs)address<<=9;
  int result=cmd_fast(READ_SINGLE_BLOCK,address,0,buffer+n*512u,rsp);
  if(result!=6||nes_diag_sd_fault||!nes_diag_sd_response(READ_SINGLE_BLOCK)){
   nes_diag_sd_error(result==CRC_ERROR?NES_DIAG_SD_CRC:NES_DIAG_SD_RESPONSE);
   disk_state=DISK_ERROR;return RES_ERROR;
  }
 }
 return RES_OK;
}
