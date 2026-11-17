"""Apply the checked map829 packet aperture to the physical MMC826 board sources."""
from pathlib import Path
import argparse
from nes_raw506 import once
import shutil
import hashlib


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/fpga/nes_map829"

def build(temp):
    base=temp/"nes-trial816-board822held"
    dest=temp/"nes-trial816-board829reserved"
    dest.mkdir()
    for name in ("rtl","sys"):
        shutil.copytree(base/name,dest/name)
    for f in base.iterdir():
        if f.is_file() and f.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".hex",".tcl"):
            shutil.copyfile(f,dest/f.name)
    for f in SOURCE.glob("*.sv"):
        orig=base/f.name
        assert hashlib.sha256(orig.read_bytes()).hexdigest()==(SOURCE/(f.stem+".sha256")).read_text().strip()
        shutil.copyfile(f,dest/f.name)
    return dest

def split_sender(out, policy="inherited"):
    from prepare_nes_map828 import OUT
    shutil.copytree(OUT/"patch-right",out)
    path=out/"nes_native_sink165.c"
    # Compare handing the tile planner a ROM grant after two map pairs versus
    # one pair, only at the existing completed-page offer.
    gate={"inherited":"!p->map_dirty && fragments>112/4","two":"fragments>112/4","one":"fragments>112/4"}[policy]
    end=38 if policy=="one" else 44
    text=once(path.read_text(),"if(!map527(s,p,map,3))return false;",
        f"uint64_t ready=({gate}) ? map & ((UINT64_C(1)<<{end})-1) : map;\n"
        "  if(!map527(s,p,ready,3))return false;")
    path.write_text(text)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("temp",type=Path)
    p.add_argument("--fit",action="store_true")
    p.add_argument("--sender",choices=("split","one","two"))
    a=p.parse_args()
    if a.sender:
        out=ROOT.parent/"probes/nes-map829"/("patch-"+a.sender)
        split_sender(out, "inherited" if a.sender=="split" else a.sender)
        raise SystemExit(0)
    build(a.temp)
    if a.fit:
        from prepare_nes_trial816 import fit
        fit(a.temp,'829reserved',Path("C:/altera_lite/25.1std/quartus/bin64"))
