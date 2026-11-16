"""Run the final ARM formatter with the context recovered from the stopped RTL observer."""
import argparse
import json
import struct
from pathlib import Path

from analyze_nes_hardware702 import fault
from analyze_nes_supply485_hardware import fields
from check_nes_game478 import (ELFFile, Machine, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC)


def check(src, n, recovered):
    cpu = Machine(src, bytes(128))
    cpu.u.mem_map(0xe000e000, 0x2000)
    with (src/"obj-nes-100/sd2snes.elf").open("rb") as f:
        symbols = ELFFile(f).get_section_by_name(".symtab")
        base = symbols.get_symbol_by_name("nes_run136")[0]["st_value"]
        if n in (807,808,811,812,813,814):
            trace = symbols.get_symbol_by_name("nes_trace166")[0]
            assert trace["st_size"]==44
            cpu.u.mem_write(trace["st_value"]+40,bytes([64,33]))
    for offset, word in ((12,recovered["context"]), (24,recovered["ppu"])):
        cpu.u.mem_write(base+offset,struct.pack("<II",int(word[:8],16),int(word[8:],16)))
    cpu.u.mem_write(base+20,bytes(recovered["status"]))
    cpu.u.mem_write(base+32,bytes([recovered["ppu_valid"]]))
    # Capture the real writes at the FatFS boundary.
    files, active = {}, None
    def endpoint(u, pc, size, op):
        nonlocal active
        if op=="f_open":
            assert active is None
            active=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),80)).split(b"\0")[0].decode()
            files[active]=bytearray()
        elif op=="f_write":
            count=u.reg_read(UC_ARM_REG_R2)
            files[active].extend(u.mem_read(u.reg_read(UC_ARM_REG_R1),count))
            u.mem_write(u.reg_read(UC_ARM_REG_R3),struct.pack("<I",count))
        elif op=="f_close":
            assert active is not None
            active=None
        u.reg_write(UC_ARM_REG_R0,0)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for op in ("f_open","f_write","f_close","printf"):
        addr=cpu.syms[op]
        cpu.u.hook_add(UC_HOOK_CODE,endpoint,op,begin=addr,end=addr)
    state=0x20012000
    cpu.u.mem_write(state,b"PREPARED_RESET_HELD\0")
    cpu.call("save_report",[state,1])
    name=f"/sd2snes/nes-game-last-mmc{n}.txt"
    assert active is None and set(files)=={name,f"/sd2snes/nes-budget-mmc{n}.txt"}
    g=fields(files[name].decode())
    if n in (807,808,811,812,813,814):
        assert (g["obj_line"],g["obj_load"])==("64","33")
    assert g["candidate"]==f"NES-MMC{n}" and g["menu_state"]=="PREPARED_RESET_HELD"
    assert g["fault_context_valid"]==g["ppu_state_valid"]=="1"
    assert g["ppu_state_hi"]+g["ppu_state_lo"]==recovered["ppu"]
    decoded=fault(g)
    assert decoded["raw"]==recovered["context"] and decoded["context_ppu"]
    return dict(file=name, bytes=len(files[name]), ppu=recovered["ppu"],context=decoded)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path)
    p.add_argument("edition",type=int)
    p.add_argument("checks",type=Path)
    a=p.parse_args()
    recovered=json.loads((a.checks/"stopped.json").read_bytes())["late"]
    (a.checks/"report.json").write_text(json.dumps(check(a.src,a.edition,recovered),indent=2)+"\n")
