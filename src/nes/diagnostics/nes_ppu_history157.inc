/* SPDX-License-Identifier: MIT */
/* Optional stopped history; invalid replies must not block STOP/base/menu. */
static bool history157(const struct nes_rom_spi_io *io){
 uint8_t tx[8]={0x77},rx[8]={0};
 nes_run136.history_valid=0;
 if(!nes_rom_spi_transfer(io,tx,rx))return false;
 unsigned flags=rx[2],count=rx[3],next=rx[4];
 if(rx[1]!=0xe0||(flags&~3u)||count>16||next>15||rx[5]!=1||rx[6]!=96||rx[7]!=1||
    (count<16&&next!=count)||(count&&!(flags&1)))return false;
 nes_run136.history_flags=flags;nes_run136.history_count=count;
 unsigned first=count==16?next:0;
 for(unsigned i=0;i<count;i++)for(unsigned half=0;half<2;half++){
  tx[0]=0xa0|(((first+i)&15)<<1)|half;
  if(!nes_rom_spi_transfer(io,tx,rx)||rx[1]!=0xe0)return false;
  for(unsigned j=0;j<6;j++)nes_run136.history[i][half*6+j]=rx[j+2];
 }
 nes_run136.history_valid=1;return true;
}
static int history157_format(char *text,size_t size,int n){
 if(n<=0||(size_t)n>=size)return -1;
 int used=snprintf(text+n,size-(size_t)n,
  "ppu_history_valid=%u\nppu_history_count=%u\nppu_history_flags=%u\nppu_history_kind=LAST16_NES_CLOCKS_INCLUDING_FAULT\n",
  nes_run136.history_valid,nes_run136.history_count,nes_run136.history_flags);
 if(used<0||(size_t)used>=size-(size_t)n)return -1;
 n+=used;
 if(nes_run136.history_valid)for(unsigned i=0;i<nes_run136.history_count;i++){
  const uint8_t *h=nes_run136.history[i];
  used=snprintf(text+n,size-(size_t)n,"ppu_history_%02u=%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x\n",i,
   h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7],h[8],h[9],h[10],h[11]);
  if(used<0||(size_t)used>=size-(size_t)n)return -1;
  n+=used;
 }
 return n;
}
