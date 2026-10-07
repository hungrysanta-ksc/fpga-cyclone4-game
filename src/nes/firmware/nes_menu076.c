/* SPDX-License-Identifier: MIT */
/* One observed menu profile, not a general ROM parser or authentication. */
#include <string.h>
#include "config.h"
#include "fileops.h"
#include "fpga_spi.h"
#include "nes_menu_return.h"
#include "nes_menu076.h"
uint32_t nes_menu_crc076(uint32_t crc,const uint8_t *data,unsigned size){
 while(size--){crc^=*data++;for(unsigned n=0;n<8;n++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);}
 return crc;
}
bool nes_menu_approved076(const snes_romprops_t *p){
 return !p->error&&p->header_address==0xffb0u&&!p->offset&&!p->load_address&&
  p->header.map==0x31&&p->header.carttype==0x55&&p->header.romsize==6&&
  p->header.ramsize==3&&!p->header.expramsize&&p->header.vect_reset==0xff02&&
  p->romsize_bytes==NES_MENU076_SIZE&&p->ramsize_bytes==8192&&p->sramsize_bytes==8192&&
  !p->srambase&&!p->mapper_id&&!p->fpga_conf&&p->fpga_features==FEAT_SRTC&&
  !p->has_dspx&&!p->has_combo&&!p->has_st0010&&!p->has_st0011&&!p->has_st0018&&
  !p->has_msu1&&!p->has_cx4&&!p->has_obc1&&!p->has_gsu&&!p->has_sa1&&!p->has_sdd1&&!p->has_spc7110;
}
bool nes_menu_classify076(snes_romprops_t *p){
 uint8_t data[256],reset_opcode=0;uint32_t crc=0xffffffffu;
 memset(p,0,sizeof(*p));
 if(!nes_diag_active()||nes_return_failed())return false;
 if(f_size(&file_handle)!=NES_MENU076_SIZE)goto fail;
 file_res=f_lseek(&file_handle,0);
 if(file_res!=FR_OK||file_handle.fptr!=0||nes_return_failed())goto fail;
 for(uint32_t at=0;at<NES_MENU076_SIZE;at+=sizeof(data)){
  UINT got=0;
  if(!nes_return_io_step())goto fail;
  file_res=f_read(&file_handle,data,sizeof(data),&got);
  if(file_res!=FR_OK||got!=sizeof(data)||nes_return_failed())goto fail;
  crc=nes_menu_crc076(crc,data,got);
  if(at==0xff00){memcpy(&p->header,data+0xb0,sizeof(p->header));reset_opcode=data[2];}
 }
 if(f_size(&file_handle)!=NES_MENU076_SIZE||(crc^0xffffffffu)!=NES_MENU076_CRC||reset_opcode!=0x78)goto fail;
 p->header_address=0xffb0;p->romsize_bytes=NES_MENU076_SIZE;
 p->ramsize_bytes=p->sramsize_bytes=8192;p->expramsize_bytes=1024;p->fpga_features=FEAT_SRTC;
 p->region=(p->header.destcode<=1||p->header.destcode>=13)?0:1;
 if(!nes_menu_approved076(p))goto fail;
 return true;
fail:
 memset(p,0,sizeof(*p));nes_return_fail(NES_DIAG_MENU);return false;
}
