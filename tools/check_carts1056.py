"""Run the actual release FatFS, CRC, PSRAM destinations and STOP/base handoff."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from prepare_nes_carts1056 import CARTS, OUT
from probe_nes_carts1056 import GAMES
from check_nes_retail_return1054 import run
from check_ff3_sd1043 import Machine, fat16, ELFFile, Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB

def headers(profile,ref):
    # LTO on the debug build can internalize filesystem functions. This check
    # calls the shared classifier in the actual STM image without any hooks.
    obj=OUT/profile/"link/src/obj-nes-100"
    firmware=(obj/"firmware.stm").read_bytes()
    m=object.__new__(Machine)
    m.u=Uc(UC_ARCH_ARM,UC_MODE_MCLASS|UC_MODE_THUMB)
    m.u.mem_map(0x08000000,0x80000)
    m.u.mem_map(0x20000000,0x10000)
    with (obj/"sd2snes.elf").open("rb") as f:
        elf=ELFFile(f)
        m.sym={s.name:s["st_value"] for s in elf.get_section_by_name(".symtab").iter_symbols()}
        for seg in elf.iter_segments():
            if seg["p_type"]=="PT_LOAD" and seg["p_filesz"]:
                off=seg["p_paddr"]-0x0800c000
                assert seg.data()==firmware[off:off+seg["p_filesz"]]
                m.u.mem_write(seg["p_vaddr"],seg.data())
    ptr=0x0807fd00
    checked=0
    for entry in ref.values():
        h=bytes.fromhex(entry["header"])
        size=16+entry["prg"]+entry["chr_rom"]
        for i,mask,delta,expected in [(0,0,0,CARTS[entry["mapper"]][0]),(0,1,0,0),
                                      (6,4,0,0),(0,0,-1,0),(9,1,0,0)]:
            data=bytearray(h)
            data[i]^=mask
            m.u.mem_write(ptr,bytes(data))
            assert m.call("nes_image_id",ptr,size+delta)==expected,(profile,h,i,delta)
            checked+=1
    return dict(checked=checked,sha256=hashlib.sha256(firmware).hexdigest())

def battery():
    src=OUT/"release/link/src"
    disk=fat16()
    expected=bytes((i*7+i//128)&255 for i in range(8192))
    for load in (False,True):
        m=Machine(src,disk)
        m.u.mem_write(m.sym["nes_board_id"],b"\x84")
        m.u.mem_write(m.sym["nes_cart_bytes"],struct.pack("<I",1<<20))
        m.rom(0x9ac62bb9)
        if not load:
            m.battery[:]=expected
        assert m.call("nes_menu_state_io",0,int(load),live=True)==1
        assert m.call("nes_menu_state_resume")==1
        assert m.battery==expected
        assert (m.writes==0)==load
    return len(expected)

def guards():
    ref=json.loads((OUT/"reference.json").read_text())
    report={p:headers(p,ref) for p in ("release","debug")}
    report["battery_roundtrip_bytes"]=battery()
    (OUT/"guards.json").write_text(json.dumps(report,indent=2))

def check(folder):
    result={}
    for mapper,game in zip((3,7,21,5),GAMES):
        raw=(folder/(game+".nes")).read_bytes()
        result[game]=run(CARTS[mapper][0],OUT,1,raw=raw,image=f"/sd2snes/nes-m{mapper}.bi3")
    result["kirby"]=run(0x7c,OUT,1)
    result["ff3"]=run(0x7d,OUT,1)
    (OUT/"handoff.json").write_text(json.dumps(result,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path)
    p.add_argument("--guards-only",action="store_true")
    args=p.parse_args()
    if not args.guards_only:
        check(args.folder)
    guards()
