"""Check peer validity, noncanonical BG fallback, OBJ history, STOP and error paths."""
import argparse,shutil,subprocess
from pathlib import Path
from nes_raw506 import once


def guard(a):
    a.out.mkdir(parents=True,exist_ok=False)
    files=[n+".sv" for n in ("nes_source_tile192","nes_tile205","nes_native_arbiter165","nes_chr_cache611","nes_obj_capture611")]
    for f in files:shutil.copyfile(a.board/f,a.out/f)
    s=Path(__file__).with_name("nes_source_board611_tb.sv").read_text()
    width=8 if a.policy in ("emit","short") else 16
    if a.policy=="short":
        s=once(s," nes_source_tile192 #"," wire plan_short=plan_rows==48'o7766554433221100 && plan_alt_mask==0;\n nes_source_tile192 #")
    s=once(s," reg [21:0] physical;",f" reg [{width-1}:0] bg_word;reg [21:0] physical;")
    s=once(s,"mem_data=value(physical);","mem_data=value(physical);bg_word="+("value(physical|8);" if width==8 else "{value(physical&~8),value(physical|8)};"))
    s=once(s,'reads-prior_reads!=17','reads-prior_reads!=9')
    for msg in ("BG second tile missed","OBJ destroyed BG history"):
        s=once(s,'reads!=prior_reads)$fatal(1,"'+msg,'reads-prior_reads!='+('0' if a.policy=='full' else '8')+')$fatal(1,"'+msg)
    s=once(s,"expected=out_index>=16?0:value(16*plan_tag+out_index/2+8*(out_index%2));",
        """expected=out_index>=16?0:value(16*((!out_index[0] && plan_alt_mask[out_index/2])?
                    plan_alt_tags[13*(out_index/2)+:13]:plan_tag)+(plan_rows[3*(out_index%16)+:3])+8*(out_index%2));""")
    s=once(s,"fresh;corrupt=1;launch(0,2);","""fresh;plan_rows[5:3]=6;plan_alt_mask=1;plan_alt_tags[12:0]=7;
  launch(0,4);consume(16);plan_rows=48'o7766554433221100;plan_alt_mask=0;
  // Stop with the sibling available but not retired to the staging sink.
  fresh;launch(0,9);while(!out_valid || out_index!=1)tick;
  out_ready=0;repeat(9)begin if(!out_valid || out_data!==value(16*9+8))$fatal(1,"peer changed");tick;end
  stop=1;#1;if(out_valid)$fatal(1,"cancelled peer");tick;stop=0;out_ready=1;
  repeat(12)tick;prior_reads=reads;launch(0,9);consume(16);
  if(reads-prior_reads!=8)$fatal(1,"cold retry retained partial word");
  fresh;corrupt=1;launch(0,2);""")
    s=once(s," integer prior_reads;",""" reg [21:0] saved_address;reg [15:0] saved_gen;
 always @(posedge clk)begin
  if(dut.arb_request&&dut.arb_ready)begin saved_address<=dut.arb_address;saved_gen<=dut.arb_generation;end
  if(dut.arbiter.owner && {dut.arb_address,dut.arb_generation}!=={saved_address,saved_gen})
   $fatal(1,"pending granted key changed");
 end
 integer prior_reads;""")
    (a.out/"tb.sv").write_text(s,newline="\n")
    for tool,args in (("vlib",["work"]),("vlog",["-sv",*files,"tb.sv"]),("vsim",["-c","nes_source_board611_tb","-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    assert "PASS611" in (a.out/"vsim.log").read_text()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("board","out","bin"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--policy",choices=("full","small","emit","short"),required=True)
    guard(p.parse_args())
