"""Derive isolated H1 STM32 firmware; preserve pinned C44 tools and overlay."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def replace(text,old,new,count=1):
    if text.count(old)!=count:
        raise RuntimeError("Unexpected pinned source shape: "+repr(old))
    return text.replace(old,new)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--upstream",type=Path,required=True)
    a=p.parse_args()
    subprocess.run([sys.executable,"-B",str(ROOT/"tools/prepare_firmware.py"),
                    "--out",str(a.out),"--upstream",str(a.upstream)],check=True)
    src=a.out/"src"
    names=("nes_h1_session.c","nes_h1_session.h","nes_h1_stm32.c","nes_h1_stm32.h")
    for name in names:
        shutil.copy2(ROOT/"src/nes/firmware"/name,src/name)
    main=(src/"main.c").read_text()
    main=replace(main,'#include "config.h"','#include "config.h"\n#include "nes_h1_stm32.h"')
    main=replace(main,"  while(1) {\n    snes_boot_configured = 0;",
                      "  while(1) {\nnes_h1_reload_menu:\n    snes_boot_configured = 0;")
    # Manual LOADROM/LAST/FAVORITE only. Intercept before adding to recents.
    old="          cfg_add_listed_game(LAST_FILE, file_lfn, true);\n          filesize = load_rom"
    new="""          if(nes_h1_is_marker(file_lfn)) {
            if(!nes_h1_run()) {
              led_panic(LED_PANIC_FPGA_NOCONF);
              for(;;); /* fail closed if a platform panic unexpectedly returns */
            }
            goto nes_h1_reload_menu;
          }
          cfg_add_listed_game(LAST_FILE, file_lfn, true);
          filesize = load_rom"""
    main=replace(main,old,new,3)
    main=replace(main,"          if(file_lfn[0]) {",
                      "          if(file_lfn[0] && !nes_h1_is_marker(file_lfn)) {")
    (src/"main.c").write_text(main,newline="\n")
    ft=(src/"filetypes.c").read_text()
    ft=replace(ft,'     ||(!strcasecmp(ext+1, "EGBC"))',
                  '     ||(!strcasecmp(ext+1, "EGBC"))\n     ||(!strcasecmp(ext+1, "NH1"))')
    (src/"filetypes.c").write_text(ft,newline="\n")
    mk=(src/"Makefile").read_text()
    mk=replace(mk,"SRC  = main.c ff.c ccsbcs.c",
                  "SRC  = main.c ff.c ccsbcs.c\nSRC += nes_h1_session.c nes_h1_stm32.c")
    (src/"Makefile").write_text(mk,newline="\n")
    paths=list(names)+["main.c","filetypes.c","Makefile"]
    (a.out/"h1-preparation.json").write_text(json.dumps({
        "candidate":"NES-H1-FIRMWARE-035","fpga_protocol_candidate":"NES-H1-BOARD-034",
        "manual_entry_hooks":3,"autoboot_marker":"NACK",
        "files":{n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in paths}
    },indent=2)+"\n")
    print("Prepared isolated H1: 3 manual hooks; autoboot marker NACK")
if __name__=="__main__":main()
