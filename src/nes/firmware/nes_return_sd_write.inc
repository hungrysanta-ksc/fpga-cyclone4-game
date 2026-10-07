/* SPDX-License-Identifier: MIT */
/* Only the late PREPARED log window permits writes. No uncertain retry. */
static DRESULT nes_return_sd_write(BYTE drv,const BYTE *buffer,DWORD sector,UINT count) {
 if(drv>=MAX_CARDS||!buffer||!count||count>128u||sector>UINT32_MAX-(count-1u)||(!ccs&&sector+count-1u>0x7fffffu))return RES_PARERR;
 if(!nes_return_log_allowed())return RES_WRPRT;
 if(nes_return_failed())return RES_NOTRDY;
 if(nes_diag_sd_fault||disk_state!=DISK_OK||!SDCARD_DETECT){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_NOTRDY;}
 if(SDCARD_WP)return RES_WRPRT;
 if(sd_offload||ff_sd_offload||during_blocktrans!=TRANS_NONE){nes_diag_sd_error(NES_DIAG_SD_STATE);return RES_ERROR;}
 for(UINT n=0;n<count;n++){
  uint32_t address=sector+n;if(!ccs)address<<=9;
  int result=cmd_fast(24,address,0,NULL,rsp);
  if(result!=6||!nes_diag_sd_response(24)){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return RES_ERROR;}
  send_datablock((uint8_t *)buffer+n*512u);
  if(nes_diag_sd_fault)return RES_ERROR;
 }
 return RES_OK;
}
