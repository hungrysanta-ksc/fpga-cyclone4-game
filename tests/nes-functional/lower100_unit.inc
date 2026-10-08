/* SPDX-License-Identifier: MIT */
static void run_unit100(unsigned sc){
 nes_diag_begin();nes_return_reset();nes_return_io_begin();irq=0;reset_held=1;
 begin_lower100(sc<6?sc:0);unit100=sc;
 uint8_t in[257],out[257];for(unsigned i=0;i<257;i++)in[i]=(uint8_t)(i*37+11);
 memset(out,0xa5,sizeof(out));
 if(sc==0){
  sram_writeblock(in,0x123456,257);sram_readblock(out,0x123456,257);assert(!memcmp(in,out,257));
  sram_writelong(0x12345678,SRAM_SCRATCHPAD);assert(sram_readlong(SRAM_SCRATCHPAD)==0x12345678);
  sram_memset(0x123456,257,0x5a);sram_readblock(out,0x123456,257);for(unsigned i=0;i<257;i++)assert(out[i]==0x5a);
  assert(!nes_return_failed()&&cs100&&select100==deselect100);
 }
 if(sc>=1&&sc<=5){
  if(sc==3||sc==5){FPGA_SELECT();FPGA_TX_BYTE(0x88);(void)spi_rx_byte();FPGA_DESELECT();}
  else sram_writeblock(in,SRAM_MENU_ADDR,257);
  assert(nes_return_failed()&&nes_diag_status()->error==NES_DIAG_SPI);
 }
 if(sc==6){nes_return_fail(NES_DIAG_SD_CRC);sram_writeblock(in,SRAM_MENU_ADDR,257);assert(nes_diag_status()->error==NES_DIAG_SD_CRC&&tx100==0&&select100==0);}
 if(sc==7){native_ns096+=60000000000ull;sram_writeblock(in,SRAM_MENU_ADDR,257);assert(nes_diag_status()->error==NES_DIAG_MENU&&tx100==0&&select100==0);}
 if(sc==8){scenario096=1010;frozen100=1;mode100=4;sram_writeblock(in,SRAM_MENU_ADDR,257);assert(nes_diag_status()->error==NES_DIAG_MENU);}
 if(sc==9){mode100=4;step_ns100=10000000;sram_writeblock(in,SRAM_MENU_ADDR,257);assert(nes_diag_status()->error==NES_DIAG_SPI);}
 if(sc==10){nes_return_log_allow(true);mode100=5;FPGA_SELECT();FPGA_TX_BYTE(0x88);(void)spi_rx_byte();FPGA_DESELECT();assert(nes_diag_status()->error==NES_DIAG_MENU);}
 if(sc==11){
  FPGA_SELECT();FPGA_TX_BYTE(0x00);spi_txrx_byte(0);spi_txrx_byte(0x80);spi_txrx_byte(0);FPGA_DESELECT();
  FPGA_SELECT();FPGA_TX_BYTE(0x98);spi_tx_block(in,257);FPGA_DESELECT();
  set_mcu_addr(0x8000);FPGA_SELECT();FPGA_TX_BYTE(0x88);spi_rx_block(out,257);FPGA_DESELECT();
  assert(!memcmp(in,out,257)&&!nes_return_failed());
 }
 if(sc==12){nes_diag_leave();sram_writeblock(in,0x8000,257);sram_readblock(out,0x8000,257);assert(!memcmp(in,out,257)&&!nes_return_failed());}
 if(nes_return_failed())assert_quiet100();
 printf("PASS100 unit=%u tx=%u select=%u error=%u\n",sc,tx100,select100,nes_diag_status()->error);
}
