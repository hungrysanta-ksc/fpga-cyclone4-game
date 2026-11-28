"""Bind the 1062 loader and planner to the 1061 debug and verified release links."""
from shutil import copytree
from prepare_dq4_movement1061 import OUT as MEASURE, BASE, ROOT
from prepare_nes_kirby1023 import edit

OUT = MEASURE.parent/"nes-compat1062"


def build_source(mode):
    dst = OUT/mode/"link"
    copytree((MEASURE if mode=="debug" else BASE)/mode/"link", dst, dirs_exist_ok=True)
    src=dst/"src"
    file="nes_menu_diagnostic.c"
    original=(src/file).read_text()
    a=original.index(" if(h[7]==8")
    b=original.index(" if(h[8]>1)",a)
    # Keep legacy wiring decisions; admit NES2 only for representable boards.
    extra=(ROOT/"src/nes/nes_header1062.inc").read_text()
    (src/file).write_text(original[:a]+extra+original[b:])
    edit(src,file,("!h[7] && h[6]==0x31","!h[7] && (h[6]&0xfe)==0x30"))
    # Provisional horizontal CNROM requires the exact known legacy dump.
    guard="(nes_board_id==0x81 && header[6]==0x30 && CRC!=0x6118313fu)"
    if mode=="debug":
        edit(src,"nes_h1_stm32.c",("nes_board_id==0x84 && expected_crc!=0x9ac62bb9u",
             "(nes_board_id==0x84 && expected_crc!=0x9ac62bb9u) || "+guard.replace("CRC","expected_crc")))
        for n in (file,"nes_checkpoint112.c"):
            edit(src,n,("debug1061","debug1062"))
        edit(src,"nes_checkpoint112.c",("DEBUG1061","DEBUG1062"))
        edit(src,"nes_budget210.c",("movement->edition=1061","movement->edition=1062"))
    else:
        edit(src,"nes_retail_preload1054.inc",("nes_board_id==0x84 && ~crc!=0x9ac62bb9u",
             "(nes_board_id==0x84 && ~crc!=0x9ac62bb9u) || "+guard.replace("CRC","~crc")))
    # HDMA scratch is zeroed for each frame and overwritten with the true HDMA
    # stream after BG processing. A 14-bit tag has five bits above bit 8.
    edit(src,"nes_planner211.c",
        ("uint32_t cached;uint8_t *entry=p->hdma+4*(tag&255);memcpy(&cached,entry,4);",
         "uint16_t cached;unsigned signature=(tag>>9)+1;uint8_t *entry=p->hdma+2*(tag&511);memcpy(&cached,entry,2);"),
        ("(cached>>16)==tag+1","(cached>>10)==signature"),("slot=(uint16_t)cached;","slot=cached&1023;"),
        ("cached=((tag+1)<<16)|slot;memcpy(entry,&cached,4);","cached=(signature<<10)|slot;memcpy(entry,&cached,2);"),
        ("for(unsigned x=0;x<33;x++){\n  unsigned idx=(s->rows[first[g]]>>3)*33+x,cell=s->maps[idx];",
         "unsigned map_base=(s->rows[first[g]]>>3)*33, first_column=column225(s->raster[first[g]]);\n  for(unsigned x=0;x<33;x++){\n  unsigned cell=s->maps[map_base+x];"),
        ("(column225(s->raster[first[g]])+x)&63u","(first_column+x)&63u"))
    (src/"nes_h1_stm32.c").touch()


if __name__=="__main__":
    for edition in ("debug","release"):
        build_source(edition)
