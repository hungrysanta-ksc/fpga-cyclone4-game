"""Witness export of valid N+1 records before consumption of N's last staged tile."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from check_nes_fault641 import MODULES,ROOT,digest,evidence
from nes_raw506 import once


def bench(tb):
    tb=once(tb,"wire export_tx;","""wire export_tx;wire [95:0] record649;integer headers649=0,values649=0;
 always @(posedge nes)if(export_tx)begin
  if(record649[92:77]!==GEN643+1 || !dut.plan_closed || !lease || captured_gen!==GEN643)
    $fatal(1,"early export identity");
  if(record649[95:93]==7 && record649[76:64]==0)headers649++;
  else values649++;
 end""")
    tb=once(tb,".response(1'b0),.hit(1'b0)",".response(1'b1),.hit(1'b1)")
    tb=once(tb,".tx_data()",".tx_data(record649)")
    tb=once(tb,"reject_geometry=1;owned=1;offer_next=1;","reject_geometry=0;owned=1;offer_next=1;")
    tb=once(tb,"lease_fault!==0 || export_tx!==0)","lease_fault!==0 || headers649!=1 || values649<1)")
    start=tb.index("  tx[0]='hea;")
    end=tb.index("`else",start)
    return tb[:start]+"""  if(dut.bulk.consume_error || retire || exporter.generation!==GEN643+1 || !lease)
   $fatal(1,"old token or premature retirement");
  $display("HELD649 next=%0d headers=%0d values=%0d old=%0d",gen,headers649,values649,captured_gen);
"""+tb[end:]


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("bin","board","out"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    sof=digest(a.board/"output_files/board.sof")
    assert sof==evidence("reject643-package.json")["board"]["SHA"]["board.sof"]
    a.out.mkdir(parents=True,exist_ok=False)
    modules=["nes_"+n+".sv" for n in MODULES]+["nes_native_export203.sv"]
    for n in modules:shutil.copyfile(a.board/n,a.out/n)
    for n in ("spi200_bus.svh","fault641_tb.sv"):shutil.copyfile(ROOT/"tests/nes-functional"/n,a.out/n)
    n="reject643.svh";(a.out/n).write_text(bench((ROOT/"tests/nes-functional"/n).read_text()))
    steps=[("vlib",["work"]),("vlog",["-sv","+define+WITNESS642+REJECT643+DEFER643",*modules,"fault641_tb.sv"]),
           ("vsim",["-c","fault641_tb","-gGEN643=97","-gHOST_PHASE=8","-gNES_HALF=23.281","-gSPI_HALF=190.476",
                    "-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"])]
    for tool,args in steps:
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
    out=(a.out/"vsim.log").read_text()
    assert "HELD649 next=98" in out and "PASS643 gen=97 STOP" in out
    (a.out/"result.json").write_text(json.dumps(dict(SOF=sof,log=digest(a.out/"vsim.log"),
        witness=next(x for x in out.splitlines() if "HELD649 next=" in x),rtl={n:digest(a.out/n) for n in modules}),indent=2)+"\n")
