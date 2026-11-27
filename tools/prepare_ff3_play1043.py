"""Prepare the FF3 play firmware, with bounded checkpoint and report buffers."""
import argparse
import shutil
from pathlib import Path

from prepare_nes_browser1036 import prepare
from prepare_nes_kirby1023 import edit


def play(dest,interactive=False):
    prepare(dest, measure_storage=True)
    menu = dest / "src/nes_menu_diagnostic.c"
    text = menu.read_text()
    start = text.index(" char text[6144];", text.index("static void save_report("))
    end = text.index(" if(!persist)return;", start)
    # Keep the physical failure and STOP/return fields in this play profile.
    # The benchmark decoder is not needed to persist an interactive session.
    text = text[:start] + r''' char text[320];
 int n=snprintf(text,sizeof text,
     "board=%02x rom_crc=%08lx start=%u error=%u rom_error=%u screen=%02x "
     "screen_error=%02x frames=%lu final_generation=%u stop=%u base_safe=%u menu=%s\n",
     (unsigned)nes_board_id,(unsigned long)nes_content_crc,nes_run136.start_sent,
     nes_run136.first_error,nes_run136.rom_error,nes_run136.screen_stage,
     nes_run136.screen_error,(unsigned long)native_runtime165.frames,native_runtime165.generation,
     nes_run136.stop_ok,safe_to_reload,menu_state);
 if(n<=0 || (unsigned)n>=sizeof text)return;
 printf("%s",text);
''' + text[end:]
    menu.write_text(text)
    if interactive:
        src=dest/'src'
        # Separate interactive save and boot logs from the timed 1036 browser.
        for name,count in (('nes_checkpoint112.c',1),('nes_menu_diagnostic.c',2)):
            source=src/name
            old=source.read_text()
            assert old.count('mmc1036')==count, name
            source.write_text(old.replace('mmc1036','ff31044'))
        shutil.copy2(Path(__file__).resolve().parents[1]/'src/nes/nes_menu_play.inc',src)
        edit(src,'nes_runtime_board165.inc',
             ('/* Large RUN storage', '#include "nes_savefile.h"\n#include "nes_menu_play.inc"\n/* Large RUN storage'),
             ('NULL,6000,&work.resident','NULL,nes_board_id==0x7d?0x7fffffffu:6000,&work.resident'),
             (' while(nes_runtime165_step(&native_runtime165)){}',''' ff3_menu_open=false;
 while(!native_runtime165.result){
  if(nes_board_id==0x7d && !ff3_play_step(io)){
   native_runtime165.result=NES_RUNTIME165_SERVICE;break;
  }
  if(!ff3_menu_open && !native_runtime165.result && !nes_runtime165_step(&native_runtime165))break;
 }'''))
        edit(src,'nes_checkpoint_gpio.inc',
             ('int nes_menu_state_io(','''static bool ff3_pause_menu(void)
{
    return gpio_owned && !native_runtime165.inside_transfer &&
           nes_state_pause(checkpoint_exchange,ff3_drain_frame,&native_runtime165);
}
static int ff3_slot_exists(unsigned slot)
{
    struct nes_save_id id={nes_content_crc,NES_CART_BYTES,slot};
    return nes_savefile_available(id,21264);
}
int nes_menu_state_io('''),
             ('int result=nes_menu_state_io(0,true);','''const unsigned slot=ff3_next_slot;
    ff3_next_slot=0;
    if(slot)return nes_state_pause(checkpoint_exchange,NULL,NULL) &&
                   nes_menu_state_io(slot,true)==NES_SAVE_OK && nes_menu_state_resume();
    int result=nes_menu_state_io(0,true);'''))
        edit(src,'nes_h1_stm32.c',
             (' total=NES_CART_BYTES;\n crc=load_crc(crc,header,16);',''' total=NES_CART_BYTES;
 if(ff3_next_slot){
  expected_crc=nes_content_crc;
  memcpy(buffer,header,16);
  goto verify_payload;
 }
 crc=load_crc(crc,header,16);'''),
             (' struct sd_source_context ctx={&file,r,&opened,total,expected_crc,',
              'verify_payload: ;\n struct sd_source_context ctx={&file,r,&opened,total,expected_crc,'),
             ('  if(!run136(&io,NES_CART_BYTES,r,nes_content_crc)||','''  ff3_next_slot=0;
  bool session_ok;
  do {
   session_ok=run136(&io,NES_CART_BYTES,r,nes_content_crc);
   if(!session_ok || !ff3_next_slot || !nes_run136.passed || !r->stop_ok)break;
   // STOP keeps PSRAM but revokes CHECK_FINISH. Recompare the full selected
   // file and require a fresh FINISH before START may reset display ownership.
   report->verified=false;
   session_ok=prepare_rom893(path,image,expected_chr32,candidate,&io,&changed_fpga,&begin_sent);
   if(!session_ok)break;
   memset(&nes_run136,0,sizeof nes_run136);
   memset(&native_runtime165,0,sizeof native_runtime165);
   r->stop_ok=false;
  }while(true);
  ff3_next_slot=0;
  if(!session_ok||'''))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument('--interactive',action='store_true')
    args=parser.parse_args()
    play(args.out,args.interactive)
