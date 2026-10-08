# SPDX-License-Identifier: MIT
"""Diagnostic-only lower SPI budget/fault and chip-select admission guards."""
from nes_menu098 import once
from test_nes_menu098 import definition

def adapt(src):
 p=src/'fpga_spi.h';s=p.read_text()
 s=once(s,'#define FPGA_SELECT() do {FPGA_TX_SYNC(); CLEAR_BIT(FPGA_SSREG, FPGA_SSBIT);} while (0)',
 '#define FPGA_SELECT() do {FPGA_TX_SYNC(); if(!nes_diag_active()||!nes_return_failed())CLEAR_BIT(FPGA_SSREG, FPGA_SSBIT);} while (0)')
 s=once(s,'#define FPGA_SELECT_ASYNC() do {CLEAR_BIT(FPGA_SSREG, FPGA_SSBIT);} while (0)',
 '#define FPGA_SELECT_ASYNC() do {if(!nes_diag_active()||!nes_return_failed())CLEAR_BIT(FPGA_SSREG, FPGA_SSBIT);} while (0)')
 p.write_text(s,encoding='utf-8',newline='\n')
 p=src/'stm32f4xx/spi.c';s=p.read_text()
 s=once(s,definition(s,'nes_return_spi_wait'),'''static bool nes_return_spi_wait(unsigned pin,bool level) {
 struct nes_diag_wait wait=nes_diag_wait_start(25,1000000u);
 for(;;) {
  if(nes_return_failed()||!nes_return_io_step())return false;
  if(!nes_diag_wait_step(&wait)){nes_return_fail(NES_DIAG_SPI);return false;}
  if(!!BITBAND(SPI1->SR,pin)==level)return true;
 }
}\n''')
 s=once(s,'  (void)SPI1->DR;\n  if(!nes_diag_wait_step(&wait))','  if(nes_return_failed()||!nes_return_io_step())return 0;\n  (void)SPI1->DR;\n  if(!nes_diag_wait_step(&wait))')
 s=once(s,definition(s,'nes_return_spi_ready'),'''bool nes_return_spi_ready(void) {
 if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return false;
 struct nes_diag_wait wait=nes_diag_wait_start(25,1000000u);
 for(;;) {
  if(nes_return_failed()||!nes_return_io_step())return false;
  if(!nes_diag_wait_step(&wait)){nes_return_fail(NES_DIAG_SPI);return false;}
  if(BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT))return true;
 }
}\n''')
 p.write_text(s,encoding='utf-8',newline='\n')
