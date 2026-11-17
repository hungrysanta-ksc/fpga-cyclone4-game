"""Link one diagnostic sink routine against MMC826's absolute function/data addresses."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from check_nes_game478 import ELFFile, sha
from prepare_nes_section832 import BASE, OUT, PROBES


def thumb_bl(pc, target):
    delta=target-pc-4
    assert delta%2==0 and -(1<<24)<=delta<(1<<24)
    sign=(delta>>24)&1
    j1=1^sign^((delta>>23)&1)
    j2=1^sign^((delta>>22)&1)
    return struct.pack("<HH",0xf000|(sign<<10)|((delta>>12)&1023),
                       0xd000|(j1<<13)|(j2<<11)|((delta>>1)&2047))


def build(mode, candidate=None, out_root=OUT):
    base=BASE/"src/obj-nes-100"
    candidate=candidate or (BASE if mode=="base" else PROBES/"nes-output823"/("link-832"+mode))
    obj=candidate/"src/obj-nes-100/nes_native_sink165.o"
    out=out_root/("overlay-"+mode)
    out.mkdir(exist_ok=True)
    with (base/"sd2snes.elf").open("rb") as f:
        syms={s.name:s["st_value"] for s in ELFFile(f).get_section_by_name(".symtab").iter_symbols() if s.name}
    with obj.open("rb") as f:
        needed=[s.name for s in ELFFile(f).get_section_by_name(".symtab").iter_symbols()
                if s.name and s["st_shndx"]=="SHN_UNDEF"]
    extern=[f"{name} = 0x{syms[name]:x};" for name in needed]
    (out/"layout.ld").write_text("\n".join(extern)+"""
ENTRY(nes_sink212_seal)
SECTIONS { . = 0x08060000; .sink : { *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) } }
""")
    ld=next((PROBES.parent/".tools/arm-gnu-toolchain-13.3.rel1").glob("*/bin/arm-none-eabi-ld.exe"))
    subprocess.run([ld,"--gc-sections","-T","layout.ld",obj.resolve(),"-o","sink.elf"],cwd=out,check=True)
    with (out/"sink.elf").open("rb") as f:
        elf=ELFFile(f)
        section=elf.get_section_by_name(".sink")
        assert section["sh_addr"]==0x08060000 and section.data_size<0x10000
        (out/"sink.bin").write_bytes(section.data())
        entry=elf.get_section_by_name(".symtab").get_symbol_by_name("nes_sink212_seal")[0]["st_value"]&~1
    sites=[]
    with (base/"nes_native_runtime165.o").open("rb") as f:
        elf=ELFFile(f)
        for sec in elf.iter_sections():
            if not sec.name.startswith(".rel.text."):
                continue
            for rel in sec.iter_relocations():
                sym=elf.get_section(sec["sh_link"]).get_symbol(rel["r_info_sym"])
                if sym.name=="nes_sink212_seal":
                    assert rel["r_info_type"]==10
                    sites.append((syms[sec.name.removeprefix(".rel.text.")]&~1)+rel["r_offset"])
    assert sites
    flash=(base/"firmware.stm").read_bytes()
    patches=[]
    for pc in sites:
        original=thumb_bl(pc,syms["nes_sink212_seal"]&~1)
        assert flash[pc-0x0800c000:pc-0x0800c000+4]==original
        patches.append([pc,original.hex(),thumb_bl(pc,entry).hex()])
    (out/"entry.json").write_text(json.dumps(dict(entry=entry,patches=patches,
        parent=sha(base/"firmware.stm"),sink=sha(out/"sink.bin"),object=sha(obj))))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode")
    build(parser.parse_args().mode)
