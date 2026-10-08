/* SPDX-License-Identifier: MIT */
#ifndef NES_CF86_SESSION094_H
#define NES_CF86_SESSION094_H
#include <stdbool.h>
/* No software reset for FAILED: only MCU restart starts a new trust lifetime. */
bool nes_cf86_enter094(void);
bool nes_cf86_arm094(void);
bool nes_cf86_check094(void);
bool nes_cf86_failed094(void);
bool nes_cf86_monitoring094(void);
bool nes_cf86_finish094(void);
bool nes_cf86_fail094(void);
#endif
