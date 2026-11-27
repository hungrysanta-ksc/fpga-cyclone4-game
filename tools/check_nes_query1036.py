"""Overlap the next immutable source lookup with an accepted record; compare full D1/D2 streams."""
import json
import re
import shutil
import tempfile
from pathlib import Path

import check_nes_kirby1035 as bench
from prepare_nes_ff3_checkpoint import ROOT, BASE, OUT
from prepare_nes_kirby1023 import edit


def run():
    bench.OUT = OUT
    with tempfile.TemporaryDirectory(prefix="query1036-") as folder:
        p=Path(folder)
        fixture,=BASE.parent.glob("nes-kirby1023/replay-*/frame3570.d1")
        blocks=[bytes.fromhex(s) for s in fixture.read_text().splitlines()]
        (p/"golden.hex").write_text("".join(f"@{i*256:x}\n"+b.hex(" ")+"\n" for i,b in enumerate(blocks)))
        (p/"lengths.hex").write_text("".join(f"{len(b):x}\n" for b in blocks))
        shutil.copy(fixture.with_suffix(".query"),p/"frame.query")
        rtl=BASE/"board-times"
        names=["nes_capture_lease201","nes_native_mailbox165","nes_native_export203","nes_native_spi165","nes_geometry_sender653","nes_input_times1035"]
        for n in names: shutil.copy(rtl/(n+".sv"),p)
        top=(rtl/"nes_live_joint.sv").read_text().split("native_export(",1)[1].split("));",1)[0]
        gates=[]
        for port,wire in [("enable","run_gate"),("start_permitted","start_gate"),("ack_accept","commit_gate")]:
            exp,=re.findall(r"\."+port+r"\(([^\n]*?)\),\.",top.replace(",\n",",.\n"))
            gates.append(f"wire {wire}={exp};")
        (p/"gate1035.svh").write_text("\n".join(gates))
        shutil.copy(ROOT/"tests/nes-functional/spi200_bus.svh",p)
        tb="kirby1035_export_tb.sv"
        shutil.copy(ROOT/"tests/nes-functional"/tb,p)
        edit(p,tb,("if(mode==2)begin", '$display("ENDD2 %.3f",$realtime-geometry_at);\n    if(mode==2)begin'))
        bench.command(p,"query-lib","vlib","work")
        results=[]
        for label in ["base","overlap"]:
            if label=="overlap":
                edit(p,"nes_native_export203.sv",
                     ("query=state==ASK&&", "query=(state==ASK||(state==VALUE&&tx_ready))&&"),
                     ("pack_count<=0;map_repeat<=0;state<=ASK;\n    end\n    META_END",
                      "pack_count<=0;map_repeat<=0;state<=query_index<limit?REPLY:ASK;\n    end\n    META_END"))
            bench.command(p,"query-"+label,"vlog","-sv","+define+INTERVAL1035",*[s+".sv" for s in names],tb)
            for phase,mode in [(1,0),(2,0),(1,1),(2,2)]:
                log=bench.command(p,f"query-{label}-{phase}-{mode}","vsim","-c","work.kirby1035_export_tb",
                                  f"+PHASE={phase}","+HOLD=11420","+LATE=0",f"+MODE={mode}",
                                  "-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0")
                assert "PASS1035 " in log
                match=re.search(r"ENDD2 ([\d.]+)",log)
                results.append(dict(label=label,phase=phase,mode=mode,
                                    geometry_to_last_data_D2_ns=float(match[1]) if match else None))
        (ROOT/"analysis/query1036.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__": run()

