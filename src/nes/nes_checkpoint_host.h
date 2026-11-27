/* SPDX-License-Identifier: MIT */
#ifndef NES_CHECKPOINT_HOST_H
#define NES_CHECKPOINT_HOST_H
#include "nes_savefile.h"
#include <stdbool.h>
/* Run only with the display drained and exclusive FatFS + cartridge SPI ownership.
 * The caller owns staging and keeps the NES paused across consecutive menu actions.
 * On transport failure, STOP/reinitialize before resuming the game. */
typedef bool (*nes_state_exchange)(const unsigned char tx[13], unsigned char rx[13]);
bool nes_state_pause(nes_state_exchange exchange,bool (*drain)(void *),void *ctx);
int nes_state_file_pages(nes_state_exchange exchange, struct nes_save_id id, bool load);
bool nes_state_resume(nes_state_exchange exchange);
int nes_state_file_action(nes_state_exchange exchange, struct nes_save_id id, bool load,
                          unsigned char *staging, unsigned capacity);
#endif
