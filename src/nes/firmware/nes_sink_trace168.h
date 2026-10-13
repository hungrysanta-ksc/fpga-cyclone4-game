/* SPDX-License-Identifier: MIT */
#ifndef NES_SINK_TRACE168_H
#define NES_SINK_TRACE168_H
#include <stdint.h>
#include <stdbool.h>
/* First failed exchange only. Scalar copy survives RUN workspace release. */
struct nes_sink_trace168 {
 uint8_t valid,ack_valid,mismatch,reserved;
 uint8_t request[16],ack[12];
};
extern struct nes_sink_trace168 nes_sink_trace168;
uint8_t nes_sink168_mismatch(const uint8_t request[16],const uint8_t ack[12]);
void nes_sink168_capture(const uint8_t request[16],const uint8_t ack[12],bool ack_valid,uint8_t mismatch);
int nes_sink168_format(char *text,unsigned capacity);
#endif
