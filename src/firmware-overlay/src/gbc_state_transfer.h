#ifndef GBC_STATE_TRANSFER_H
#define GBC_STATE_TRANSFER_H
#include "gbc_state_format.h"
/* Menu must remain open. Return 1 success, 0 recoverable failure,
 * -1 locked failure: only a core reset/reload can resume safely. */
int gbc_state_capture(const gbc_state_identity *id);
int gbc_state_restore(const gbc_state_identity *id);
int gbc_state_faulted(void);
void gbc_state_reset_session(void);
#endif

void gbc_state_diagnostic(uint32_t out[4]);
