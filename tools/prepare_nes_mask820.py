"""Build the MMC819 successor with row-specific OBJ plane masks."""
from pathlib import Path
import re
import argparse
import shutil

from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial816 import fit

WORK = PROBES / "nes-mask820"


def edit(path, old, new):
    data = path.read_bytes()
    assert data.count(old.encode()) == 1, (path.name, old)
    path.write_bytes(data.replace(old.encode(), new.encode()))


def board(temp):
    base = temp / "nes-opening818-board"
    dst = temp / "nes-trial816-board820b"
    dst.mkdir()
    for name in ("rtl", "sys"):
        shutil.copytree(base / name, dst / name)
    for f in base.iterdir():
        if f.suffix in (".sv", ".v", ".vhd", ".qpf", ".qsf", ".sdc", ".hex", ".tcl"):
            shutil.copyfile(f, dst / f.name)
    raster = dst / "nes_native_raster181.sv"
    edit(raster, "display_mask!=8'h18 && display_mask!=8'h1e",
         "display_mask!=8'h18 && display_mask!=8'h1e && display_mask!=8'h0e")
    # Keep the original eight mask bits in each normal row descriptor. A
    # change inside the row still takes the raw compositor unconditionally.
    edit(raster, "display_mask!=normal_mask", "display_mask[1]!=normal_mask[1]")
    # Normal descriptors have three possible masks. Encode the constants at
    # the RAM write port; raw rows retain their fixed zero descriptor.
    edit(raster, "bank,line_mask,line_mode", "bank,3'b0,line_mask[4],1'b1,{2{line_mask[1]}},1'b0,line_mode")


def arm():
    base = PROBES / "nes-opening818/link819/src"
    dst = WORK / "patch820b"
    rename_edition(base, dst, 819, 820)
    planner = dst / "nes_planner211.c"
    recv = dst / "nes_native165.c"
    for f in (planner, recv):
        shutil.copyfile(base / f.name, f)
    edit(planner, "static unsigned epoch(", """/* OBJ is disabled on stable $0e rows. Use the already transported tile
 * plane mask so the SNES independently validates its ordinary/raw tables. */
static unsigned layer_class820(uint64_t raster){
 uint8_t mask=(uint8_t)(raster>>36);
 return mask==0x0e?0x1e:mask;
}
static unsigned epoch(""")
    edit(planner, "(uint8_t)(s->raster[first_normal]>>36)", "layer_class820(s->raster[first_normal])")
    edit(planner, "((s->raster[y]>>36)&255)!=p->display_mask", "layer_class820(s->raster[y])!=p->display_mask")
    edit(planner, "rank_used[y]|=(uint8_t)(1u<<rank);masks", """rank_used[y]|=(uint8_t)(1u<<rank);
   if(!(s->raster[y]&(UINT64_C(1)<<40)))continue;
   masks""")
    edit(recv, "if(!(raster&(UINT64_C(1)<<49)))epochs",
         "if(raster&(UINT64_C(1)<<40))epochs")
    # Raw descriptors have no layer bits. Check malformed raw separately in
    # the parser as before. OAM depth still counts all allocated SNES objects.
    # Optimize the same validated planner for flash size on the timed ARM.
    edit(planner, '#include "nes_cost471.h"', '#pragma GCC optimize ("Oz")\n#include "nes_cost471.h"')
    # The report dictionary is immutable. Each word has at least one byte;
    # removing that byte from each preceding offset fits all offsets in u8.
    budget = dst / "nes_budget210.c"
    shutil.copyfile(base / budget.name, budget)
    old = re.search(r"static const uint16_t offsets\[\] = \{ ([0-9,]+) \};", budget.read_text())
    offsets = [int(n) for n in old[1].split(",")]
    delta = [v-i for i,v in enumerate(offsets)]
    assert all(0<=v<=255 for v in delta)
    edit(budget, old[0], "static const uint8_t offsets[] = { "+",".join(map(str,delta))+" };")
    edit(budget, "words + offsets[symbol-128]", "words + (symbol-128) + offsets[symbol-128]")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("board", "arm", "fit"))
    p.add_argument("--temp", type=Path)
    a = p.parse_args()
    if a.action == "arm":
        arm()
    elif a.action == "board":
        board(a.temp)
    else:
        fit(a.temp, "820b", Path("C:/altera_lite/25.1std/quartus/bin64"))
