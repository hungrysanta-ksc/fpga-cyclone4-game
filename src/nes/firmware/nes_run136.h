/* SPDX-License-Identifier: MIT */
#ifndef NES_RUN136_H
#define NES_RUN136_H
#include <stdint.h>
#include <stdbool.h>
struct nes_run136_report {
 uint32_t first,last,stopped;
 uint8_t flags,rom_error,observer_id,error;
 bool start_sent,stop_ok,passed;
};
extern struct nes_run136_report nes_run136;
#endif
