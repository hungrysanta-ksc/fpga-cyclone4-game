#ifndef GBC_STATE_SLOTS_H
#define GBC_STATE_SLOTS_H
#include "gbc_state_format.h"
/* Staged file at E80000, payload at E80040. These functions never modify
 * the live core or battery save. Save caller freezes the staged payload;
 * load must succeed before the caller enters the hardware restore session. */
int gbc_state_slot_save(const gbc_state_identity *identity);
int gbc_state_slot_stage_load(const gbc_state_identity *identity);
#endif
