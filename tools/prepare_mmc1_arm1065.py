"""Add the SXROM profile and its file geometry to the two 1064 ARM links."""
from pathlib import Path
from shutil import copytree
from prepare_nes_headers1064 import OUT as PREVIOUS
from prepare_nes_kirby1023 import edit
from prepare_sxrom1065 import OUT

def prepare(mode):
    link=OUT/mode/"link"
    copytree(PREVIOUS/mode/"link",link,dirs_exist_ok=True)
    src=link/"src"
    edit(src,"nes_cartridge_header.h",(" if(c->format==NES_20) {",""" // Legacy byte 8 == 0 is ambiguous. The loader must resolve that case
 // against the full image before activating this provisional board ID.
 if(c->mapper==1 && (c->wiring&14)==2 && c->prg_size==524288 && !c->chr_size &&
    ((c->format==NES_20 && !c->submapper && c->work_ram==0x90 && c->pattern_ram==7) ||
     (c->format==NES_INES && (!c->work_ram || c->work_ram==4))))return 0x86;
 if(c->format==NES_20) {"""))
    edit(src,"nes_menu_diagnostic.c",('[0x85-0x7c]="/sd2snes/nes-m1.bi3",','[0x85-0x7c]="/sd2snes/nes-m1.bi3",\n [0x86-0x7c]="/sd2snes/nes-sx.bi3",'))
    edit(src,"nes_mmc479.h",("(nes_board_id&0xfe)==0x84","(nes_board_id>=0x84 && nes_board_id<=0x86)"))
    # A size or CRC is insufficient to identify a file layout across profiles.
    # The active board has already been selected and revalidated at this point.
    edit(src,"nes_savefile.h",("static inline unsigned nes_state_bytes","extern uint8_t nes_board_id;\nstatic inline unsigned nes_battery_bytes(void){return nes_board_id==0x86 ? 32768u : 8192u;}\nstatic inline unsigned nes_state_bytes"),("return id.rom_bytes==","if(nes_board_id==0x86)return 45840u;\n    return id.rom_bytes=="))
    edit(src,"nes_savefile.c",("bytes==8192","bytes==nes_battery_bytes()"),("nes_state_bytes(id):8192","nes_state_bytes(id):nes_battery_bytes()"))
    edit(src,"nes_checkpoint_host.c",("nes_state_bytes(id):BAT_BYTES","nes_state_bytes(id):nes_battery_bytes()"))
    file,crc=("nes_retail_preload1054.inc","~crc") if mode=="release" else ("nes_h1_stm32.c","expected_crc")
    edit(src,file,(f"(nes_board_id==0x84 && {crc}",f"(nes_board_id==0x86 && (header[7]&12)!=8 && header[8]!=4 && {crc}!=0x6f8906adu) || (nes_board_id==0x84 && {crc}"))
    if mode=="debug":
        # All four call sites compare SD filenames only. Avoid pulling in the
        # general-purpose unrolled libc strcmp just for these short strings.
        for f in ("filetypes.c","fpga.c","memory.c","nes_h1_stm32.c"):
            path=src/f
            text=path.read_text()
            assert "strcmp(" in text
            path.write_text('#include "nes_path_compare1065.h"\n'+text.replace("strcmp(","nes_path_compare1065("))
        (src/"nes_path_compare1065.h").write_bytes((Path(__file__).resolve().parents[1]/"src/nes/nes_path_compare1065.h").read_bytes())
        for f in ("nes_menu_diagnostic.c","nes_checkpoint112.c"):edit(src,f,("debug1064","debug1065"))
        edit(src,"nes_checkpoint112.c",("DEBUG1064","DEBUG1065"))
        edit(src,"nes_budget210.c",("movement->edition=1064","movement->edition=1065"))
if __name__=="__main__":
    for mode in ("debug","release"):prepare(mode)
