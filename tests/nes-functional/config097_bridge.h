/* SPDX-License-Identifier: MIT */
#ifndef CONFIG097_BRIDGE_H
#define CONFIG097_BRIDGE_H
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
extern uint8_t *diag_packed097,*diag_raw097,*base_packed097,*base_raw097,*menu097;
extern unsigned diag_size097,diag_raw_size097,base_size097,base_raw_size097,menu_size097;
void card_stage097(unsigned);
unsigned card_report097(char *,unsigned);
#endif
