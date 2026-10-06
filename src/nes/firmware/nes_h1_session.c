/* SPDX-License-Identifier: MIT */
#include "nes_h1_session.h"
static bool read_byte(const struct nes_h1_io *io,uint8_t command,uint8_t *value) {
 uint8_t tx[2]={command,0},rx[2]={0,0};
 if(!io->transaction(io->context,tx,rx,2))return false;
 *value=rx[1];return true;
}
static bool command(const struct nes_h1_io *io,uint8_t code) {
 uint8_t tx[3]={code,0xa5,0x5a},rx[3]={0,0,0};
 return io->transaction(io->context,tx,rx,3);
}
static bool generation(const struct nes_h1_io *io,uint16_t *value) {
 uint8_t low,high;
 if(!read_byte(io,0xf3,&low)||!read_byte(io,0xf4,&high))return false;
 *value=(uint16_t)((uint16_t)high<<8)|low;return true;
}
enum nes_h1_result nes_h1_stop(const struct nes_h1_io *io) {
 uint8_t status;
 io->reset(io->context,true);
 if(!command(io,0xe9)||!read_byte(io,0xf2,&status))return NES_H1_IO_ERROR;
 return status==2?NES_H1_OK:NES_H1_STATE_ERROR;
}
enum nes_h1_result nes_h1_start(const struct nes_h1_io *io,uint16_t *epoch) {
 uint8_t id,status=0;uint16_t before,after;
 enum nes_h1_result failure=NES_H1_IO_ERROR;
 io->reset(io->context,true);
 if(!io->configure(io->context,"/sd2snes/fpga_nh1.bi3"))return NES_H1_IO_ERROR;
 /* Bounded identity wait allows the PLL/control release after configuration. */
 for(unsigned tries=0;tries<32;tries++) {
  if(read_byte(io,0xf0,&id)&&id==0xa5)break;
  if(tries==31)return NES_H1_ID_ERROR;
  io->delay_us(io->context,200);
 }
 if(!read_byte(io,0xf1,&id))return NES_H1_IO_ERROR;
 if(id!=0x34)return NES_H1_ID_ERROR;
 if(!read_byte(io,0xf2,&status)||!generation(io,&before))return NES_H1_IO_ERROR;
 if(status!=2)return NES_H1_STATE_ERROR;
 if(before==UINT16_MAX)return NES_H1_EPOCH_ERROR;
 if(!command(io,0xe8))goto failed;
 if(!read_byte(io,0xf2,&status)||!generation(io,&after))goto failed;
 if(status!=3){failure=NES_H1_STATE_ERROR;goto failed;}
 if(after!=(uint16_t)(before+1)){failure=NES_H1_EPOCH_ERROR;goto failed;}
 *epoch=after;io->reset(io->context,false);return NES_H1_OK;
failed:
 /* Best effort STOP while the CPU remains held in reset. Preserve first error. */
 (void)command(io,0xe9);
 return failure;
}
