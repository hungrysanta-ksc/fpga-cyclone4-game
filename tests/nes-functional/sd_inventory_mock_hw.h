/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SDINV_HW_H
#define SDINV_HW_H
#include <stdint.h>
#include <stdbool.h>
#define OTG_FS_IRQn 67
void NVIC_DisableIRQ(unsigned);
void snes_reset(int);
void snes_bootclear(void);
void snes_bootprint_version(void);
void snes_bootprint_center(int,const char *,...);
void mock_halt(void) __attribute__((noreturn));
#define __NOP() mock_halt()
#endif
