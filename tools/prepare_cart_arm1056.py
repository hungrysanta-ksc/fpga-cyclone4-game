"""Bind the selected iNES geometry to both the MCU load and FPGA identity check."""
import argparse
import shutil
from prepare_nes_carts1056 import OUT, CARTS
from prepare_nes_kirby1023 import edit

def prepare(edition):
    src = OUT / edition / "link/src"
    shutil.copytree(OUT.parent/"nes-pair1055"/edition/"link",src.parent,dirs_exist_ok=True)
    browser=src/"nes_browser.h"
    original=browser.read_text()
    start=original.index("static inline unsigned nes_image_id")
    browser.write_text(original[:start]+"unsigned nes_image_id(const uint8_t h[16],uint32_t file_size);\n#endif\n")
    host=src/"nes_menu_diagnostic.c"
    sizes={"0x7c":"nes-chrrom","0x7d":"nes-chrram"}
    sizes.update({hex(ident):f"nes-m{mapper}" for mapper,(ident,_,_) in CARTS.items()})
    paths=",\n".join(f' {{ {k}, "/sd2snes/{v}.bi3" }}' for k,v in sizes.items())
    classifier = """
uint32_t nes_cart_bytes,nes_prg_bytes;
static const struct {uint8_t id;const char *file;} boards[]={
@PATHS@
};
static const char *nes_board_file;
unsigned nes_image_id(const uint8_t h[16],uint32_t size){
 if(memcmp(h,"NES\\032",4) || size!=16u+16384u*h[4]+8192u*h[5])return 0;
 unsigned id=0;
 if(h[7]==8 && h[6]==0x52 && h[4]==64 && !h[5] &&
    !memcmp(h+8,"\\000\\000\\160\\007\\000\\000\\000\\000",8))return 0x84;
 if(h[8]>1)return 0;
 for(unsigned i=9;i<16;i++)if(h[i])return 0;
 if(!h[7] && (h[6]&~2u)==0x40 && h[4]==32){
  if(h[5]==32)id=0x7c;
  if(!h[5])id=0x7d;
 }else if(!h[7] && h[6]==0x31 && h[4]==2 && h[5]==4)id=0x81;
 else if(!h[7] && h[6]==0x70 && h[4]==32 && !h[5])id=0x82;
 else if(h[7]==0x10 && h[6]==0x50 && h[4]==16 && h[5]==16)id=0x83;
 return id;
}
""".replace("@PATHS@",paths)
    old="id=nes_image_id(header,f_size(&file));"
    edit(src,host.name,("#define geometry (NES_CART_BYTES/1024u)","#define geometry ((unsigned)(NES_CART_BYTES/1024u))"),
         ("uint32_t nes_content_crc;","uint32_t nes_content_crc;"+classifier),
         (old,"""{
   id=nes_image_id(header,f_size(&file));
   nes_prg_bytes=header[4]*16384u;
   nes_cart_bytes=f_size(&file)-16u;
   nes_board_file=NULL;
   for(unsigned i=0;i<sizeof boards/sizeof *boards;i++)
    if(boards[i].id==id)nes_board_file=boards[i].file;
   if(!nes_board_file)id=0;
  }"""),
         ('nes_board_id==0x7d?"/sd2snes/nes-chrram.bi3":"/sd2snes/nes-chrrom.bi3"',"nes_board_file"))
    edit(src,"nes_mmc479.h",("#define NES_CART_BYTES (nes_board_id == 0x7d ? 0x80000u : 0xc0000u)",
         "extern uint32_t nes_cart_bytes,nes_prg_bytes;\n#define NES_CART_BYTES nes_cart_bytes\n#define NES_PATTERN_RAM (nes_board_id==0x7d || nes_board_id==0x82 || nes_board_id==0x84)"))
    for name in ("nes_native165.c","nes_planner211.c","nes_native_runtime165.c"):
        f=src/name
        f.write_text(f.read_text().replace("nes_board_id==0x7d","NES_PATTERN_RAM")
                     .replace("nes_board_id!=0x7d","!NES_PATTERN_RAM"))
    edit(src,"nes_h1_stm32.c",("(rx[4]&0xf0)","(rx[4]&0xe0)"))
    # Pattern-RAM boards hold the CPU until the checkpoint port acknowledges
    # RESUME. AxROM has no battery. ExROM has 8 KiB of battery-backed RAM.
    edit(src,"nes_run136.inc",("nes_board_id!=0x7d || nes_restore_boot_battery()",
         "!NES_PATTERN_RAM || nes_restore_boot_battery()"))
    edit(src,"nes_checkpoint_gpio.inc",
         ("gpio_owned && nes_board_id==0x7d","gpio_owned && (nes_board_id==0x7d || nes_board_id==0x84)"),
         ("if(nes_board_id!=0x7d || (!borrowed && !slow_begin())) return NES_SAVE_IO;",
          "if((nes_board_id!=0x7d && (slot || nes_board_id!=0x84)) || (!borrowed && !slow_begin())) return NES_SAVE_IO;"),
         ("if(nes_board_id!=0x7d || (!borrowed && !slow_begin())) return false;",
          "if(!NES_PATTERN_RAM || (!borrowed && !slow_begin())) return false;"),
         ("const unsigned slot=ff3_next_slot;", "if(nes_board_id==0x82)return nes_menu_state_resume();\n    const unsigned slot=ff3_next_slot;"))
    edit(src,"nes_savefile.c",("id.rom_bytes==0xc0000u","id.rom_bytes==0xc0000u || (!id.slot && id.rom_bytes==0x100000u)"))
    edit(src,"nes_runtime_board165.inc",("nes_board_id==0x7d?", "NES_PATTERN_RAM?"),
         ("nes_board_id==0x7d && !ff3_play_step","NES_PATTERN_RAM && !ff3_play_step"))
    # Only the original MMC3 RAM board contains the complete mapper snapshot.
    # A disabled slot operation is recoverable and must not exit the game.
    edit(src,"nes_menu_play.inc",("}else if(ff3_menu_open){","""}else if(ff3_menu_open){
        if(nes_board_id!=0x7d && ((req>=0x10 && req<=0x23) || (req==2 && nes_board_id!=0x84)))
            return ff3_mail(io,req,2,&req);"""))
    if edition=="release":
        edit(src,"nes_retail_preload1054.inc",("off>=0x80000","off>=nes_prg_bytes"),
             ("(off-0x80000u)","(off-nes_prg_bytes)"),
             (" ok=true;"," if(nes_board_id==0x84 && ~crc!=0x9ac62bb9u){r->result=NES_MCU_LOAD_HEADER;goto closed;}\n ok=true;"))
    else:
        platform=src/"nes_diag_platform.c"
        old=platform.read_text()
        a=old.index(" unsigned quarter=")
        b=old.index("\n}",a)
        # SD breadcrumbs and LEDs already track loader progress; duplicate UART
        # quarter announcements consumed space in the constrained debug link.
        old=old[:a]+old[b:]
        platform.write_text(old)
        edit(src,"nes_h1_stm32.c",("expected_crc=crc^0xffffffffu;","expected_crc=crc^0xffffffffu;\n if(nes_board_id==0x84 && expected_crc!=0x9ac62bb9u){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}"))
        # Cross-unit size optimization for the SD file services, outside RUN.
        cold=("ff","ccsbcs","fileops","cfg","nes_savefile","nes_checkpoint_host",
              "nes_menu_return","nes_menu076","nes_diag_runtime","nes_diag_platform",
              "nes_css108","nes_menu_diagnostic","nes_checkpoint112","nes_rom_verify","nes_h1_session")
        edit(src,"Makefile",("$(CC) $(ALL_CFLAGS) $^ --output $@ $(LDFLAGS)",
                            "$(CC) $(filter-out -Wa%,$(ALL_CFLAGS)) $^ --output $@ $(LDFLAGS)"),
             ("CFLAGS += -Wa,-adhlns=$(OBJDIR)/$(<:.c=.lst)","# LTO output must remain object paths; omit assembler listings in this edition."))
        with (src/"Makefile").open("a") as f:
            f.write("\n"+" ".join("$(OBJDIR)/"+name+".o" for name in cold)+" : CFLAGS += -flto -Oz\n")
        for name in cold:
            (src/(name+".c")).touch()
        for name in ("nes_checkpoint112.c","nes_menu_diagnostic.c","nes_frame900.c"):
            f=src/name
            if f.exists():f.write_text(f.read_text().replace("debug1055","debug1056"))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("edition",choices=("debug","release"))
    prepare(p.parse_args().edition)
