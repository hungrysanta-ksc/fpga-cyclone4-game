/* SPDX-License-Identifier: MIT */
#ifndef NES_DIAG_RUNTIME_H
#define NES_DIAG_RUNTIME_H
#include <stdbool.h>
#include <stdint.h>
enum nes_diag_phase {NES_DIAG_VALIDATE=1,NES_DIAG_CONFIG,NES_DIAG_LOAD,NES_DIAG_CHECK,NES_DIAG_RECOVER,NES_DIAG_BLOCKED};
enum nes_diag_error {NES_DIAG_ERROR_NONE,NES_DIAG_SD_BUSY,NES_DIAG_SD_RESPONSE,NES_DIAG_SD_DATA,NES_DIAG_SD_CRC,NES_DIAG_SD_STATE,NES_DIAG_FPGA_OPEN,NES_DIAG_FPGA_PROG,NES_DIAG_FPGA_INIT,NES_DIAG_FPGA_DONE,NES_DIAG_FPGA_READ,NES_DIAG_FPGA_FORMAT,NES_DIAG_FPGA_LIMIT,NES_DIAG_FPGA_CLOSE};
struct nes_diag_report {enum nes_diag_phase phase;enum nes_diag_error error;uint32_t completed,total;};
struct nes_diag_wait {uint32_t started,ticks,polls;};
bool nes_diag_active(void);
void nes_diag_begin(void);
void nes_diag_leave(void);
void nes_diag_progress(enum nes_diag_phase,uint32_t,uint32_t);
void nes_diag_fail(enum nes_diag_error);
const struct nes_diag_report *nes_diag_status(void);
struct nes_diag_wait nes_diag_wait_start(uint32_t ticks,uint32_t polls);
bool nes_diag_wait_step(struct nes_diag_wait *);
uint32_t nes_diag_ticks(void);
void nes_diag_observe(const struct nes_diag_report *,bool active);
void nes_diag_led_tick(void);
void nes_diag_sd_reset(void);
bool nes_diag_sd_failed(void);
bool nes_diag_fpga_pgm(const uint8_t *);
void nes_diag_blocked(void) __attribute__((noreturn));
#endif
