/* SPDX-License-Identifier: MIT */
#ifndef NES_MENU_RETURN_H
#define NES_MENU_RETURN_H
#include "nes_diag_runtime.h"
void nes_return_reset(void);
void nes_return_io_begin(void);
bool nes_return_io_step(void);
void nes_return_fail(enum nes_diag_error);
bool nes_return_failed(void);
void nes_return_log_allow(bool);
bool nes_return_log_allowed(void);
bool nes_return_spi_ready(void);
bool nes_return_delay(unsigned,bool);
uint32_t nes_return_copy_menu(const char *,uint32_t,uint32_t);
bool nes_menu_diagnostic_pending(void);
#endif
