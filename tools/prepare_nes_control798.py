"""Combine the physically played 763/764 pair with the PR160 loader and bounded boot probes."""
from prepare_nes_shared794 import ROOT, prepare, replace_once

WORK = ROOT.parent / "probes/nes-control798"


def build_patch(n):
    src = ROOT.parent / f"probes/nes-trial763/linked{n-35}/src"
    out = WORK / f"patch{n}"
    prepare(src, out, str(n-35), str(n))

    def edit(name, *changes):
        p = out / name
        s = (p if p.exists() else src/name).read_text()
        for old, new in changes:
            s = replace_once(s, old, new)
        p.write_text(s, newline="\n")

    edit("nes_menu_diagnostic.c",
         ("static unsigned geometry;", "static unsigned geometry;\nunsigned char nes_boot_probe798;"),
         (f' return !strcmp(name,"NES MMC3 {n}.nh1")?384:0;',
          f' if(!strcmp(name,"NES START {n}.nh1"))return 385;\n'
          f' if(!strcmp(name,"NES BOOT {n}.nh1"))return 386;\n return !strcmp(name,"NES MMC3 {n}.nh1")?384:0;'),
         (" entry_only113=selected==113;", """ nes_boot_probe798=(unsigned char)(selected-384);
 if(nes_boot_probe798)selected=384;
 entry_only113=selected==113;"""))
    edit("nes_run136.inc",
         ('#include "nes_runtime_board165.inc"', 'extern unsigned char nes_boot_probe798;\n#include "nes_runtime_board165.inc"'),
         ("static bool run136(", "static __attribute__((noinline,noclone)) bool run136("),
         ('nes_checkpoint112("DISPLAY_NEXT",0,total)', 'nes_checkpoint112("DISPLAY_NEXT",nes_boot_probe798,total)'),
         ("bool released222=native_session165(io,content_epoch);",
          "bool released222=nes_boot_probe798!=1 && native_session165(io,content_epoch);"),
         ("if(!nes_run136.first_error && (!nes_run136.first",
          "if(!nes_boot_probe798 && !nes_run136.first_error && (!nes_run136.first"),
         ("nes_run136.passed=nes_run136.error==0;", "nes_run136.passed=!nes_boot_probe798 && nes_run136.error==0;"),
         ('return nes_checkpoint112("DISPLAY_STOPPED",nes_run136.first,nes_run136.stopped);',
          '''/* These diagnostic endpoints are recorded only after reset and checked STOP. */
 if(nes_boot_probe798)return nes_checkpoint112("PROBE_STOPPED",nes_boot_probe798,nes_run136.error);
 return nes_checkpoint112("DISPLAY_STOPPED",nes_run136.first,nes_run136.stopped);'''))
    edit("nes_runtime_board165.inc",
         ("if(native_boot172(io))native_frames222(io,content_epoch);",
          "if(native_boot172(io) && !nes_boot_probe798)native_frames222(io,content_epoch);"),
         ("if(!nes_display_enter146()){native_io165=NULL;return false;}",
          "if(!nes_display_enter146()){nes_run136.first_error=9;native_io165=NULL;return false;}"))
    # The independently tested RESET fix is identical in both prior editions.
    name = "nes_cf86_session094.c"
    (out/name).write_bytes((ROOT.parent/"probes/nes-reset796/final796/src"/name).read_bytes())


if __name__ == "__main__":
    for number in (798,799):
        build_patch(number)
