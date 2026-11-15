"""Materialize the ARM pre-COMMIT OBJ admission change on an MMC805/806 link."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_trial802 import rename_edition


def prepare(src, out, parent=None):
    if parent:
        rename_edition(src, out, parent, parent+2)
    else:
        out.mkdir(parents=True, exist_ok=True)
    header = "nes_native165.h"
    s = once((src / header).read_text(), "NES_NATIVE165_FAILED};", "NES_NATIVE165_FAILED,NES_NATIVE807_WAIT_ABORT};")
    (out / header).write_text(s, newline="\n")
    name = "nes_native165.c"
    s = (src / name).read_text()
    s = once(s, "static bool logical_record(", """/* Validate capacity before D3, while no destination-bank write is possible.
 * Admitted frames still pass build211's independent rank and OAM checks. */
static bool obj_overflow807(const struct nes_native165 *s){
 unsigned palettes=s->counts[5]/32;
 if(s->counts[2]*palettes<=32)return false;
 uint8_t depth[224]={0};
 for(unsigned i=0;i<s->counts[2];i++){
  uint64_t object=s->objects[i];
  int top=(int)((object>>13)&511);
  if(top&256)top-=512;
  unsigned mask=(unsigned)(object>>38)&255,epochs=0;
  for(unsigned row=0;row<8;row++)if(mask&(1u<<row)){
   unsigned y=top+((object&(UINT64_C(1)<<37))?7-row:row);
   if(y>=224)return false; /* Original planner diagnoses malformed geometry. */
   uint64_t raster=s->raster[y];
   if(!(raster&(UINT64_C(1)<<49)))epochs|=1u<<((raster>>44)&1);
  }
  unsigned entries=(epochs&1)+(epochs>>1);
  for(int y=top;y<top+8;y++)if((unsigned)y<224&&!(s->raster[y]&(UINT64_C(1)<<49))){
   depth[y]+=entries;
   if(depth[y]>32){
    nes_trace166.obj_line=(uint8_t)y;nes_trace166.obj_load=depth[y];return true;
   }
  }
 }
 return false;
}
static bool logical_record(""")
    # Only the matching, CRC-checked standalone ABORT(6) can release a rejected
    # input. A stale COMMIT, unsolicited BEGIN or a different reason fails closed.
    s = once(s, "if(s->state==NES_NATIVE165_FAILED)return false;", """if(s->state==NES_NATIVE165_FAILED)return false;
 if(s->state==NES_NATIVE807_WAIT_ABORT &&
    (n!=12 || p[0]!=0xe0 || p[1]!=2))return fail(s,5);""")
    s = once(s, "if(kind==7&&index==2){", "if(kind==7&&index==2){if(s->state==NES_NATIVE807_WAIT_ABORT&&v!=6)return fail(s,5);")
    s = once(s, "frame(tx,0xd3,s->generation,(uint8_t)accept);",
             "bool skip=accept&&obj_overflow807(s);\n frame(tx,0xd3,s->generation,(uint8_t)(accept&&!skip));")
    s = once(s, "s->state=accept?NES_NATIVE165_PREPARED:NES_NATIVE165_FAILED;",
             "s->state=skip?NES_NATIVE807_WAIT_ABORT:(accept?NES_NATIVE165_PREPARED:NES_NATIVE165_FAILED);")
    (out / name).write_text(s, newline="\n")
    name = "nes_trace166.h"
    s = once((src/name).read_text(), "first_abort_reason,last_abort_reason;", "first_abort_reason,last_abort_reason,obj_line,obj_load;")
    (out/name).write_text(s, newline="\n")
    name = "nes_menu_diagnostic.c"
    s = ((out if parent else src)/name).read_text()
    s = once(s, r'\201begins\202', r'obj_line\200obj_load\200\201begins\202')
    s = once(s, ",(unsigned long)nes_trace166.begins,", ",nes_trace166.obj_line,nes_trace166.obj_load,(unsigned long)nes_trace166.begins,")
    # Keep UART measurements and SD reports. Share the write-result format
    # between both files and shorten legacy prose to make room in ARM flash.
    for old,new in (
        ("NES165 %uKiB; SPI1 mode0 PCLK2/32; duration not yet measured on hardware.", "NES %uKiB SPI1/32"),
        ("NES094 recovery failed; RESET/USB protection held; no menu reload.", "NES recovery failed; RESET/USB held"),
        ("NES094 final phase=%u error=%u progress=%lu/%lu", "NES p%u e%u %lu/%lu"),
        ('"NES227 budget open=%u write=%u close=%u bytes=%u/%u\\n",bo', '"NES %s o%u w%u c%u %u/%u\\n","budget",bo'),
        ('"NES094 log open=%u write=%u close=%u bytes=%u/%u\\n",', '"NES %s o%u w%u c%u %u/%u\\n","last",'),
    ):
        s = once(s, old, new)
    (out/name).write_text(s, newline="\n")
    # The source and plan protocols both use CRC-8/ATM (init 0).
    name = "nes_native165.c"
    s = (out/name).read_text().replace("crc8(", "nes_wire_crc807(")
    (out/name).write_text(once(s,"static uint8_t nes_wire_crc807(", "uint8_t nes_wire_crc807("), newline="\n")
    name = "nes_plan_service200.c"
    s = (src/name).read_text()
    crc = next(line for line in s.splitlines() if line.startswith("static uint8_t crc8("))
    s = once(s, crc, "extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);")
    (out/name).write_text(s.replace("crc8(", "nes_wire_crc807("), newline="\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--parent",type=int,choices=(805,806))
    args = p.parse_args()
    prepare(args.src, args.out,args.parent)
