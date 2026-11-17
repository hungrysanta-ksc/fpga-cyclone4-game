"""Use spare capture-port cycles to duplicate an OBJ byte into an unclaimed line."""
from pathlib import Path
import sys
from prepare_nes_mask820 import edit
import shutil

def create(temp,held=False):
    base=temp/"nes-trial816-board820b"
    dst=temp/("nes-trial816-board822held" if held else "nes-trial816-board822m")
    dst.mkdir()
    for sub in ("rtl","sys"):
        shutil.copytree(base/sub,dst/sub)
    for f in base.iterdir():
        if f.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".tcl",".hex"):
            shutil.copyfile(f,dst/f.name)
    cap=dst/"nes_obj_capture611.sv"
    edit(cap,"input wire query,","input wire alternate,query,")
    edit(cap,"reg [21:0] directory","reg [22:0] directory")
    edit(cap,"reg [21:0] entry","reg [22:0] entry")
    a=cap.read_text()
    old=a[a.index(" wire [7:0] write_line"):a.index(" wire owns=")]
    edit(cap,old,""" // A mirror may occupy only an empty line or another mirror. A new primary
 // sample always displaces it. Neither a query nor a capture waits for a copy.
 reg mirror_pending, reply_alternate;
 wire [6:0] mirror_index=wr_addr[10:4]^{1'b0,wr_addr[16:11]};
 wire [6:0] query_index=query_address[10:4]^(alternate?{1'b0,query_address[16:11]}:7'd0);
 wire copy_read=pending && capturing && !seal && !lookup && wr_addr[16:11]!=0;
 wire [7:0] read_line=take?{bank,sample_address[10:4]}:
                        copy_read?{bank,mirror_index}:{query_gen[0],query_index};
 wire copy_write=mirror_pending && capturing && !seal && !clearing && !pending &&
                 (entry[22] || entry[15:0]==0) &&
                 (!(take||lookup) || read_line!={bank,mirror_index});
 wire [7:0] write_line=clearing&&!pending?{clear_bank,clear_index}:
                       {bank,copy_write?mirror_index:wr_addr[10:4]};
 wire [15:0] mask=(entry[22]==copy_write && entry[21:16]==wr_addr[16:11]?
                   entry[15:0]:16'b0)|(16'h1<<wr_addr[3:0]);
""")
    edit(cap,"entry[21:16]==tag&&","entry[22]==reply_alternate&&entry[21:16]==tag&&")
    edit(cap,"else if(live&&pending) directory[write_line]<={wr_addr","else if(live&&(pending||copy_write)) directory[write_line]<={copy_write,wr_addr")
    edit(cap,"if(take||(lookup&&owns))","mirror_pending<=live&&copy_read;\n  if(take||copy_read||(lookup&&owns))")
    edit(cap,"if(live&&pending) bytes[{bank,wr_addr[10:0]}]","if(live&&(pending||copy_write)) bytes[{write_line,wr_addr[3:0]}]")
    edit(cap,"fetched<=bytes[{query_gen[0],query_address[10:0]}];","reply_alternate<=alternate;\n   fetched<=bytes[{query_gen[0],query_index,query_address[3:0]}];")
    cache=dst/"nes_chr_cache611.sv"
    edit(cache,"MISS=2,WAIT=3;","MISS=2,WAIT=3,ALT=4,ALT_REPLY=5;")
    edit(cache,".query(accept&&request_obj),.query_gen(generation),.query_address(address[16:0]),",
         """.alternate(state==ALT),.query((accept&&request_obj)||state==ALT),
  .query_gen(state==ALT?held_generation:generation),
  .query_address(state==ALT?held_address[16:0]:address[16:0]),""")
    edit(cache,"wire cached=state==LOOKUP&&","wire cached=(state==LOOKUP||state==ALT_REPLY)&&")
    edit(cache,"LOOKUP:if(qresponse)state<=cached?IDLE:MISS;","""LOOKUP:if(qresponse)state<=cached?IDLE:ALT;
   ALT:if(qready)state<=ALT_REPLY;
   ALT_REPLY:if(qresponse)state<=cached?IDLE:MISS;""")
    if held:
        edit(cache,"module nes_chr_cache611 (","module nes_chr_cache611 #(parameter HELD_PLAN=0) (")
        edit(cache,"reg [21:0] held_address;\n reg [15:0] held_generation;","""reg [21:0] saved_address;reg [15:0] saved_generation;
 // The external plan is leased through tile_done. tile205 holds its byte
 // index through WAIT; its STOP/fault cancels this port before the next plan.
 wire [21:0] held_address=HELD_PLAN?address:saved_address;
 wire [15:0] held_generation=HELD_PLAN?generation:saved_generation;""")
        edit(cache,"held_address<=address;held_generation<=generation;","saved_address<=address;saved_generation<=generation;")
        edit(dst/"nes_source_tile192.sv","nes_chr_cache611 cache(","nes_chr_cache611 #(.HELD_PLAN(EXTERNAL_PLAN)) cache(")
    return dst

if __name__=="__main__":
    create(Path(sys.argv[1]),"--held" in sys.argv)
