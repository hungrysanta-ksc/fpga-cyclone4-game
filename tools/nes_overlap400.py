# SPDX-License-Identifier: MIT
"""400 M4 receive-ahead, retaining the old display identity through final ACK.
Private helper status:0 failure,1 no source SPI,2 source SPI changed ownership.
Only2 invalidates the cached plan response and its armed WFI state.
"""
from nes_delta231 import once

def apply(d):
 p=d/'nes_input286.inc';s=p.read_text()
 s=once(s,'void invalidate352(void){raw_groups352=UINT32_MAX;display_epoch352=0;}', '''static uint32_t display_epoch400,display_serial400,display_count400;
static unsigned display_saved400;
void invalidate352(void){display_saved400=0;raw_groups352=UINT32_MAX;display_epoch352=0;}''')
 s=once(s,'void publish352(void){', '''static uint32_t display_epoch400,display_serial400,display_count400;
static unsigned display_saved400;
unsigned save_display400(void){
 if(display_saved400)return display_serial400==resident285.serial;
 if(!receiver280.valid||receiver280.phase||!resident285.open||!resident285.prepared||
    resident285.serial!=receiver280.serial||resident285.epoch!=receiver280.epoch)return 0;
 display_epoch400=receiver280.epoch;display_serial400=receiver280.serial;
 display_count400=receiver280.raw_count;display_saved400=1;return 1;
}
void publish352(void){''')
 s=s.replace('static uint32_t display_epoch400,display_serial400,display_count400;\nstatic unsigned display_saved400;\nunsigned save_display400', 'unsigned save_display400')
 s=once(s,'display_epoch352=receiver280.epoch;display_serial352=receiver280.serial;\n display_count352=receiver280.raw_count;', '''if(display_saved400){
  if(resident285.serial!=display_serial400||resident285.epoch!=display_epoch400){display_saved400=0;invalidate352();return;}
  display_epoch352=display_epoch400;display_serial352=display_serial400;display_count352=display_count400;display_saved400=0;
 }else{display_epoch352=receiver280.epoch;display_serial352=receiver280.serial;display_count352=receiver280.raw_count;}''')
 s=once(s,'if(!receiver280.valid||receiver280.phase||dirty285.open', 'if((!display_saved400&&(!receiver280.valid||receiver280.phase))||dirty285.open')
 # A fault must not leave a saved display identity or prefetched input alive.
 s=once(s,'void stop286(void){', 'extern void cancel_prefetch400(void);\nvoid stop286(void){display_saved400=0;cancel_prefetch400();')
 p.write_text(s,newline='\n')
 p=d/'nes_decode280.c';s=p.read_text()
 s=once(s,'unsigned source_receive367(void){', '''unsigned prefetched400,prefetch_busy400,prefetch_enabled400,prefetch_groups400,prefetch_attempts400,prefetch_completions400;
unsigned prefetch_partial400,prefetch_yields400;
static unsigned prefetch_hinted400,prefetch_pop400;
static uint16_t prefetch_token400,prefetch_generation400;
extern unsigned save_display400(void);
void source_prefetch_policy400(unsigned enabled){prefetch_enabled400=enabled!=0;}
void cancel_prefetch400(void){prefetched400=prefetch_busy400=prefetch_groups400=prefetch_partial400=0;}
static unsigned source_receive_core400(void){''')
 s=once(s,'unsigned generation=receiver280.valid?(uint16_t)(receiver280.generation+1):1;\n unsigned pop=0,hinted=0;source_blocks367=source_empty367=source_hint_count367=source_hint_tags367=0;', '''unsigned continuing=prefetch_partial400;
 unsigned generation=continuing?prefetch_generation400:receiver280.valid?(uint16_t)(receiver280.generation+1):1;
 unsigned pop=continuing?prefetch_pop400:0,hinted=continuing?prefetch_hinted400:0;
 if(!continuing)source_blocks367=source_empty367=source_hint_count367=source_hint_tags367=0;
 prefetch_partial400=0;''')
 s=once(s,'if(!n){source_empty367++;irq_begin284();wait284();continue;}', '''if(!n){source_empty367++;
   if(prefetch_busy400){if(continuing){prefetch_partial400=1;prefetch_pop400=0;}irq_end284();return 2;}
   irq_begin284();wait284();continue;}''')
 s=once(s,'  source_blocks367++;\n  if(!hinted){', '  source_blocks367++;\n  if(prefetch_busy400)prefetch_groups400|=geometry_groups367;\n  if(!hinted){')
 s=once(s,'   w=source_buffer367();w[0]=0xd5;', '''   if(prefetch_busy400){prefetch_token400=token;prefetch_generation400=generation;irq_end284();return 1;}
   w=source_buffer367();w[0]=0xd5;''')
 s=once(s,'  pop=1;\n }', '''  pop=1;
  if(prefetch_busy400){prefetch_generation400=generation;prefetch_partial400=1;prefetch_pop400=1;irq_end284();return 3;}
 }''')
 s+='''
unsigned source_prefetch400(void){
 if(!prefetch_enabled400||prefetched400==1||prefetch_busy400||receiver280.serial<3)return 1;
 if(source_cancel367||source_error367||!save_display400())return 0;
 unsigned continuing=prefetched400==2;
 unsigned serial=receiver280.serial+(continuing?0:1),epoch=receiver280.epoch,mode=hint_mode367;
 uint16_t generation=(uint16_t)(receiver280.generation+(continuing?0:1));
 prefetch_attempts400++;prefetch_busy400=1;if(!continuing)prefetch_groups400=0;hint_mode367=0;
 unsigned ok=source_receive_core400();hint_mode367=mode;prefetch_busy400=0;
 if(ok==2)return 2;
 if(ok==3&&prefetch_partial400&&receiver280.serial==serial&&receiver280.epoch==epoch&&
    receiver280.generation==generation){
  prefetched400=2;prefetch_yields400++;return 2;
 }
 if(!ok||!receiver280.valid||receiver280.phase||receiver280.serial!=serial||
    receiver280.epoch!=epoch||receiver280.generation!=generation)return source_fail367(11);
 prefetched400=1;prefetch_completions400++;return 2;
}
unsigned source_receive367(void){
 if(!prefetched400)return source_receive_core400();
 unsigned partial=prefetched400==2;
 if(source_cancel367||source_error367||(partial?(!prefetch_partial400||!receiver280.phase):(!receiver280.valid||receiver280.phase)))return source_fail367(12);
 prefetched400=0;geometry_groups367=prefetch_groups400;
 unsigned bytes=source_hint367();
 if(bytes){if(!physical267(source_buffer367(),bytes))return source_fail367(13);source_hint_count367++;}
 if(partial){prefetch_hinted400=bytes!=0;unsigned ok=source_receive_core400();if(ok)prefetch_completions400++;return ok;}
 uint8_t *w=source_buffer367();w[0]=0xd5;w[1]=(uint8_t)(prefetch_token400>>8);w[2]=(uint8_t)prefetch_token400;
 w[3]=(uint8_t)prefetch_generation400;w[4]=(uint8_t)(prefetch_generation400>>8);w[5]=3;
 w[6]=(uint8_t)source_crc8_367(w,6);w[7]=0xa5;
 if(!physical267(w,8))return source_fail367(14);
 source_token367++;irq_end284();
 return 1;
}
'''
 p.write_text(s,newline='\n')
 p=d/'nes_refill267.c';s=p.read_text()
 s=once(s,'static unsigned finish_core284(void){', 'extern unsigned source_prefetch400(void);\nstatic unsigned finish_core284(void){')
 s=once(s,'if(sent){if(plan_flags282==1&&plan_accepted282==0)return 1;}', '''if(sent){if(plan_flags282==1&&plan_accepted282==0)return 1;
   unsigned received400=source_prefetch400();if(!received400)return 0;
   /* D4 owns the same SPI/GPIO. Refresh the old plan namespace afterwards. */
   if(received400==2){plan_cache282=0;wait_armed284=0;}
  }''')
 p.write_text(s,newline='\n')
