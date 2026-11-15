"""Replay the linked eGBC renderer load at its load_rom call site with file and SRAM I/O modeled."""
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from zipfile import ZipFile

from check_nes_game478 import ELFFile, Machine, Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R10, UC_ARM_REG_SP)

ROOT = Path(__file__).resolve().parents[2]
PROBES = ROOT / "probes"


def check_cartridge_dispatch(src):
    """Run the linked GBC filename and mapper decoder with a synthetic MBC5 header."""
    cpu = Machine(src, bytes(128))
    props, filename = 0x20012000, 0x20012100
    reads = []
    def io(u, pc, size, name):
        if name == "file_readblock":
            assert u.reg_read(UC_ARM_REG_R1) == 0x100
            header = bytearray(u.reg_read(UC_ARM_REG_R2))
            header[0x47:0x4a] = bytes([0x1b,8,3])
            u.mem_write(u.reg_read(UC_ARM_REG_R0), bytes(header))
            reads.append(1)
        u.reg_write(UC_ARM_REG_R0,0)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ("printf","snprintf","file_readblock"):
        pc=cpu.syms[name]
        cpu.u.hook_add(UC_HOOK_CODE,io,name,begin=pc,end=pc)
    cases={}
    for ext in ("sfc","smc","EgBc","gbc"):
        reads.clear()
        cpu.u.mem_write(filename,("example."+ext+"\0").encode())
        cpu.u.mem_write(props,b"\xff"*128)
        cpu.call("sgb_id",[props,filename])
        mapper,egbc,ram,size=struct.unpack("<BBII",cpu.u.mem_read(props,10))
        cases[ext] = [mapper,egbc,ram,size,len(reads)]
    assert cases==dict(sfc=[0,0,0,0,0],smc=[0,0,0,0,0],
                       EgBc=[5,1,32768,8<<20,1],gbc=[5,0,32768,0,1])
    return cases


def check(src, renderer, damage):
    obj = src / "obj-nes-100"
    firmware = (obj / "firmware.stm").read_bytes()
    cpu = Uc(UC_ARCH_ARM, UC_MODE_MCLASS | UC_MODE_THUMB)
    cpu.mem_map(0x08000000, 0x40000)
    cpu.mem_map(0x20000000, 0x10000)
    elf = obj / "sd2snes.elf"
    with elf.open("rb") as stream:
        image = ELFFile(stream)
        symbols = {s.name:s["st_value"] for s in image.get_section_by_name(".symtab").iter_symbols()}
        for part in image.iter_segments():
            if part["p_type"] == "PT_LOAD" and part["p_filesz"]:
                offset = part["p_paddr"] - 0x0800c000
                assert firmware[offset:offset+part["p_filesz"]] == part.data()
                cpu.mem_write(part["p_vaddr"], part.data())
    dump = next((ROOT / ".tools/arm-gnu-toolchain-13.3.rel1").rglob("arm-none-eabi-objdump.exe"))
    listing = subprocess.check_output([dump, "-d", "--disassemble=load_rom", elf.name],
                                      cwd=elf.parent, text=True).splitlines()
    call = next(i for i,line in enumerate(listing) if "<gbc_copy_verified>" in line)
    assert "<puts>" in listing[call-5] and "0x890000" in listing[call-1] and "r2, sl" in listing[call-2]
    assert "cmp" in listing[call+1] and "beq" in listing[call+2]
    address = lambda line: int(line.split(":")[0].strip(), 16)
    entry = address(listing[call-4])
    fail = int(re.search(r"beq(?:\.w)?\s+([0-9a-f]+)", listing[call+2])[1],16)
    ok = address(listing[call+3])
    offset = 0
    readback = 0
    ram = bytearray(len(renderer))
    expected = []

    def hook(u, pc, size, name):
        nonlocal offset, readback
        r0,r1,r2 = (u.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
        if name == "gbc_copy_verified":
            assert r1 == 0x890000 and r2 == len(renderer)
            expected.append(u.reg_read(UC_ARM_REG_R3))
            return
        if name in ("success","failure"):
            u.emu_stop()
            return
        if name == "file_open":
            assert bytes(u.mem_read(r0,32)).split(b"\0")[0] == b"/sd2snes/gbc_snes.bin"
            u.mem_write(symbols["file_handle"]+12,struct.pack("<I",len(renderer)))
        elif name == "file_read":
            block = renderer[offset:offset+512]
            if block:
                u.mem_write(symbols["file_buf"],block)
            offset += len(block)
            u.reg_write(UC_ARM_REG_R0,len(block))
        elif name in ("sram_writeblock","sram_readblock"):
            at = r1-0x890000
            assert 0 <= at <= len(renderer)-512 and r2 == 512
            if name == "sram_writeblock":
                ram[at:at+r2] = u.mem_read(r0,r2)
            else:
                assert at == readback
                data = bytearray(ram[at:at+r2])
                if damage and at+r2 == len(renderer):
                    data[-1] ^= 1
                u.mem_write(r0,bytes(data))
                readback += r2
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    for name in ("gbc_copy_verified","file_open","file_read","file_close","sram_writeblock","sram_readblock"):
        pc = symbols[name] & ~1
        cpu.hook_add(UC_HOOK_CODE,hook,name,begin=pc,end=pc)
    for name,pc in (("success",ok),("failure",fail)):
        cpu.hook_add(UC_HOOK_CODE,hook,name,begin=pc,end=pc)
    cpu.mem_write(symbols["SGBSR"],b"/sd2snes/gbc_snes.bin\0")
    cpu.reg_write(UC_ARM_REG_SP,0x2000fe00)
    cpu.reg_write(UC_ARM_REG_R10,len(renderer))
    cpu.emu_start(entry|1,0,count=16000000)
    pc = cpu.reg_read(UC_ARM_REG_PC)
    assert len(expected)==1 and offset==readback==len(renderer) and pc in (ok,fail)
    return dict(firmware=hashlib.sha256(firmware).hexdigest(),flash_bytes=len(firmware),
                required_crc=f"{expected[0]:08x}",readback_bytes=readback,accepted=pc==ok)


if __name__ == "__main__":
    with ZipFile(PROBES/"gbc-rgb774/GBC774-RGB555-SD-ROOT.zip") as z:
        renderer = z.read("sd2snes/gbc_snes.bin")
    assert hashlib.sha256(renderer).hexdigest()=="730564d2b2efe60d73ff3aa2bd55b0639fd951480227023303909c8bf448af1c"
    results = {}
    for n in (792,793,794,795):
        folder = "nes-trial792" if n<794 else "nes-shared794"
        src = PROBES/folder/f"link{n}/src"
        results[n] = {"original":check(src,renderer,False)}
        assert results[n]["original"]["accepted"] == (n>=794)
        if n>=794:
            results[n]["damaged_readback"] = check(src,renderer,True)
            assert not results[n]["damaged_readback"]["accepted"]
    print(json.dumps(results,indent=2))
