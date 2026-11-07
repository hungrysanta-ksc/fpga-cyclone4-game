"""Bind only proven Quartus A&S duplicate-register aliases, without relaxing constraints."""
import argparse,re
from pathlib import Path
from nes_raw506 import once

def bind(board):
    rpt=(board/"output_files/board.map.rpt").read_text()
    edges=dict(re.findall(r"^; ([^;\n]+?)\s*; Merged with ([^;\n]+?)\s*;",rpt,re.M))
    mapping={}
    for name in edges:
        dst=name;seen=set()
        while dst in edges and dst not in seen:
            seen.add(dst);dst=edges[dst]
        if dst not in seen:mapping[name]=dst
    p=board/"cdc181.sdc";s=p.read_text()
    code="array set aliases659 {\n"+"".join("{"+k+"} {"+v+"}\n" for k,v in mapping.items())+"}\n"
    p.write_text(once(s," set r [get_registers $name]",code+""" set r [get_registers -nowarn $name]
 if {[get_collection_size $r]==0 && [info exists aliases659($name)]} {
  set name $aliases659($name)
  set r [get_registers $name]
 }"""),newline="\n")
    print(len(mapping),"map-reported aliases")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("board",type=Path);bind(p.parse_args().board)
