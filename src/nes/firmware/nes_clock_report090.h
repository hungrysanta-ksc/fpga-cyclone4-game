/* SPDX-License-Identifier: MIT */
#ifndef NES_CLOCK_REPORT090_H
#define NES_CLOCK_REPORT090_H
#include "nes_clock_reader088.h"
unsigned clock_text090(char *,unsigned,const struct clock_report088 *);
const char *clock_label090(enum clock_result088);
bool report_session090(void);
#endif
