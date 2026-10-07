/* SPDX-License-Identifier: MIT */
static bool nes_return_spi_wait(unsigned pin,bool level) {
 struct nes_diag_wait wait=nes_diag_wait_start(25,1000000u);
 if(nes_return_failed())return false;
 while(!!BITBAND(SPI1->SR,pin)!=level){
  if(!nes_diag_wait_step(&wait)){nes_return_fail(NES_DIAG_SPI);return false;}
 }
 return true;
}
static uint8_t nes_return_spi_exchange(uint8_t data) {
 if(!nes_return_spi_wait(SPI_SR_BSY_Pos,false))return 0;
 struct nes_diag_wait wait=nes_diag_wait_start(25,1000000u);
 while(BITBAND(SPI1->SR,SPI_SR_RXNE_Pos)){
  (void)SPI1->DR;
  if(!nes_diag_wait_step(&wait)){nes_return_fail(NES_DIAG_SPI);return 0;}
 }
 if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return 0;
 SPI1->DR=data;
 if(!nes_return_spi_wait(SPI_SR_RXNE_Pos,true))return 0;
 return SPI1->DR;
}
bool nes_return_spi_ready(void) {
 if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return false;
 struct nes_diag_wait wait=nes_diag_wait_start(25,1000000u);
 while(!BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)){
  if(!nes_diag_wait_step(&wait)){nes_return_fail(NES_DIAG_SPI);return false;}
 }
 return !nes_return_failed();
}
