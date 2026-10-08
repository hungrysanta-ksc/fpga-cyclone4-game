/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include "nes_menu_return.h"
static uint32_t ticks099,tick_step099;
uint32_t nes_diag_ticks(void){uint32_t v=ticks099;ticks099+=tick_step099;return v;}
void nes_diag_observe(const struct nes_diag_report*r,bool active){(void)r;(void)active;}
bool nes_diag_sd_failed(void){return false;}
#include "rtc099.inc"
static void fail099(int sig){(void)sig;_Exit(86);}
int main(int argc,char **argv){
 signal(SIGABRT,fail099);assert(argc==2);unsigned sc=strtoul(argv[1],0,10);
 setup_rtc099(sc);nes_diag_begin();nes_return_reset();nes_return_io_begin();
 tick_step099=0;
 struct rtc_tm099 t={56,34,12,8,10,2026,3};
 uint32_t oldtr=regs099[R_TR],olddr=regs099[R_DR],oldcentury=regs099[R_BKP2R];
 if(sc==0){read_rtc(&t);assert(t.tm_year==2026&&t.tm_mon==10&&t.tm_mday==8&&t.tm_hour==12&&t.tm_min==34&&t.tm_sec==56&&t.tm_wday==3);assert(!aliases099[0][RTC_ISR_RSF_Pos]);}
 if(sc==1){set_bcdtime(0x20120701000000LL);assert(regs099[R_TR]==0&&regs099[R_DR]==0x122701&&regs099[R_BKP2R]==20&&regs099[R_BKP0R]==RTC_MAGIC);assert(!aliases099[0][RTC_ISR_INIT_Pos]&&regs099[R_WPR]==0);}
 if(sc==2){delay099=7;assert((get_bcdtime()&0x00ffffffffffffffULL)==0x20261008123456ULL&&polls099==9);}
 if(sc==3){assert(get_fattime()==((46u<<25)|(10u<<21)|(8u<<16)|(12u<<11)|(34u<<5)|28u));}
 if(sc>=4&&sc<=9){
  stall099=1;tick_step099=(sc==4||sc==5||sc==8||sc==9)?1:0;
  if(sc==8||sc==9){ticks099=0xfffffff0u;nes_return_io_begin();}
  if(sc%2)set_rtc(&t);else {memset(&t,0xa5,sizeof(t));read_rtc(&t);struct rtc_tm099 zero={0};assert(!memcmp(&t,&zero,sizeof(t)));}
  assert(nes_return_failed()&&nes_diag_status()->error==NES_DIAG_RTC);
  assert(polls099>0&&polls099<=100000);
  assert(polls099==(tick_step099?49u:100000u)); /* Shared + local tick queries. */
  assert(regs099[R_TR]==oldtr&&regs099[R_DR]==olddr&&regs099[R_BKP2R]==oldcentury&&regs099[R_BKP0R]==RTC_MAGIC);
  assert(!aliases099[0][RTC_ISR_INIT_Pos]&&regs099[R_WPR]==0);
 }
 if(sc==10){nes_return_fail(NES_DIAG_SD_CRC);unsigned n=accesses099;set_rtc(&t);set_bcdtime(0);invalidate_rtc();read_rtc(&t);assert(!get_fattime()&&!get_bcdtime()&&rtc_isvalid()==RTC_INVALID);assert(accesses099==n&&nes_diag_status()->error==NES_DIAG_SD_CRC);}
 if(sc==11||sc==12){delay099=100;inject099=3;if(sc==11)read_rtc(&t);else set_rtc(&t);assert(nes_return_failed()&&nes_diag_status()->error==NES_DIAG_SPI&&polls099==3);assert(regs099[R_TR]==oldtr&&regs099[R_DR]==olddr&&!aliases099[0][RTC_ISR_INIT_Pos]&&regs099[R_WPR]==0);}
 if(sc==13||sc==14){stall099=1;if(sc==13)assert(get_fattime()==0);else assert(get_bcdtime()==0);assert(nes_diag_status()->error==NES_DIAG_RTC);}
 if(sc==15){ticks099=6001;read_rtc(&t);assert(nes_diag_status()->error==NES_DIAG_MENU&&polls099==0);}
 if(sc==16){nes_diag_leave();delay099=12;read_rtc(&t);set_rtc(&t);assert(!nes_return_failed()&&t.tm_year==2026);}
 if(sc==17){regs099[R_BKP0R]=0;assert(rtc_isvalid()==RTC_INVALID);set_bcdtime(0x20120701000000ULL);assert(rtc_isvalid()==RTC_OK);invalidate_rtc();assert(rtc_isvalid()==RTC_INVALID);}
 if(nes_return_failed()){
  unsigned n=accesses099,p=polls099;unsigned err=nes_diag_status()->error;
  stall099=0;read_rtc(&t);set_rtc(&t);set_bcdtime(0);invalidate_rtc();assert(!get_bcdtime()&&!get_fattime());
  assert(accesses099==n&&polls099==p&&nes_diag_status()->error==err);
 }
 printf("PASS099 unit=%u polls=%u error=%u\n",sc,polls099,nes_diag_status()->error);return 0;
}
