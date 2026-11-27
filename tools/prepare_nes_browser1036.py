"""Build the .nes browser edition from the hardware-tested 1035 ARM source tree."""
import argparse
import shutil
from pathlib import Path

from prepare_nes_ff3_checkpoint import BASE, OUT, ROOT
from prepare_nes_kirby1023 import edit
from prepare_nes_trial802 import rename_edition


def prepare(dest, measure_storage=False):
    src = dest / "src"
    if not dest.exists():
        shutil.copytree(BASE / "link", dest)
    edition = dest / "browser-edition"
    if not edition.exists():
        rename_edition(BASE / "link/src", edition, 1035, 1036)
    for name in ("Makefile", "nes_mmc479.h", "main.c", "nes_menu_diagnostic.h", "filetypes.c",
                 "nes_h1_stm32.c", "nes_rom_verify.c", "nes_budget210.c","nes_run136.inc"):
        shutil.copy2(BASE / "link/src" / name, src / name)
    for file in edition.iterdir():
        shutil.copy2(file, src / file.name)
    shutil.copy2(ROOT / "src/nes/nes_browser.h", src)
    # A CHR-RAM address can describe different pixels on successive captures.
    # Keep slot allocation and same-frame dedup, but upload the selected
    # inactive bank's patterns again on its first use in each FF3 frame.
    shutil.copy2(BASE / "link/src/nes_resident211.c",src)
    edit(src,"nes_resident211.c",('#include "nes_resident211.h"',
         '#include "nes_resident211.h"\n#include "nes_mmc479.h"'),
         ("s->generation=generation;s->serial++;",
          "s->generation=generation;s->serial++;\n if(nes_board_id==0x7d) memset(s->resident[s->target],0,sizeof s->resident[s->target]);"))
    if measure_storage:
        driver="stm32f4xx/sdnative.c"
        shutil.copy2(BASE/"link/src"/driver,src/driver)
        edit(src,driver,("static DRESULT nes_return_sd_write(",
                         "extern bool nes_ff3_write_allowed(void);\nstatic DRESULT nes_return_sd_write("),
             ("if(!nes_return_log_allowed())return RES_WRPRT;",
              "if(!nes_return_log_allowed() && !nes_ff3_write_allowed())return RES_WRPRT;"),
             ("for(UINT n=0;n<count;n++){\n  uint32_t address=sector+n;if(!ccs)address<<=9;",
              """for(UINT n=0;n<count;n++){
  if(!nes_return_log_allowed() && !nes_ff3_write_allowed())return RES_WRPRT;
  uint32_t address=sector+n;if(!ccs)address<<=9;"""))
        for name in ("nes_savefile.h", "nes_savefile.c","nes_checkpoint_host.h",
                     "nes_checkpoint_host.c","nes_checkpoint_gpio.inc"):
            shutil.copy2(ROOT / "src/nes" / name,src/name)
        edit(src,"Makefile",("nes_cost471.c nes_h1_session.c", "nes_checkpoint_host.c nes_savefile.c nes_cost471.c nes_h1_session.c"),
             ("LDFLAGS += -T$(LINKERSCRIPT)", "LDFLAGS += -T$(LINKERSCRIPT) -Wl,-u,nes_menu_state_io,-u,nes_menu_state_resume"))
    edit(src, "filetypes.c", ('(!strcasecmp(ext+1, "NH1"))', '(!strcasecmp(ext+1, "NES"))'))
    edit(src, "nes_budget210.c", ("edition=1035", "edition=1036"))
    (src / "nes_mmc479.h").write_text("""#pragma once
#include <stdint.h>
extern uint8_t nes_board_id;
extern uint32_t nes_content_crc;
#define NES_MMC479_BOARD_ID nes_board_id
#define NES_CART_BYTES (nes_board_id == 0x7d ? 0x80000u : 0xc0000u)
""")
    edit(src, "nes_menu_diagnostic.h", ("/* Manual-only compile candidate. Marker selects a fixed approved fixture;\n * neither the marker contents nor an arbitrary browser path becomes a ROM. */",
         "/* Select an iNES image using its SD path and cartridge header. */"),
         ("bool nes_menu_diagnostic_marker",
         "bool nes_menu_select_rom(const uint8_t *path);\nbool nes_menu_diagnostic_marker"))
    main = src / "main.c"
    source = main.read_text()
    marker = "if(nes_menu_diagnostic_marker(file_lfn)) {"
    assert source.count(marker) == 3
    # The old NH1-only hardware smoke runner is unreachable from this browser.
    start = source.index("          if(nes_h1_is_marker(file_lfn))")
    end = source.index("          cfg_add_listed_game", start)
    legacy = source[start:end]
    assert source.count(legacy) == 3
    source = source.replace(legacy, "")
    main.write_text(source.replace(marker, marker + """
            if(!nes_menu_select_rom(file_lfn)) { cmd=0; break; }"""))
    menu = src / "nes_menu_diagnostic.c"
    source = menu.read_text()
    start = source.index("static __attribute__((noipa)) unsigned marker_geometry")
    end = source.index("/* SPDX-License", start)
    source = source[:start] + r'''#include "nes_browser.h"
#include "nes_mmc479.h"
uint8_t nes_board_id;
uint32_t nes_content_crc;
/* Directory scanning uses file_lfn as scratch. Retain the path through readback. */
static char selected_rom[sizeof file_lfn];
bool nes_menu_diagnostic_marker(const uint8_t *path) { return nes_filename(path); }
bool nes_menu_select_rom(const uint8_t *path) {
 FIL file;
 uint8_t header[16];
 UINT count;
 unsigned id=0;
 const char *error="Unsupported NES mapper or memory layout";
 size_t len=strnlen((const char *)path,sizeof selected_rom);
 bool irq=NVIC_GetEnableIRQ(OTG_FS_IRQn)!=0;
 NVIC_DisableIRQ(OTG_FS_IRQn);
 if(len<sizeof selected_rom) memcpy(selected_rom,path,len+1);
 if(len<sizeof selected_rom && f_open(&file,selected_rom,FA_READ)==FR_OK){
  if(f_read(&file,header,sizeof header,&count)==FR_OK && count==sizeof header)
   id=nes_image_id(header,f_size(&file));
  if(f_close(&file)!=FR_OK){id=0;error="NES file close failed";}
 }else error="Cannot open selected NES file";
 if(irq) NVIC_EnableIRQ(OTG_FS_IRQn);
 nes_board_id=id;
 if(!id){
  char message[64]={0};
  strcpy(message,error);
  snes_menu_errmsg(MENU_ERR_NOIMPL,message);
  return false;
 }
 return true;
}
''' + source[end:]
    source = source.replace(" unsigned selected=marker_geometry(path);\n if(!selected||pending)",
                            " if(!nes_board_id||pending)")
    source = source.replace(" /* Each accepted diagnostic marker loads the same 384 KiB ROM. */\n mode900=selected>>3;\n nes_boot_probe798=selected&3;",
                            " mode900=0;\n nes_boot_probe798=0;")
    source = source.replace('"/sd2snes/nes/mmc1036.nes"', "selected_rom")
    source = source.replace('"/sd2snes/fpga_mmc1036.bi3"', 'nes_board_id==0x7d?"/sd2snes/nes-chrram.bi3":"/sd2snes/nes-chrrom.bi3"')
    source = source.replace("enum { geometry=384 };", '#include "nes_mmc479.h"\n#define geometry (NES_CART_BYTES/1024u)')
    source = source.replace("_hex=7b", "_hex=%02x").replace("  report.board_seen,report.board_id,geometry,",
                           "  (unsigned)nes_board_id,report.board_seen,report.board_id,geometry,")
    if measure_storage:
        # The interactive play edition retains the binary frame trace and
        # the loader, STOP and base recovery report. Omit the benchmark's
        # second, human-readable timing report from this link.
        start=source.index(" int budget_n=nes_budget210_format")
        end=source.index(' write_report893("/sd2snes/nes-frame-',start)
        source=source[:start]+source[end:]
    menu.write_text(source)
    loader = src / "nes_h1_stm32.c"
    source = loader.read_text()
    start = source.index(" /* Exact target Kirby")
    end = source.index(" crc=load_crc(crc,header,16);",start)
    source = source[:start] + """ if(!nes_board_id || expected_chr32 ||
    nes_image_id(header,f_size(&file))!=nes_board_id){
  r->result=NES_MCU_LOAD_HEADER;goto cleanup;
 }
 r->chr_32k=false;
 total=NES_CART_BYTES;
""" + source[end:]
    source = source.replace('#include "nes_mmc479.h"', '#include "nes_mmc479.h"\n#include "nes_browser.h"')
    prefix, marker, active = source.partition("bool prepare_rom893(")
    assert marker
    source = prefix + marker + active.replace("if((crc^0xffffffffu)!=expected_crc){r->result=NES_MCU_LOAD_CONTENT;goto cleanup;}",
                                              "expected_crc=nes_content_crc=crc^0xffffffffu;", 1)
    source = source.replace("0xc0000u,r,NES_MMC479_ROM_CRC","NES_CART_BYTES,r,nes_content_crc")
    source = source.replace("0xc0000u,0xc0000u","NES_CART_BYTES,NES_CART_BYTES")
    source = source.replace("s->count<=0xc0000","s->count<=NES_CART_BYTES")
    loader.write_text(source)
    if measure_storage:
        with loader.open("a") as f:
            f.write('\n#include "nes_checkpoint_gpio.inc"\n')
        edit(src,"nes_run136.inc",("static __attribute__((noinline,noclone)) bool run136(",
             "extern bool nes_restore_boot_battery(void);\nstatic __attribute__((noinline,noclone)) bool run136("),
             (" bool released222=nes_boot_probe798!=1 && native_session165(io,content_epoch);",
              """ bool battery_ok=nes_board_id!=0x7d || nes_restore_boot_battery();
 if(!battery_ok)nes_run136.first_error=11;
 bool released222=battery_ok && nes_boot_probe798!=1 && native_session165(io,content_epoch);"""))
    edit(src, "nes_rom_verify.c", ("length!=0xc0000","length!=NES_CART_BYTES"),
         ("length==0xc0000","length==NES_CART_BYTES"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT/"browser-link")
    parser.add_argument("--measure-storage",action="store_true",help="retain both FatFS entry points in the Flash budget")
    args=parser.parse_args()
    prepare(args.out,args.measure_storage)

