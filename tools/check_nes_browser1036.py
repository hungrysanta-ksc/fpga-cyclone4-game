"""Exercise directory selection, header admission and the first full read in linked ARM code."""
import hashlib
import argparse
import json
from pathlib import Path
from check_nes_opening818 import admission
from check_ff3_state_reference import DIGEST
from prepare_nes_ff3_checkpoint import ROOT, OUT


def check(src, output):
    flash = (src / "obj-nes-100/firmware.stm").read_bytes()
    assert len(flash) <= 212992
    roms = Path.home() / "Downloads/test"
    kirby = next(roms.glob("Hoshi no Kirby*.nes")).read_bytes()
    ff3 = next(data for f in roms.glob("Final Fantasy III*.nes")
               if hashlib.sha256(data:=f.read_bytes()).hexdigest()==DIGEST)
    altered = ff3[:-1] + bytes([ff3[-1] ^ 1])
    cases = [
        ("/action/flying.NES", kirby, "chrrom"),
        ("/rpg/FF III [J-K].nes", ff3, "chrram"),
        ("/dir.nes/another.NeS", altered, "chrram"),
        ("/dir.nes/old.sfc", ff3, None),
        ("/rpg/bad.nes.bak", ff3, None),
        ("/rpg/cut.nes", ff3[:-1], False),
        ("/rpg/other mapper.nes", ff3[:6] + b"\x52" + ff3[7:], False),
    ]
    results = []
    for path, raw, kind in cases:
        result = admission(src, raw, selected=path)
        assert result["extension"] == (kind is not None)
        assert result["program"] == result["selected"] == bool(kind), (path, result)
        if kind:
            assert result["image"] == f"/sd2snes/nes-{kind}.bi3"
            assert result["read_B"] == len(raw)+16
        results.append({"path": path, **result})
    changed=admission(src,kirby,selected="/rpg/swapped.nes",select_raw=ff3)
    assert changed["selected"] and not changed["program"] and changed["read_B"]==32
    results.append({"path":"/rpg/swapped.nes","media_change_after_selection":True,**changed})
    report = {"flash_B": len(flash), "firmware_stm_sha256": hashlib.sha256(flash).hexdigest(),
              "boundary": "menu, FatFS selection, complete selected file CRC, enter FPGA programmer",
              "cases": results}
    output.write_text(json.dumps(report, indent=2)+"\n")
    print(f"PASS linked menu/loader: {len(results)} cases; Flash {len(flash)} B")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src",type=Path,default=OUT/"browser-link/src")
    p.add_argument("--report",type=Path,default=ROOT/"analysis/nes-browser1036.json")
    args=p.parse_args()
    check(args.src,args.report)

