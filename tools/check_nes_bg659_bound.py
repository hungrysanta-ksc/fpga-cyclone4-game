"""Replay the linked CPU's failing 16-byte bursts on the actual aperture RTL.
Give it the full 4-byte lead and even a one-cycle memory response."""
import argparse,csv,shutil,subprocess
from pathlib import Path
from test_nes_service509_schedule import Calendar

TB=r"""
`timescale 1ns/1ps
module deadline_tb;
 reg clk=0,reset=1,slot=1,rd=1,wr=1;always #5 clk=~clk;
 reg[23:0] addr=0;wire issue,owned,sel,fault;wire[7:0] data;wire[21:0] request;
 reg response=0;reg[21:0] reply=0;
 always @(posedge clk)begin response<=!reset && issue;if(issue)reply<=request;end
 nes_bg_window659 w(.clk(clk),.reset(reset),.stop(1'b0),.slot(slot),.safe(1'b1),.normal_request(1'b0),
  .mem_ready(1'b1),.mem_response(response),.mem_error(1'b0),.mem_response_address(reply),.mem_word(16'ha55a),
  .address(addr),.read_n(rd),.write_n(wr),.issue(issue),.request_address(request),.owned(owned),.selected(sel),.data(data),.fault(fault));
 integer fd,out,g,phase,i,grant,n,count=0;
 initial begin fd=$fopen("schedule.txt","r");out=$fopen("bounds.txt","w");
 while($fscanf(fd,"%d %d %d",g,phase,n)==3)begin
  reset=1;rd=1;wr=1;slot=1;repeat(3)@(negedge clk);reset=0;
  addr=24'h520000;wr=0;@(negedge clk);wr=1;rd=0;wait(data[0]);@(negedge clk);
  rd=1;slot=0;
  for(i=0;i<128;i++)begin
   if($fscanf(fd,"%d",grant)!=1)$fatal;slot=grant!=0;addr=24'h500000+i/8;rd=i%8>=4;
   @(negedge clk);
  end
  if(!fault || w.consumed>=16 || w.consumed>4+2*n)$fatal(1,"false receipt");
  $fwrite(out,"%d %d %d %d\n",g,phase,n,w.consumed);count++;
 end
 if(count!=4)$fatal;$display("PASS659 four measured grant windows reject an incomplete burst");$finish;end
endmodule
"""

def run(a):
    out=a.out;out.mkdir(parents=True,exist_ok=False);calendar=Calendar(a.traces/"nes-service509-rom03")
    shutil.copyfile(a.board/"nes_bg_window659.sv",out/"window.sv");(out/"tb.sv").write_text(TB)
    with (out/"schedule.txt").open("w") as f:
        for g,suffix in ((954,"live"),(955,"live955")):
            for n in (1,2):
                source=a.traces/f"nes-bg659-calendar{n}{suffix}"
                records=list(csv.DictReader((source/"bus659.csv").read_text().splitlines()))
                rr=[int(row["clock"]) for row in records if row["event"]=="read"]
                assert len(rr)==16 and rr[-1]-rr[0]==120
                slots=set();at=rr[0]
                while True:
                    grant,resp=calendar.select(at)
                    if grant>=rr[0]+128:break
                    slots.add(grant-rr[0]);at=grant+1
                print(g,n,len(slots),*(int(i in slots) for i in range(128)),file=f)
    for tool,args in (("vlib",["work"]),("vlog",["-sv","window.sv","tb.sv"]),("vsim",["-c","-quiet","deadline_tb","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    assert "PASS659" in (out/"vsim.log").read_text()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("traces","board","out","bin"):p.add_argument("--"+n,type=Path,required=True)
    run(p.parse_args())
