/* SPDX-License-Identifier: MIT */
/* Included after native nes_diag_sd_response. A completed legacy CMD18 read
 * may still own the card when the menu hands control to this diagnostic.
 * Only that state is drainable here; WRITE/MID/offload remain hard rejects.
 * Do not forge TRANS_NONE before a checked CMD12 response and R1b completion.
 * cmd_fast uses the existing bounded diagnostic waits and shared fault gate. */
extern bool nes_entry_owner113(void);
int nes_entry_transfer113;
bool nes_diag_sd_handoff113(void) {
 nes_entry_transfer113=during_blocktrans;
 if(!nes_diag_active()||nes_return_failed()||!nes_entry_owner113())return false;
 if(disk_state!=DISK_OK||!SDCARD_DETECT||sd_offload||ff_sd_offload||
    (during_blocktrans!=TRANS_NONE&&during_blocktrans!=TRANS_READ)) {
  nes_diag_sd_error(NES_DIAG_SD_STATE);return false;
 }
 if(during_blocktrans==TRANS_NONE)return true;
 int length=cmd_fast(STOP_TRANSMISSION,0,0x61,NULL,rsp);
 if(nes_return_failed())return false;
 if(length!=6||!nes_diag_sd_response(STOP_TRANSMISSION)) {
  nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return false;
 }
 during_blocktrans=TRANS_NONE;
 return true;
}
