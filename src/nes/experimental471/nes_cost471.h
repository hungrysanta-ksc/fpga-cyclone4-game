/* SPDX-License-Identifier: MIT */
#ifndef NES_COST471_H
#define NES_COST471_H
#include <stdint.h>
struct nes_cost471_bucket {uint64_t cycles;uint32_t calls,bytes,max_cycles;};
extern struct nes_cost471_bucket nes_cost471_ops[12],nes_cost471_phases[3];
extern uint32_t nes_cost471_scene_crc;
extern uint32_t nes_cost471_available,nes_cost471_crc_errors,nes_cost471_transfer_stops;
void nes_cost471_begin(void);void nes_cost471_end(void);
uint32_t nes_cost471_now(void);void nes_cost471_op(unsigned,unsigned,uint32_t);
void nes_cost471_phase(unsigned,uint32_t);
int nes_cost471_append(char *,unsigned,int);
#endif
