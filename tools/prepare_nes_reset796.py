"""Build the two NES reset-handoff patches on the PR160-compatible ARM links."""
from pathlib import Path
from prepare_nes_shared794 import ROOT, replace_once

PROBES = ROOT.parent / "probes"
OUT = PROBES / "nes-reset796"


def prepare(number):
    previous = str(number - 2)
    src = PROBES / f"nes-shared794/link{previous}/src"
    patch = OUT / f"final-patch{number}"
    patch.mkdir(parents=True, exist_ok=False)

    def edit(file, changes):
        value = (src / file).read_text()
        for old, new in changes:
            value = replace_once(value, old, new)
        (patch / file).write_text(value, newline="\n")

    for name in ("nes_menu_diagnostic.c", "nes_checkpoint112.c", "VERSION"):
        raw = (src / name).read_bytes()
        assert previous.encode() in raw
        (patch / name).write_bytes(raw.replace(previous.encode(), str(number).encode()))

    edit("nes_cf86_session094.c", [(
        " if(!nes_return_delay(1,true)||!nes_cf86_check094())return nes_cf86_fail094();\n"
        " phase094=DISPLAY146;return nes_cf86_check094();",
        """ /* RESET is released by changing the pin to input. Keep all other
  * ownership and clock checks live until the physical input goes high. */
 for(unsigned ms=0;ms<20;ms++){
  if(!nes_return_delay(1,true)||!nes_cf86_check094())return nes_cf86_fail094();
  if(!get_snes_reset()){
   phase094=DISPLAY146;
   return nes_cf86_check094();
  }
 }
 /* No display ownership was established. Reclaim RESET, then let run136
  * issue and verify the ordinary STOP before base/menu restoration. */
 snes_reset(1);phase094=ARMED094;
 (void)nes_cf86_check094();
 return false;""")])
    edit("nes_diag_runtime.h", [("void nes_diag_led_tick(void);",
          "extern volatile uint8_t nes_boot_stage796;\nvoid nes_diag_led_tick(void);")])
    edit("nes_diag_platform.c", [
        ("static volatile unsigned led_phase,led_owned;",
         "volatile uint8_t nes_boot_stage796;\nstatic volatile unsigned led_phase,led_owned;"),
        (" if(!led_owned)return;", """ if(!led_owned)return;
 unsigned stage=nes_boot_stage796;
 if(stage){
  rdyled((stage&4)!=0);readled((stage&2)!=0);writeled((stage&1)!=0);
  return;
 }""")])
    edit("nes_run136.inc", [
        ("static bool run136(", "static __attribute__((noinline,noclone)) bool run136("),
        (' if(!nes_checkpoint112("DISPLAY_NEXT"', ' nes_boot_stage796=1;\n if(!nes_checkpoint112("DISPLAY_NEXT"'),
        (" uint8_t expected_rom=", " nes_boot_stage796=7;\n uint8_t expected_rom="),
        (' return nes_checkpoint112("DISPLAY_STOPPED"', ' nes_boot_stage796=0;\n return nes_checkpoint112("DISPLAY_STOPPED"')])
    edit("nes_runtime_board165.inc", [
        (" if(!native_preflight222(io)){", " nes_boot_stage796=2;\n if(!native_preflight222(io)){"),
        (" if(!nes_display_enter146()){native_io165=NULL;return false;}",
         """ nes_boot_stage796=3;
 if(!nes_display_enter146()){
  nes_run136.first_error=9;native_io165=NULL;return false;
 }
 nes_boot_stage796=4;"""),
        (" if(native_boot172(io))native_frames222(io,content_epoch);", """ nes_boot_stage796=5;
 if(native_boot172(io)){
  nes_boot_stage796=6;native_frames222(io,content_epoch);
 }""")])


if __name__ == "__main__":
    for edition in (796, 797):
        prepare(edition)
