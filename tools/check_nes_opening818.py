"""Run the final loader's real ARM header, size and CRC path up to FPGA programming."""
import argparse
import json
from pathlib import Path
import struct

from check_nes_game478 import ELFFile, sha
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_MCLASS, UC_MODE_THUMB
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_XPSR)
from prepare_nes_opening818 import ADVENTURE_SHA, ROM_SHA, SRC, WORK


def admission(src,raw,edition=818,selected=None,select_raw=None):
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
    for addr,size in ((0x08000000,0x80000),(0x20000000,0x20000),(0xe000e000,0x2000),(0x40000000,0x100000)):
        u.mem_map(addr,size)
    obj=src/"obj-nes-100"
    flash=(obj/"firmware.stm").read_bytes()
    with (obj/"sd2snes.elf").open("rb") as f:
        elf=ELFFile(f)
        for seg in elf.iter_segments():
            if seg["p_type"]=="PT_LOAD" and seg["p_filesz"]:
                offset=seg["p_paddr"]-0x0800c000
                assert flash[offset:offset+seg["p_filesz"]]==seg.data()
                u.mem_write(seg["p_vaddr"],seg.data())
        symbols={s.name:s["st_value"]&~1 for s in elf.get_section_by_name(".symtab").iter_symbols()}
    path,image,report,done=0x20001000,0x20001100,0x20001200,0x0807fff0
    pathname = selected or f"/sd2snes/nes/mmc{edition}.nes"
    u.mem_write(path,pathname.encode()+b"\0")
    u.mem_write(image,f"/sd2snes/fpga_mmc{edition}.bi3\0".encode())
    st=dict(pos=0,read_B=0,program=False)
    active_file=raw
    yes=("nes_diag_sd_handoff113","nes_checkpoint_begin112","nes_checkpoint112","nes_cf86_enter094",
         "nes_css_begin108","nes_cf86_check094","nes_cf86_finish094")
    no=("nes_menu_base_only116","nes_menu_entry_only113","nes_cf86_failed094","nes_cf86_monitoring094",
        "nes_diag_sd_failed","nes_return_failed","nes_menu_diagnostic_pending","nes_diag_leave","nes_diag_progress","snes_reset")
    def hook(uc,addr,size,name):
        nonlocal active_file,select_raw
        a,b,c,d=[uc.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        result=int(name in yes)
        if name=="nes_diag_fpga_pgm":
            st["program"]=True
            if selected:
                st["image"]=bytes(uc.mem_read(a,64)).split(b"\0")[0].decode()
            uc.emu_stop()
            return
        if name=="f_open":
            assert bytes(uc.mem_read(b,len(pathname.encode())+1))==pathname.encode()+b"\0"
            st["pos"]=0
            active_file=select_raw if select_raw is not None else raw
            select_raw=None
            uc.mem_write(a,bytes(12)+struct.pack("<I",len(active_file)))
        elif name=="f_read":
            chunk=active_file[st["pos"]:st["pos"]+c]
            uc.mem_write(b,chunk);uc.mem_write(d,struct.pack("<I",len(chunk)))
            st["pos"]+=len(chunk);st["read_B"]+=len(chunk)
            uc.mem_write(a+8,struct.pack("<I",st["pos"]))
        elif name=="f_lseek":
            st["pos"]=b;uc.mem_write(a+8,struct.pack("<I",b))
        uc.reg_write(UC_ARM_REG_R0,result)
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for name in (*yes,*no,"f_open","f_read","f_lseek","f_close","nes_diag_fpga_pgm","snes_menu_errmsg"):
        if name not in symbols: continue
        addr=symbols[name]
        u.hook_add(UC_HOOK_CODE,hook,name,begin=addr,end=addr)
    for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_XPSR),
                       (path,image,0,report,0x2001e000,done|1,0x01000000)):
        u.reg_write(reg,val)
    if selected:
        u.mem_map(0x42000000,0x02000000)  # Cortex-M peripheral bit-band aliases
        u.mem_map(0x10000000,0x10000)  # STM32F4 CCM
        if "printf" in symbols:
            u.hook_add(UC_HOOK_CODE,hook,"printf",begin=symbols["printf"],end=symbols["printf"])
        from unicorn import UC_HOOK_MEM_UNMAPPED
        def unmapped(uc, access, addr, size, value, _):
            print(f"unmapped {addr:08x} pc={uc.reg_read(UC_ARM_REG_PC):08x}",flush=True)
            return False
        u.hook_add(UC_HOOK_MEM_UNMAPPED,unmapped)
        def menu_call(symbol):
            u.reg_write(UC_ARM_REG_R0,path)
            u.reg_write(UC_ARM_REG_LR,done|1)
            u.emu_start(symbols[symbol]|1,done,count=200000000)
            return u.reg_read(UC_ARM_REG_R0)
        st["extension"]=bool(menu_call("nes_menu_diagnostic_marker"))
        st["selected"]=st["extension"] and bool(menu_call("nes_menu_select_rom"))
        if st["selected"]:
            # Directory scanner's shared filename must no longer own the selection.
            u.mem_write(path,b"/changed.sfc\0")
            menu_call("nes_menu_diagnostic_run")
        return st
    u.emu_start(symbols["nes_menu_sd_probe"]|1,done,count=200000000)
    assert st["program"] or u.reg_read(UC_ARM_REG_PC)==done
    return dict(program=st["program"],read_B=st["read_B"],error=u.mem_read(report,1)[0])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("captain","adventure","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    assert sha(a.captain)==ROM_SHA and sha(a.adventure)==ADVENTURE_SHA
    cap,adv=a.captain.read_bytes(),a.adventure.read_bytes()
    new=WORK/"link818/src"
    rows={}
    for name,src,raw,error in (("816_captain",SRC,cap,2),("816_adventure",SRC,adv,2),
            ("818_captain",new,cap,0),("818_adventure",new,adv,4),
            ("818_last_byte_corrupt",new,cap[:-1]+bytes([cap[-1]^1]),4),
            ("819_adventure",WORK/"link819/src",adv,0),("819_captain",WORK/"link819/src",cap,4),
            ("819_last_byte_corrupt",WORK/"link819/src",adv[:-1]+bytes([adv[-1]^1]),4)):
        r=admission(src,raw)
        assert r["error"]==error and r["program"]==(error==0) and r["read_B"]==(16 if error==2 else len(raw)),(name,r)
        rows[name]=r
    a.out.write_text(json.dumps(rows,indent=2)+"\n")
    print(rows)
