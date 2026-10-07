/* SPDX-License-Identifier: MIT */
#include "nes_diag_runtime.h"
static bool active;
static struct nes_diag_report report;
bool nes_diag_active(void){return active;}
const struct nes_diag_report *nes_diag_status(void){return &report;}
void nes_diag_begin(void){active=true;report=(struct nes_diag_report){NES_DIAG_VALIDATE,0,0,0};nes_diag_observe(&report,true);}
void nes_diag_leave(void){active=false;nes_diag_observe(&report,false);}
void nes_diag_progress(enum nes_diag_phase phase,uint32_t completed,uint32_t total){
 report.phase=phase;report.completed=completed;report.total=total;nes_diag_observe(&report,active);
}
void nes_diag_fail(enum nes_diag_error error){if(!report.error)report.error=error;nes_diag_observe(&report,active);}
struct nes_diag_wait nes_diag_wait_start(uint32_t ticks,uint32_t polls){return (struct nes_diag_wait){nes_diag_ticks(),ticks,polls};}
bool nes_diag_wait_step(struct nes_diag_wait *w){
 if(!w->polls||(uint32_t)(nes_diag_ticks()-w->started)>=w->ticks)return false;
 w->polls--;return true;
}
