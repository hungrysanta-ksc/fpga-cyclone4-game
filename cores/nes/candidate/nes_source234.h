/* SPDX-License-Identifier: MIT */
#ifndef NES_SOURCE234_H
#define NES_SOURCE234_H
#include "nes_native165.h"
/* Candidate framed-record receiver. Outer SPI token/CRC/admission remain
 * required. No record reassembly buffer and no second geometry image. */
struct nes_source234 {
 uint32_t epoch,serial,pending;
 uint16_t generation,next,end,spans,bytes,crc,raw_at;
 bool valid,open,full,geometry,fault;
};
bool nes_source234_packet(struct nes_source234 *,struct nes_native165 *,const uint8_t *,unsigned);
void nes_source234_abort(struct nes_source234 *,struct nes_native165 *);
/* Only after common STOP/reset; a partial update must never be reused. */
void nes_source234_reset(struct nes_source234 *);
#endif
