/* SPDX-License-Identifier: MIT */
#ifndef NES_CHECKPOINT112_H
#define NES_CHECKPOINT112_H
#include <stdbool.h>
#include <stdint.h>
bool nes_checkpoint_begin112(void);
bool nes_checkpoint112(const char *,uint32_t,uint32_t);
void nes_checkpoint_progress112(unsigned,uint32_t,uint32_t);
bool nes_return_checkpoint_enter112(void);
void nes_return_checkpoint_leave112(void);
#endif
