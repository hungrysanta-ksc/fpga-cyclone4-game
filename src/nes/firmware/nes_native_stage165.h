/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE_STAGE165_H
#define NES_NATIVE_STAGE165_H
#include "nes_native_video165.h"
/* These are SNES CPU WRAM addresses, NEVER MCU/cartridge memory addresses.
 * Adapter must use a SNES-side transport. No direct cartridge SRAM callback. */
#define NES_STAGE165_WRAM_BASE 0x7f0000u
#define NES_STAGE165_SLOT 0x8000u
#define NES_STAGE165_COMMANDS 32u
enum {NES_STAGE165_IDLE,NES_STAGE165_BUILD,NES_STAGE165_DIFF,
      NES_STAGE165_READY,NES_STAGE165_WAIT,NES_STAGE165_FAILED,NES_STAGE165_FAULT};
/* kind0 VRAM,1 CGRAM,2 OAM,3 direct HDMA table in staged WRAM.
 * For kind3 dest is unused. Always install the candidate HDMA pointer, even
 * when bytes matched and there is no kind3 command (old slot may be reused). */
struct nes_stage165_command {uint32_t source;uint16_t dest,size;uint8_t kind;};
typedef bool (*nes_stage165_read_fn)(void *,uint32_t,uint8_t *,unsigned);
typedef bool (*nes_stage165_write_fn)(void *,uint32_t,const uint8_t *,unsigned);
struct nes_native_stage165 {
 struct nes_stage165_command commands[NES_STAGE165_COMMANDS];
 nes_stage165_read_fn read;nes_stage165_write_fn write;void *ctx;
 uint32_t serial,payload,charged;
 uint16_t size[6],old_size[6],generation,hofs,vofs,at,start,end;
 uint16_t bg_next,obj_next,budget;
 uint8_t state,error,section,ncommands,current,candidate;
 bool displayed,run;
};
/* Only after a common consumer/transport reset; old ACKs must be flushed. */
void nes_stage165_reset(struct nes_native_stage165 *,nes_stage165_read_fn,nes_stage165_write_fn,void *);
bool nes_stage165_begin(struct nes_native_stage165 *,uint16_t generation);
bool nes_stage165_pattern(void *,unsigned kind,unsigned slot,const uint8_t *,unsigned);
/* Candidate remains caller-owned/immutable through this bounded staging call.
 * Each write is <=64 bytes. Callback must check the existing fault/time guard. */
bool nes_stage165_seal(struct nes_native_stage165 *,const struct nes_native_video165 *,uint16_t budget);
/* One section or <=64 bytes compared per call, <=2 external reads. */
bool nes_stage165_step(struct nes_native_stage165 *);
/* Arm BEFORE issuing the transport publish; ambiguous failure => abort/FAULT.
 * Even a zero-DMA scene needs the generation/scroll/display ACK. */
bool nes_stage165_arm(struct nes_native_stage165 *);
bool nes_stage165_ack(struct nes_native_stage165 *,uint32_t serial,uint16_t generation,bool success);
void nes_stage165_abort(struct nes_native_stage165 *);
#endif
