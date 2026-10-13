/* SPDX-License-Identifier: MIT */
#ifndef NES_SINK_IO170_H
#define NES_SINK_IO170_H
#include <stdint.h>
#include <stdbool.h>
/* First failing exchange only. reason bit7 means status bytes were received,
 * not that their ID/flags/CRC are valid. status is SPI RX[1..15], no dummy byte.
 * polls counts attempted E0 poll transfers (not guards or elapsed time). */
struct nes_sink_io170 {uint32_t polls;uint8_t reason,status[15];};
extern struct nes_sink_io170 nes_sink_io170;
enum {SIO170_ARGUMENT=1,SIO170_PRE_GUARD,SIO170_PRE_TRANSFER,SIO170_PRE_STATUS,
 SIO170_BUSY,SIO170_WRITE_GUARD,SIO170_WRITE_TRANSFER,SIO170_POLL_GUARD,
 SIO170_POLL_TRANSFER,SIO170_POLL_STATUS,SIO170_POLL_LIMIT};
bool nes_sink_io170_fail(unsigned reason,uint32_t polls,const uint8_t *rx);
int nes_sink_io170_format(char *text,unsigned capacity);
#endif
