"""Use the fitted board endpoint's simultaneous plan-ready and held-tile flags."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from check_nes_fault641 import MODULES,ROOT,digest,evidence
from nes_raw506 import once


def check(a):
    sof=digest(a.board/"output_files/board.sof")
    assert sof==evidence("reject643-package.json")["board"]["SHA"]["board.sof"]
    a.out.mkdir(parents=True,exist_ok=False)
    files=["nes_"+m+".sv" for m in MODULES]
    for f in files:shutil.copyfile(a.board/f,a.out/f)
    test=ROOT/"tests/nes-functional"
    shutil.copyfile(test/"spi200_bus.svh",a.out/"spi200_bus.svh")
    # Split the blank tile (slot 0) from the following BG (slot 3). Thus a
    # descriptor is visible even before the END-only plan is submitted.
    tb=once((test/"fault641_tb.sv").read_text(),"tx[10]=1;tx[11]=0;","tx[10]=3;tx[11]=0;")
    (a.out/"fault641_tb.sv").write_text(tb)
    (a.out/"reject643.svh").write_text("""parameter integer GEN643=97;
assign export_drop=0;assign export_reason=0;
initial begin
 reg [31:0] token;
 repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
 gen=GEN643-1;capture_begin=1;@(negedge nes);capture_begin=0;gen=GEN643;owned=1;
 @(negedge nes);release_frame=1;@(negedge nes);release_frame=0;owned=0;
 batch('h82,GEN643,0);status197();
 if(rx197[3]!==1 || rx197[6]!==1 || rx197[8]!==16 || rx197[5]!==1)$fatal(1,"simultaneous E8");
 token={rx197[17],rx197[16],rx197[15],rx197[14]};
 batch('h83,GEN643,0);status197();
 if(rx197[3]!==2 || rx197[5]!==2 || rx197[6]!==1 || token!=={rx197[17],rx197[16],rx197[15],rx197[14]})$fatal(1,"lost prior tile");
 for(int tile=0;tile<2;tile++)begin
  if(rx197[8]!==16 || rx197[6]!==1 || {rx197[17],rx197[16],rx197[15],rx197[14]}!==(token+tile))$fatal(1,"token");
  for(int i=0;i<16;i++)begin
   @(negedge host);addr='h400800+i;rd_n=0;repeat(8)@(negedge host);
   if(oe!==0 || dout!==0)$fatal(1,"read");rd_n=1;repeat(8)@(negedge host);
  end
  for(int i=0;i<4;i++)write_bus('h604c+i,rx197[14+i]);
  write_bus('h6050,'ha5);status197();
 end
 if(rx197[6]!==0 || hf||nf||lease_fault||!lease||retire)$fatal(1,"premature retire");
 reset=1;repeat(12)@(negedge nes);if(lease||retire||hf||nf)$fatal(1,"STOP");
 $display("PASS651 simultaneous E8, END and two ordered receipts, STOP");$finish;
end
""")
    for tool,args in (("vlib",["work"]),("vlog",["-sv","+define+WITNESS642+REJECT643",*files,"fault641_tb.sv"]),
                      ("vsim",["-c","fault641_tb","-gHOST_PHASE=8","-gNES_HALF=23.281","-gSPI_HALF=190.476",
                               "-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    assert "PASS651" in (a.out/"vsim.log").read_text()
    return dict(SOF=sof,log=digest(a.out/"vsim.log"),plan_ready_with_tile=True,receipts=2,STOP=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("bin","board","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();result=check(a);(a.out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
