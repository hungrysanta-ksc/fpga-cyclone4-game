"""Prepare the diagnostic movement trace on the DQ4 board only."""
from shutil import copytree
from prepare_cart_debug1060 import OUT as BASE
from prepare_cart_state1059 import OUT as BOARDS
from prepare_nes_carts1056 import ROOT
from prepare_nes_kirby1023 import edit

OUT = BASE.parent / "nes-dq4-movement1061"


def board():
    dst=OUT/"board"
    copytree(BOARDS/"board-5",dst,dirs_exist_ok=True)
    edit(dst,"fxpak_nes_screen137_top.sv",("nes_screen_status151 screen_status(","nes_screen_status151 screen_status(.directions(pad_buttons[11:8]),"))
    edit(dst,"nes_screen_status151.sv",("module nes_screen_status151(","module nes_screen_status151(input wire [3:0] directions,"),
         ("nes_display1010 trace(","nes_display1010 trace(.directions(directions),"))
    p=dst/"nes_display1010.sv"
    s=p.read_text().replace("module nes_display1010(","module nes_display1010(input wire [3:0] directions,")
    p.write_text(s[:s.index(" reg clear_record;")]+(ROOT/"tests/nes-functional/ff3_movement1052.svh").read_text())


def arm():
    dst=OUT/"debug/link"
    copytree(BASE/"debug/link",dst,dirs_exist_ok=True)
    src=dst/"src"
    for name in ("nes_checkpoint112.c","nes_menu_diagnostic.c"):
        edit(src,name,("debug1060","debug1061"))
    edit(src,"nes_checkpoint112.c",("DEBUG1060","DEBUG1061"))
    edit(src,"nes_checkpoint_gpio.inc",("const unsigned slot=ff3_next_slot;", """extern void dq4_new_session(void);
    dq4_new_session();
    const unsigned slot=ff3_next_slot;"""))
    edit(src,"nes_savefile.c",("return f_close(&file)==FR_OK && ok;", """ok=f_close(&file)==FR_OK && ok;
    if(ok && load && id.slot){
        extern void dq4_loaded(unsigned,uint32_t,uint32_t,uint32_t);
        dq4_loaded(id.slot,h.rom_crc,h.serial,h.crc);
    }
    return ok;"""))
    p=src/"nes_budget210.c"
    s=p.read_text()
    lo=s.index("static struct mark900")
    hi=s.index("memset(&nes_budget210",lo)
    p.write_text(s[:lo]+(ROOT/"tests/nes-functional/dq4_movement1061.inc").read_text()+s[hi:])
    edit(src,p.name,("if(elapsed>=5500 && elapsed<6000)++log900p->displayed55;",""),
         ("record900(s->frame_start,v);","record900(elapsed,v);"),
         ("b[B210_PLANS]++;","staged_bytes+=q->kind==1?32:16; b[B210_PLANS]++;"))
    (src/"nes_h1_stm32.c").touch()


if __name__=="__main__":
    import sys
    {"board":board,"arm":arm}[sys.argv[1]]()
