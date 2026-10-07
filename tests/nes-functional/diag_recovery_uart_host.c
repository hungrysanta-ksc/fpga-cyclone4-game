/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include "nes_diag_runtime.h"
static struct {unsigned DR;} regs;
#define UART_REGS (&regs)
#define USART_SR_TXE_Pos 0
static unsigned ready,reads;
#define BITBAND(reg,pin) (++reads,ready)
volatile uint32_t nes_diag_uart_dropped;
static uint32_t tick,step;
uint32_t nes_diag_ticks(void){tick+=step;return tick;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
#include "uart-functions.inc"
int main(void){
 nes_diag_begin();regs.DR=123;ready=0;uart_putc('A');assert(regs.DR==123&&nes_diag_uart_dropped==1&&reads==100001);
 reads=0;uart_flush();assert(nes_diag_uart_dropped==2&&reads==100001);
 step=1;reads=0;uart_putc('B');assert(nes_diag_uart_dropped==3&&reads==1);
 step=0;ready=1;uart_putc('\n');assert(regs.DR=='\n'&&nes_diag_uart_dropped==3);
 nes_diag_leave();uart_putc('C');assert(regs.DR=='C'&&nes_diag_uart_dropped==3);
 printf("PASS RECOVERY064 UART cases=5 frozen_tick=1 normal_path=1\n");return 0;
}
