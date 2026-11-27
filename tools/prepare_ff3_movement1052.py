"""Build paired FF3 diagnostics from the routed 1051D source and linked input tree."""
import argparse
from pathlib import Path
import shutil
from prepare_nes_kirby1023 import edit

ROOT = Path(__file__).resolve().parents[1]

def board(base, dest):
    shutil.copytree(base/'board-d', dest)
    edit(dest,'fxpak_nes_screen137_top.sv',('nes_screen_status151 screen_status(', 'nes_screen_status151 screen_status(.directions(pad_buttons[11:8]),'))
    edit(dest,'nes_screen_status151.sv',('module nes_screen_status151(', 'module nes_screen_status151(input wire [3:0] directions,'),
         ('nes_display1010 trace(', 'nes_display1010 trace(.directions(directions),'))
    # Dedicate the optional PPU fault-detail snapshot to timing probes.
    # ROM fault code, STOP and every functional checker remain live.
    edit(dest,'nes_run_observer134.sv',
         ("7'd0,context_valid,first_ppu154[63:24]", "8'd0,40'd0"),
         ("7'd0,context_valid,first_ppu154[23:0]", "8'd0,24'd0"))
    edit(dest,'nes_run_observer134.sv',
         ("7'd0,context_valid,first_context[63:24]", "8'd0,40'd0"),
         ("7'd0,context_valid,first_context[23:0]", "8'd0,24'd0"))
    p=dest/'nes_display1010.sv'
    s=p.read_text().replace('module nes_display1010(', 'module nes_display1010(input wire [3:0] directions,')
    p.write_text(s[:s.index(' reg clear_record;')]+(ROOT/'tests/nes-functional/ff3_movement1052.svh').read_text())

def arm(base,dest,edition):
    shutil.copytree(base/'link',dest,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    src=dest/'src'
    for name in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
        edit(src,name,('ff31051',f'ff3{edition}'))
    if edition==1052:
        edit(src,'nes_native165.c',('version ? 256+(flags>>1)', 'version ? (1u<<(flags>>4))'))
    edit(src,'nes_checkpoint_gpio.inc',('ff3_next_slot=0;', 'extern unsigned char movement_slot;\n    movement_slot=slot;\n    ff3_next_slot=0;'))
    edit(src,'nes_savefile.c',('if(ok && load) ok=crc==h.crc;', '''if(ok && load) {
        extern uint32_t movement_save[3];
        ok=crc==h.crc;
        if(ok && id.slot){movement_save[0]=h.rom_crc;movement_save[1]=h.serial;movement_save[2]=h.crc;}
    }'''))
    path=src/'nes_budget210.c'
    s=path.read_text()
    start=s.index('static struct mark900')
    end=s.index('memset(&nes_budget210',start)
    s=s[:start]+(ROOT/'tests/nes-functional/ff3_movement1052.inc').read_text().replace('EDITION1052',str(edition))+'\n'+s[end:]
    s=s.replace('if(elapsed>=5500 && elapsed<6000)++log900p->displayed55;', '')
    path.write_text(s.replace('record900(s->frame_start,v);','record900(elapsed,v);'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('work',type=Path)
    p.add_argument('part',choices=['board','1052','1053'])
    args=p.parse_args()
    base=args.work.parent/'nes-ff3-1051B'
    if args.part=='board':
        board(base,args.work/'board-c')
    else:
        arm(base,args.work/args.part/'link',int(args.part))
