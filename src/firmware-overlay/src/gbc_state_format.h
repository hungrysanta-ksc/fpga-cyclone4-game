#ifndef GBC_STATE_FORMAT_H
#define GBC_STATE_FORMAT_H
#include <stdint.h>
#define GBC_STATE_HEADER_BYTES 64u
#define GBC_STATE_CORE_BYTES 49936u
#define GBC_STATE_SCHEMA 0x00350002u
#define GBC_STATE_STAGE_BASE 0xe80000u
#define GBC_STATE_MAX_PAYLOAD (GBC_STATE_CORE_BYTES+131072u)
typedef struct { uint32_t rom_bytes,rom_crc,ram_bytes,slot; } gbc_state_identity;
typedef int (*gbc_state_reader)(void *context,uint32_t offset,uint8_t *data,uint16_t count);
int gbc_state_identity_valid(const gbc_state_identity *id);
int gbc_state_header_make(uint8_t out[64],const gbc_state_identity *id,uint32_t generation,uint32_t payload_crc);
/* Reads the entire file. Never writes the core or filesystem. */
int gbc_state_validate(gbc_state_reader read,void *context,uint32_t file_bytes,
 const gbc_state_identity *id,uint32_t *generation,uint32_t *payload_crc);
/* Payload order: WRAM, VRAM, OAM, HRAM, palette, registers, cartridge RAM.
 * Returns the largest contiguous transfer up to limit, or zero at EOF/error. */
uint16_t gbc_state_region(uint32_t offset,uint32_t ram_bytes,uint16_t limit,uint32_t *address);
#endif
