# SPDX-License-Identifier: MIT
"""Run isolated Cortex-M4 mask kernels on the observed planner write sequence."""
import argparse
import collections
import json
import subprocess
from pathlib import Path
from analyze_nes_map513 import WIDTHS, expand, trim
from check_nes_game478 import ELFFile, Machine, sha

ROOT = Path(__file__).resolve().parents[1]
GCC = (ROOT.parent / ".tools/arm-gnu-toolchain-13.3.rel1/"
       "arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin/arm-none-eabi-gcc.exe")


def measure(arm, out, unit, frames):
    obj = out / f"mask{unit}.o"
    src = ROOT / "tools/nes_map513_mask.c"
    subprocess.run([str(GCC), "-mcpu=cortex-m4", "-mthumb", "-Os", "-ffreestanding",
                    "-fno-unwind-tables", f"-DUNIT={unit}", "-c", str(src), "-o", str(obj)], check=True)
    m = Machine(arm, bytes(128))
    code = 0x08060000
    with obj.open("rb") as file:
        elf = ELFFile(file)
        assert elf.get_section_by_name(".rel.text") is None
        text = elf.get_section_by_name(".text").data()
        m.u.mem_write(code,text)
        for sym in elf.get_section_by_name(".symtab").iter_symbols():
            if sym.name.startswith("map513_"):
                m.syms[sym.name] = code + (sym["st_value"] & ~1)
    a, b, current = 0x20013000, 0x20013100, 0x20013200
    count = collections.Counter()

    def call(name,*args):
        start = m.instructions
        value = m.call("map513_"+name,args)
        count[name] += m.instructions - start
        return value

    for ptr in (a,b):
        call("fill",ptr,0xffffffff)
    initial = sum(count.values())
    wm = [(1<<2048)-1]*2
    rows = []
    for frame in frames:
        count.clear()
        changed = int(frame["touched_words_hex"],16)
        call("fill",current,0 if frame["inherits"] else 0xffffffff)
        for index in frame["changed_calls"]:
            call("mark",current,index)
        call("prepare",a,b,current)
        wm = [old|changed for old in wm]
        bank = frame["bank"]
        target = (a,b)[bank]
        for packet in frame["map_packets"]:
            start, body = expand(bytes.fromhex(packet))
            expected, payload = trim(body,start,wm[bank],unit)
            result = call("span",target,start,len(body))
            assert (result & 0xffff, result >> 16) == (expected,len(payload)), (unit,frame["generation"],start,result)
        call("fill",target,0)  # after the modeled final ACK only
        wm[bank] = 0
        rows.append(dict(generation=frame["generation"],instructions=dict(count)))
    return dict(unit=unit,text_B=len(text),data_B=0,extra_masks_B=3*4096//unit//8,
                initialization_instructions=initial,per_frame=rows,object_SHA256=sha(obj))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("arm","capture","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    frames=json.loads((a.capture/"captures.json").read_text())
    a.out.mkdir(parents=True,exist_ok=False)
    reports=[measure(a.arm,a.out,n,frames) for n in WIDTHS]
    (a.out/"result.json").write_text(json.dumps(dict(capture_SHA256=sha(a.capture/"captures.json"),
        firmware_SHA256=sha(a.arm/"obj-nes-100/firmware.stm"),source_SHA256=sha(ROOT/"tools/nes_map513_mask.c"),
        kernels=reports),indent=2)+"\n")
    for r in reports:
        print(r["unit"],r["text_B"],sum(sum(f["instructions"].values()) for f in r["per_frame"][2:]))
