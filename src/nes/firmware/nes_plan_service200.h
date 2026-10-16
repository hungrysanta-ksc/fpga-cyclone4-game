/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN_SERVICE200_H
#define NES_PLAN_SERVICE200_H
#include "nes_plan191.h"
#include "nes_sink_bulk195.h"
/* transfer must support tx==rx: read each outbound byte before overwriting it.
 * Return after SS high + >=2us gap. Never retain buffers. RUN-owned storage;
 * zero initialize after common reset, sink BUILD. Retire after matching final display ACK; then begin the next frame.
 * emit success may mean locally buffered, NOT FPGA accepted or displayed. */
typedef bool (*nes_plan200_transfer)(void *,const uint8_t *,uint8_t *,unsigned);
struct nes_plan200 {
 nes_plan200_transfer transfer;bool (*guard)(void *);void *ctx;struct nes_native_sink165 *sink;
 unsigned poll_limit;uint16_t sent,bytes,generation;uint8_t count,error;bool started,finished;
 uint8_t buffer[248]; // <=240B plans+8B framing, within deployed259B transfer cap.
};
bool nes_plan200_emit(void *,const struct nes_plan191 *);
bool nes_plan200_finish(struct nes_plan200 *);
/* Requires successful finish AND matching sink final display ACK, not op7 ACK. */
bool nes_plan200_retire(struct nes_plan200 *);
#endif
