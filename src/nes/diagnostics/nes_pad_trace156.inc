/* SPDX-License-Identifier: MIT */
/* Entire ring is immutable after STOP; invalid auxiliary data cannot block return. */
static bool pad156(const struct nes_rom_spi_io *io){
 uint8_t tx[8]={0x76},rx[8]={0};
 nes_run136.pad_valid=0;
 if(!nes_rom_spi_transfer(io,tx,rx))return false;
 uint16_t total=((uint16_t)rx[3]<<8)|rx[4];
 unsigned count=rx[5],next=rx[6];
 if(rx[1]!=0xdf||(rx[2]&0xfcu)||rx[7]!=1||count>16||next>15||
    total<count||(count<16&&(next!=count||total!=count))||
    (count&&!(rx[2]&1)))return false;
 nes_run136.pad_flags=rx[2];nes_run136.pad_total=total;nes_run136.pad_count=count;
 unsigned first=count==16?next:0;
 for(unsigned i=0;i<count;i++){
  tx[0]=0x80|((first+i)&15);
  if(!nes_rom_spi_transfer(io,tx,rx)||rx[1]!=0xdf||rx[7]!=1)return false;
  nes_run136.pad_buttons[i]=rx[2];
  nes_run136.pad_ticks[i]=((uint32_t)rx[3]<<24)|((uint32_t)rx[4]<<16)|((uint32_t)rx[5]<<8)|rx[6];
 }
 nes_run136.pad_valid=1;return true;
}
