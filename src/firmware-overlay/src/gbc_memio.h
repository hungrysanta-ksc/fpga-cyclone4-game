#ifndef GBC_MEMIO_H
#define GBC_MEMIO_H
#include <stdint.h>
uint16_t gbc_sram_readblock(void *buf,uint32_t addr,uint16_t size);
uint16_t gbc_sram_writeblock(void *buf,uint32_t addr,uint16_t size);
void gbc_memio_clear_error(void);
uint32_t gbc_memio_error_address(void);
#endif
