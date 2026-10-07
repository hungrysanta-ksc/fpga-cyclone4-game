/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NES_REPORT_BOOT080_H
#define NES_REPORT_BOOT080_H
#include <stdint.h>
#include <stdbool.h>
typedef bool (*report_sink080)(void *,uint8_t);
bool report_decode080(const uint8_t *,unsigned,unsigned,report_sink080,void *);
bool report_boot080(void);
bool report_line080(unsigned,const char *);
#endif
