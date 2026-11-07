"""Use the original checked byte plus the other lane only for a canonical BG pair."""
from nes_raw506 import once
from prepare_nes_word660 import board

def emit_board(base,out):
    board(base,out)
    def edit(name,fn):
        p=out/name;p.write_text(fn(p.read_text()),newline="\n")
    # Native byte retains address selection and existing CDC endpoints. Only
    # the second plane (low data pins) needs an additional capture/return lane.
    for f in ("nes_rom_physical.sv","nes_rom_boot.sv","nes_spi_boot.sv","nes_live_joint.sv","nes_direct206.sv","nes_source_tile192.sv"):
        edit(f,lambda s:s.replace("[15:0] bg_word","[7:0] bg_word").replace("[15:0] bg_hold","[7:0] bg_hold").replace("bg_hold<=psram_data;","bg_hold<=psram_data[7:0];"))
    edit("board.sdc",lambda s:once(s,"foreach i {0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15} {\n set src660","foreach i {0 1 2 3 4 5 6 7} {\n set src660"))
    def cache(s):
        s=once(s,"input wire [15:0] bg_word,","")
        begin=s.index(" reg held_obj;");end=s.index(" reg [21:0] held_address;",begin)
        s=s[:begin]+s[end:]
        s=s.replace("(bg_hit||back_idle)","back_idle").replace("||state==BG_HIT","").replace("state==BG_HIT?bg_reply:","")
        start=s.index("held_obj<=request_obj;");end=s.index("  if(!live)state",start)
        s=s[:start]+"\n  end\n"+s[end:]
        return s.replace("request_obj?LOOKUP:bg_hit?BG_HIT:MISS","request_obj?LOOKUP:MISS").replace("   BG_HIT:state<=IDLE;\n","").replace(",BG_HIT=4","")
    edit("nes_chr_cache611.sv",cache)
    edit("nes_source_tile192.sv",lambda s:once(once(s,".bg_word(bg_word),.back_data",".back_data"),".response_data(reply_data)",".response_data(reply_data),.second_plane(bg_word)"))
    def tile(s):
        s=once(s,"input wire [7:0] response_data","input wire [7:0] second_plane,input wire [7:0] response_data")
        s=once(s," wire lease_ok=",""" reg [7:0] peer_byte;
 wire pair_bg=kind==0 && rows==48'o7766554433221100 && alt_mask==0;
 wire lease_ok=""")
        s=once(s,"held_byte<=response_data;state<=EMIT;","held_byte<=response_data;peer_byte<=second_plane;state<=EMIT;")
        return once(s,"else begin index<=index+1'b1;state<=FETCH;end","""else begin
      index<=index+1'b1;
      if(pair_bg && !index[0])begin held_byte<=peer_byte;state<=EMIT;end
      else state<=FETCH;
     end""")
    edit("nes_tile205.sv",tile)

if __name__=="__main__":
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();emit_board(a.base,a.out)
