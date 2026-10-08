/* SPDX-License-Identifier: MIT */
#ifndef NES_CSS108_H
#define NES_CSS108_H
#include <stdbool.h>
#include <stdint.h>
bool nes_css_begin108(void);
bool nes_css_end108(void);
uint32_t nes_css_fault108(void);
void NMI_Handler(void) __attribute__((noreturn));
#endif
