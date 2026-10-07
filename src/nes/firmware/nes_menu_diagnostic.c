/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <string.h>
#include "config.h"
#include "fileops.h"
#include "nes_menu_probe.h"
#include "nes_menu_diagnostic.h"

static struct nes_menu_probe_report report;
static bool pending, safe_to_reload, prepared;
static unsigned geometry;

static unsigned marker_geometry(const uint8_t *path) {
 if(!path)return 0;
 const char *name=(const char *)path;
 for(const char *p=name;*p;p++)if(*p=='/'||*p=='\\')name=p+1;
 const char *names[2]={"NES VERIFY 062 80.nh1","NES VERIFY 062 96.nh1"};
 for(unsigned i=0;i<2;i++) {
  const char *a=name,*b=names[i];
  while(*a&&*b) {
   unsigned ca=(unsigned char)*a++,cb=(unsigned char)*b++;
   if(ca>='a'&&ca<='z')ca-=32;
   if(cb>='a'&&cb<='z')cb-=32;
   if(ca!=cb)break;
   if(!*a&&!*b)return i?96:80;
  }
 }
 return 0;
}
bool nes_menu_diagnostic_marker(const uint8_t *path){return marker_geometry(path)!=0;}

static void save_report(const char *menu_state,bool persist) {
 char text[640];FIL log;UINT written=0;
 int n=snprintf(text,sizeof(text),
  "candidate=NES-MENU-DIAGNOSTIC-062\nboard_expected_hex=61\nboard_seen=%u\nboard_observed_hex=%02x\n"
  "geometry_kib=%u\nload_result=%u\nfile_result=%u\nloaded_bytes=%lu\ncompared_bytes=%lu\n"
  "verify_error=%u\nverified=%u\nend_accepted=%u\nstop_ok=%u\nbase_attempted=%u\n"
  "base_restored=%u\nsafe_to_reload=%u\nmenu_state=%s\nstart_sent=0\n",
  report.board_seen,report.board_id,geometry,(unsigned)report.sd.load.result,report.sd.load.file_result,
  (unsigned long)report.sd.load.acknowledged_bytes,(unsigned long)report.sd.verify.compared,
  (unsigned)report.sd.verify.error,report.sd.verified,report.sd.load.end_accepted,report.sd.load.stop_ok,
  report.sd.load.recovery_attempted,report.sd.load.base_restored,safe_to_reload,menu_state);
 if(n<=0||(size_t)n>=sizeof(text))return;
 printf("%s",text);
 if(!persist)return;
 /* Only after safe base restoration and outside the GPIO session. Protect
  * the shared FatFS implementation from USB, restoring its original IRQ. */
 bool irq=NVIC_GetEnableIRQ(OTG_FS_IRQn)!=0;
 NVIC_DisableIRQ(OTG_FS_IRQn);
 FRESULT opened=f_open(&log,"/sd2snes/nes-verify-last-062.txt",FA_CREATE_ALWAYS|FA_WRITE);
 FRESULT saved=opened,closed=opened;
 if(opened==FR_OK){saved=f_write(&log,text,(UINT)n,&written);closed=f_close(&log);}
 if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);
 printf("NES062 log open=%u write=%u close=%u bytes=%u/%u\n",
  (unsigned)opened,(unsigned)saved,(unsigned)closed,(unsigned)written,(unsigned)n);
}
bool nes_menu_diagnostic_run(const uint8_t *path) {
 unsigned selected=marker_geometry(path);
 if(!selected||pending)return false;
 geometry=selected;pending=true;prepared=false;safe_to_reload=false;
 memset(&report,0,sizeof(report));
 printf("NES062 manual load/verify-only: %uKiB; RESET held; no pad cancel; wire delays >=%us plus SD/configuration.\n",
  geometry,geometry==80?113:136);
 safe_to_reload=nes_menu_sd_probe(geometry==80?"/sd2snes/nes/fine_x.nes":"/sd2snes/nes/banks32.nes",
  "/sd2snes/fpga_nlv.bi3",geometry==96,&report);
 /* Recovery failure: keep report in RAM/UART; no SD/USB/menu operations. */
 if(!safe_to_reload){save_report("BLOCKED_RESET_HELD",false);printf("NES062 recovery failed; RESET/USB protection held; no menu reload.\n");}
 return safe_to_reload;
}
bool nes_menu_diagnostic_prepared(bool menu_ok) {
 if(!pending)return true;
 if(!safe_to_reload||!menu_ok)return false;
 prepared=true;save_report("PREPARED_RESET_HELD",true);return true;
}
void nes_menu_diagnostic_released(void) {
 if(pending&&safe_to_reload&&prepared){save_report("RELEASE_BOUNDARY_REACHED",true);pending=false;}
}
