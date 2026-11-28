"""Resolve only synthesis-reported merges; retain the exact endpoint check."""
import re
import sys
from pathlib import Path

def bind(board):
    report=(board/"output_files/board.map.rpt").read_text(errors="replace")
    edges=dict(re.findall(r"^; ([^;\n]+?)\s*; Merged with ([^;\n]+?)\s*;",report,re.M))
    assert edges
    for old in tuple(edges):
        target=old
        visited=set()
        while target in edges:
            if target in visited: raise ValueError(target)
            visited.add(target)
            target=edges[target]
        edges[old]=target
    path=board/"cdc181.sdc"
    source=path.read_text()
    # Supersede historical reset aliases when the device selected another
    # representative. Re-check after any historical alias substitution too.
    table="array set ::fitted1037 {\n"+"".join("{"+src+"} {"+dst+"}\n" for src,dst in edges.items())+"}\n"
    raw="set r [get_registers -nowarn $name]"
    lookup="if {[info exists ::fitted1037($name)]} {set name $::fitted1037($name)}\n "
    source=source.replace(raw,lookup+raw).replace("set r [get_registers $name]",lookup+"set r [get_registers $name]")
    path.write_text(table+source)
    # The CHR port moved to SRAM. PRG-only PSRAM reads have a constant top
    # address bit. Drop only its two old constraints if MAP proves it constant.
    reader="nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader"
    # A 256 KiB PRG-only board also fixes bit 18 to zero.
    for bit in (21,18):
        node=f"{reader}|address_hold[{bit}]"
        if re.search(r"^; "+re.escape(node)+r"\s*; Stuck at GND ",report,re.M):
            path=board/"cdc576.sdc"
            lines=path.read_text().splitlines(keepends=True)
            old=[line for line in lines if "{"+node+"}" in line]
            if not old: continue
            assert len(old)==2 and all(f"check_response_address[{bit}]" in line for line in old)
            path.write_text("".join(line for line in lines if line not in old))
    path=board/"cdc576.sdc"
    source=path.read_text()
    start="proc cdc576_pin {regname} {"
    assert source.count(start)==1
    path.write_text(source.replace(start,start+"\n if {[info exists ::fitted1037($regname)]} {set regname $::fitted1037($regname)}"))

if __name__=="__main__":bind(Path(sys.argv[1]))
