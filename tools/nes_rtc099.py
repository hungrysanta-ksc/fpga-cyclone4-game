# SPDX-License-Identifier: MIT
"""Derive diagnostic-only RTC guards from the immutable098 source."""
from pathlib import Path
from nes_menu098 import once

HELPER = '''
/* Diagnostic waits must terminate even when SysTick stops. The local limit
 * does not restart the shared menu/report budget or clear its first error. */
static bool rtc_wait099(unsigned bit) {
  struct nes_diag_wait wait = nes_diag_wait_start(100, 100000u);
  for(;;) {
    if(nes_return_failed() || !nes_return_io_step()) return false;
    if(!nes_diag_wait_step(&wait)) {
      nes_return_fail(NES_DIAG_RTC);
      return false;
    }
    if(BITBAND(RTC->ISR, bit)) return true;
  }
}
'''

def adapt(src: Path):
    p=src/'stm32f4xx/rtc.c';s=p.read_text()
    s=once(s,'#include "power.h"','#include "power.h"\n#include "nes_menu_return.h"\n'+HELPER)
    s=once(s,'uint8_t rtc_isvalid() {','uint8_t rtc_isvalid() {\n  if(nes_diag_active() && nes_return_failed()) return RTC_INVALID;')
    s=once(s,'  while(!BITBAND(RTC->ISR, RTC_ISR_RSF_Pos));','''  if(nes_diag_active()) {
    *time = (struct tm){0};
    if(nes_return_failed() || !rtc_wait099(RTC_ISR_RSF_Pos)) return;
  } else while(!BITBAND(RTC->ISR, RTC_ISR_RSF_Pos));''')
    s=once(s,'void set_rtc(struct tm *time) {\n  uint32_t val;','void set_rtc(struct tm *time) {\n  uint32_t val;\n  if(nes_diag_active() && nes_return_failed()) return;')
    s=once(s,'  while(!BITBAND(RTC->ISR, RTC_ISR_INITF_Pos));','''  if(nes_diag_active()) {
    if(!rtc_wait099(RTC_ISR_INITF_Pos)) {
      /* Cancel our init request and restore write protection only. No
       * calendar/century/validity update and no recovery/retry after fault. */
      BITBAND(RTC->ISR, RTC_ISR_INIT_Pos) = 0;
      rtc_lock();
      return;
    }
  } else while(!BITBAND(RTC->ISR, RTC_ISR_INITF_Pos));''')
    s=once(s,'void invalidate_rtc() {','void invalidate_rtc() {\n  if(nes_diag_active() && nes_return_failed()) return;')
    assert s.count('  read_rtc(&time);')==2
    s=s.replace('  read_rtc(&time);','  read_rtc(&time);\n  if(nes_diag_active() && nes_return_failed()) return 0;')
    s=once(s,'void set_bcdtime(uint64_t btime) {','void set_bcdtime(uint64_t btime) {\n  if(nes_diag_active() && nes_return_failed()) return;')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=src/'nes_diag_runtime.h'
    p.write_text(once(p.read_text(),'NES_DIAG_TIMER,NES_DIAG_MENU};','NES_DIAG_TIMER,NES_DIAG_MENU,NES_DIAG_RTC};'),encoding='utf-8',newline='\n')
