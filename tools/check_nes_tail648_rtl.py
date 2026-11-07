"""Exercise a queued table tail followed by SEAL on the fitted MMC643 endpoint."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from check_nes_fault641 import ROOT,digest,evidence
from nes_raw506 import once


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    rtl=["nes_"+name+".sv" for name in ("domain_reset124","sink_spi165","sink_bus165","sink_bridge165")]
    assert digest(a.board/"output_files/board.sof")==evidence("reject643-package.json")["board"]["SHA"]["board.sof"]
    for f in rtl+["sink-program.hex"]:
        shutil.copyfile(a.board/f,a.out/f)
    tb=(ROOT/"tests/nes-functional/sink_window184_tb.sv").read_text()
    tb=once(tb,"dut(clk,reset,active,stop,ss,","dut(clk,reset,active,stop,,ss,")
    start=tb.index("  fd=$fopen")
    end=tb.index(" end\n initial begin #100000000",start)
    tb=tb[:start]+"""  trace_on=0;
  lengths[1]=25;packet[1][0]=2;packet[1][1]=5;packet[1][12]=9;acks[1][1]=2;
  lengths[32]=184;packet[32][12]=168;
  // Every field of the preceding ordinary ACK must pass before SEAL is visible.
  for(i=0;i<12;i++)begin
   common_reset;send_packet(1);send_packet(32);inspect(1);
   for(j=0;j<12;j++)write_byte(24'h006010+j,acks[1][j]^(i==j?1:0));
   write_byte(24'h00601c,8'ha5);#1000;status;
   if(!fault||dut.ready||{rx[5],rx[6]}!=0||{rx[3],rx[4]}!=2)$fatal(1,"tail ACK %d",i);
  end
  common_reset;send_packet(1);send_packet(32);consume(1);status;
  if({rx[5],rx[6]}!=1||rx[7]!=0)$fatal(1,"tail is not display");
  consume(32);status;if({rx[5],rx[6]}!=2||rx[7]!=1||rx[8]!=3)$fatal(1,"display");
  common_reset;send_packet(1);send_packet(32);stop=1;read_byte(24'h006001,8'h80);release_read;
  if(dut.endpoint.retired!=0)$fatal(1,"STOP retired pending head");
  common_reset;status;if(rx[2]||{rx[3],rx[4],rx[5],rx[6]})$fatal(1,"restart");
  $display("PASS648 12 tail errors, ordered final ACK, STOP and reset");$finish;
"""+tb[end:]
    (a.out/"tail648_tb.sv").write_text(tb)
    for tool,args in (("vlib",["work"]),("vlog",["-sv",*rtl,"tail648_tb.sv"]),
                      ("vsim",["-c","sink_window184_tb","-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -f"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    assert "PASS648" in (a.out/"vsim.log").read_text()
    (a.out/"result.json").write_text(json.dumps(dict(bad_tail_ACK=12,ordered=True,STOP_reset=True,
        rtl={n:digest(a.out/n) for n in rtl},log=digest(a.out/"vsim.log")),indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("out","bin","board"):p.add_argument("--"+k,type=Path,required=True)
    run(p.parse_args())
