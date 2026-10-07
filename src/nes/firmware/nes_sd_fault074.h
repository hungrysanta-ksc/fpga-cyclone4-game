/* SPDX-License-Identifier: MIT */
#ifndef NES_SD_FAULT074_H
#define NES_SD_FAULT074_H
/* Foreground checkpoints, set BEFORE the potentially failing operation. */
void sdinv_fault_stage(unsigned stage);
#endif
