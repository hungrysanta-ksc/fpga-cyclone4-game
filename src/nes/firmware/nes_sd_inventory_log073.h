/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NES_SD_INVENTORY_LOG073_H
#define NES_SD_INVENTORY_LOG073_H
#include <stdint.h>
struct sdinv_save_detail {unsigned operation,fresult,requested,returned,offset,failed;};
/* 1 open,2 write,3 sync,4 close,5 read-open,6 read,7 read-close,8 size. */
const struct sdinv_save_detail *sdinv_save_detail(void);
#endif
