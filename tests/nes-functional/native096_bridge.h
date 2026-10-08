/* SPDX-License-Identifier: MIT */
#ifndef NATIVE096_BRIDGE_H
#define NATIVE096_BRIDGE_H
#include <stdint.h>
void native_edge096(unsigned,unsigned);
void card_setup096(const uint8_t *,unsigned);
unsigned card_commands096(void);
unsigned card_edges096(void);
void card_fault096(unsigned,unsigned);
void card_phase_fault096(unsigned,unsigned,unsigned);
void card_summary096(void);
void card_present096(unsigned);
void card_invalidate096(void);
void card_profile096(unsigned);
unsigned card_writes096(void);
#endif
