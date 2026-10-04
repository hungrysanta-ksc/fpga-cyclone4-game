#ifndef GBC_DUMP_H
#define GBC_DUMP_H
#include <stdint.h>
void gbc_dump_disarm(void);
void gbc_dump_arm(const uint8_t *filename);
void gbc_dump_observe(void);
uint8_t gbc_dump_exit(void);
#endif
