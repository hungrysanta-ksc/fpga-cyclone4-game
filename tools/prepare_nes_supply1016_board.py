"""Substitute a passive per-operand observer in the routed MMC1012 source project."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from nes_display1010 import ROOT, once

def prepare(original, dst):
    reference=json.loads((ROOT/"analysis/trial1010-package.json").read_bytes())
    if hashlib.sha256((original/"output_files/board.sof").read_bytes()).hexdigest()!=reference["image"]["SOF"]:
        raise ValueError("Unexpected MMC1012 board source")
    dst.mkdir(parents=True)
    for name in ("rtl","sys"):
        shutil.copytree(original/name,dst/name)
    for f in original.iterdir():
        if f.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".hex",".tcl"):
            shutil.copyfile(f,dst/f.name)
    for name in ("nes_supply1016","nes_supply1016_host"):
        shutil.copyfile(ROOT/"tests/nes-functional"/(name+".sv"),dst/(name+".sv"))
    def edit(name,*pairs):
        f=dst/name
        s=f.read_text()
        for a,b in pairs:
            s=once(s,a,b)
        f.write_text(s,newline="\n")
    edit("board.qsf",("SYSTEMVERILOG_FILE nes_display1010.sv","SYSTEMVERILOG_FILE nes_supply1016.sv\nset_global_assignment -name SYSTEMVERILOG_FILE nes_supply1016_host.sv"))
    pins="input wire bw1016,input wire [31:0] word1016,input wire origin1016,input wire [8:0] rd1016,output wire [31:0] q1016,"
    conn=".bw1016(bw1016),.word1016(word1016),.origin1016(origin1016),.rd1016(rd1016),.q1016(q1016),"
    edit("nes_chr_cache611.sv",(" input wire clk,"," output wire capture_hit1016,input wire clk,"),
         (" wire returned=", " assign capture_hit1016=live&&cached;\n wire returned="))
    edit("nes_e9_rows914.sv",(" input wire page963"," output wire fg1016,row1016,spec1016,input wire page963"),
         (" assign request=foreground"," assign fg1016=foreground,row1016=hit_reply&&live,spec1016=spec_owner;\n assign request=foreground"))
    edit("nes_source_tile192.sv",(" input wire hint,", " "+pins+"input wire host1016,input wire hint,"),
         (" generate if(USE_CACHE)", " wire cap_hit1016,fg1016,row1016,spec1016;\n generate if(USE_CACHE)"),
         (" cache(.clk(clk)", " cache(.capture_hit1016(cap_hit1016),.clk(clk)"),
         ("end else begin:no_cache","end else begin:no_cache\n  assign cap_hit1016=0;"),
         (" ahead(.page963"," ahead(.fg1016(fg1016),.row1016(row1016),.spec1016(spec1016),.page963"),
         ("endmodule",""" nes_supply1016 capture1016(.clk(clk),.stop(stop||reset||fault),.origin_toggle(origin1016),
 .start_tile(plan_valid&&plan_ready),.done(done),.tag(plan_tag),.kind(plan_kind),.generation(plan_generation),
 .accept_read(tile_request&&tile_ready),.reply(tile_response),.capture_hit(cap_hit1016),.row_hit(row1016),
 .foreground(fg1016),.grant(fg1016&&shared_ready),.demand(arb_request),.spec_busy(spec1016),
 .address(tile_address),.host_clk(host1016),.rd(rd1016),.bank_we(bw1016),.bank_word(word1016),.q(q1016));
endmodule"""))
    edit("nes_direct206.sv",("module nes_direct206(","module nes_direct206("+pins),
         (" source(.page963"," source(.host1016(host_clk),"+conn+".page963"))
    edit("nes_live_joint.sv",("module nes_live_joint(","module nes_live_joint("+pins),
         (" direct_path(.evt905"," direct_path("+conn+".evt905"))
    edit("fxpak_nes_screen137_top.sv",(" wire [2:0] evt905;"," wire bw1016,origin1016;wire [8:0] rd1016;wire [31:0] word1016,q1016;\n wire [2:0] evt905;"),
         (" core(.evt905"," core("+conn+".evt905"),(" screen_status(.trace_cancel"," screen_status("+conn+".trace_cancel"),
         (".bus_drive(consumer_dir&&!consumer_oe)",".drive_inputs({core_reset,sink_oe204,bus_oe_n,bus_dir,sink_dir204})"))
    f=dst/"nes_screen_status151.sv"
    s=once(f.read_text(),"module nes_screen_status151(","module nes_screen_status151(output wire bw1016,output wire [31:0] word1016,output wire origin1016,output wire [8:0] rd1016,input wire [31:0] q1016,")
    # Sample the inputs to the status-only bus direction calculation on edge
    # one, and register its result on edge two, aligned to the address sample.
    s=once(s,"input wire bus_drive","input wire [4:0] drive_inputs")
    s=once(s," reg [1:0] wr_sync"," reg [4:0] drive_meta;\n (* altera_attribute=\"-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS\" *) reg [1:0] wr_sync")
    s=once(s,"drive_sync<=0;","drive_sync<=0;drive_meta<=5'b10000;")
    s=once(s,"drive_sync<={drive_sync[0],bus_drive};","""drive_meta<=drive_inputs;
   drive_sync[1]<=!drive_meta[4] && (drive_meta[3]!=drive_meta[2]) &&
                  (drive_meta[3]?drive_meta[1]:drive_meta[0]);""")
    a=s.index(" nes_display1010 trace(");b=s.index(" assign selected",a)
    f.write_text(s[:a]+""" nes_supply1016_host trace(.clk(clk),.reset(reset),.active(active_sync[1]),.cancel(trace_cancel),
 .first_e9(first905),.writer(writer903),.returned(ret905),.reader(reader903),.kind(kind903),.units(units905),.token(token903),.generation(tr_gen),
 .retired(tr_retired),.op(tr_op),.query(trace_byte&&byte_count==0&&incoming==8'h78),
 .set_page(trace_byte&&byte_count==1&&command==8'h78),.incoming(incoming),.index(byte_count),
 .rd(rd1016),.q(q1016),.bank_we(bw1016),.bank_word(word1016),.origin_toggle(origin1016),.reply(trace_reply));
"""+s[b:],newline="\n")
    # Quartus can merge equivalent reset-release stages under different
    # hierarchy names. Follow only literal, documented map-report merges.
    # Every existing endpoint still has to resolve to exactly one register.
    edit("cdc181.sdc",(" if {[get_collection_size $r]!=1} {error", """ if {[get_collection_size $r]==0} {
  if {![info exists ::mapped1016]} {
   set f [open output_files/board.map.rpt r]
   set ::mapped1016 [dict create]
   while {[gets $f line]>=0} {
    if {[regexp {^; ([^;]+) +; Merged with ([^;]+) +;} $line all src dst]} {
     dict set ::mapped1016 [string trim $src] [string trim $dst]
    }
   }
   close $f
  }
  set visited {}
  while {[get_collection_size $r]==0 && [dict exists $::mapped1016 $name] && $name ni $visited} {
   lappend visited $name
   set name [dict get $::mapped1016 $name]
   set r [get_registers -nowarn $name]
  }
 }
 if {[get_collection_size $r]!=1} {error"""))
    for constraint in ("cdc576.sdc","initial576.sdc","fitter-guidance.sdc"):
        path=dst/constraint
        original_pin="{nes_screen_status151:screen_status|drive_sync[0]}"
        lines=path.read_text().splitlines()
        assert any(original_pin in line for line in lines)
        expanded=[]
        for line in lines:
            if original_pin in line:
                expanded.extend(line.replace(original_pin,"{nes_screen_status151:screen_status|drive_meta["+str(i)+"]}") for i in range(5))
            else:
                expanded.append(line)
        path.write_text("\n".join(expanded)+"\n",newline="\n")
    f=dst/"board.sdc";s=f.read_text()
    a=s.index("set src1010 ");b=s.index("\n",s.index("set_false_path -hold -from $src1010",a))
    f.write_text(s[:a]+"""set src1016 [cdc181_exact {nes_screen_status151:screen_status|nes_supply1016_host:trace|origin_toggle}]
set dst1016 [cdc181_exact {nes_live_joint:core|nes_direct206:direct_path|nes_source_tile192:source|nes_supply1016:capture1016|origin_sync[0]}]
set_max_delay 45.454 -from $src1016 -to $dst1016
set_false_path -hold -from $src1016 -to $dst1016"""+s[b:],newline="\n")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original",type=Path);p.add_argument("destination",type=Path)
    a=p.parse_args();prepare(a.original,a.destination)
