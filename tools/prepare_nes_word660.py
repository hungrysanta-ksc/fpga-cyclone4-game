"""Build 660 from the verified 657 board; retain its staging, ROM and ARM interfaces."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_bg659 import board as layout_board


def board(base,out,shared=False,one_word=False,peer=False):
    layout_board(base,out,window=False)
    def edit(name,fn):
        p=out/name;p.write_text(fn(p.read_text()),newline="\n")
    # Preserve the physical 16-bit sample. Core/OBJ single-byte replies still
    # use the original lane latch, generation tag and checked acknowledgement.
    def physical(s):
        if shared:
            s=once(s," output wire rom_ready,"," output wire [15:0] bg_word,output wire rom_ready,")
            s=once(s,"reg [7:0] data_hold;","reg [15:0] data_hold;")
            s=once(s,"reg [7:0] reply_data;","reg [15:0] reply_data;")
            s=once(s,"assign rom_data=reply_data;","assign bg_word=reply_data;assign rom_data=address_hold[0]?reply_data[7:0]:reply_data[15:8];")
            s=once(s,"assign check_data=data_hold;","assign check_data=lane?data_hold[7:0]:data_hold[15:8];")
            s=once(s,"data_hold[3:0]<=lane?psram_data[3:0]:psram_data[11:8];","{data_hold[11:8],data_hold[3:0]}<={psram_data[11:8],psram_data[3:0]};")
            return once(s,"data_hold[7:4]<=lane?psram_data[7:4]:psram_data[15:12];","{data_hold[15:12],data_hold[7:4]}<={psram_data[15:12],psram_data[7:4]};")
        s=once(s," output wire rom_ready,"," output reg [15:0] bg_word,output wire rom_ready,")
        return once(s," wire capture_next=",""" (* preserve *) reg [15:0] bg_hold;
 always @(posedge mem_clk)if(capture_low && capture_high)bg_hold<=psram_data;
 always @(posedge clk)bg_word<=bg_hold;
 wire capture_next=""")
    edit("nes_rom_physical.sv",physical)
    for name in ("nes_rom_boot.sv","nes_spi_boot.sv"):
        edit(name,lambda s:once(once(s,"(input wire clk,mem_clk","(output wire [15:0] bg_word,input wire clk,mem_clk"),".rom_data(rom_data),",".rom_data(rom_data),.bg_word(bg_word),"))
    edit("nes_live_joint.sv",lambda s:once(once(once(s,"wire [7:0] native_mem_data;","wire [7:0] native_mem_data;wire [15:0] bg_word;"),".rom_data(native_mem_data),",".rom_data(native_mem_data),.bg_word(bg_word),"),".mem_data(native_mem_data),",".mem_data(native_mem_data),.bg_word(bg_word),"))
    for name,anchor in (("nes_direct206.sv",".mem_data(mem_data),"),("nes_source_tile192.sv",".back_data(arb_data)")):
        edit(name,lambda s:once(once(s,"input wire [7:0] mem_data","input wire [15:0] bg_word,input wire [7:0] mem_data"),anchor,".bg_word(bg_word),"+anchor))
    def cache(s):
        s=once(s," input wire [7:0] back_data"," input wire [15:0] bg_word,input wire [7:0] back_data")
        s=once(s,"reg [7:0] bg_bytes[0:15];","reg [15:0] bg_rows[0:7];")
        s=once(s,"reg [15:0] bg_valid;","reg [7:0] bg_valid;")
        s=once(s,"bg_valid[address[3:0]]","bg_valid[address[2:0]]")
        s=once(s,"bg_bytes[address[3:0]]","address[3]?bg_rows[address[2:0]][7:0]:bg_rows[address[2:0]][15:8]")
        s=once(s,"bg_bytes[held_address[3:0]]<=back_data;","bg_rows[held_address[2:0]]<=bg_word;")
        s=once(s,"?bg_valid:16'b0)|(16'b1<<held_address[3:0])","?bg_valid:8'b0)|(8'b1<<held_address[2:0])")
        if one_word:
            s=once(s,"reg [15:0] bg_rows[0:7];","reg [15:0] bg_row;")
            s=once(s,"reg [7:0] bg_valid;reg [17:0] bg_tag;","reg bg_valid;reg [15:0] bg_key;")
            s=once(s,"bg_tag==address[21:4]&&bg_valid[address[2:0]]","bg_valid && bg_key=={address[16:4],address[2:0]}")
            s=s.replace("bg_rows[address[2:0]]","bg_row")
            s=once(s,"bg_rows[held_address[2:0]]<=bg_word;bg_tag<=held_address[21:4];",
                   "bg_row<=bg_word;bg_key<={held_address[16:4],held_address[2:0]};")
            s=once(s,"bg_valid<=(bg_tag==held_address[21:4]?bg_valid:8'b0)|(8'b1<<held_address[2:0]);","bg_valid<=1;")
        if peer:
            s=once(s,"reg [15:0] bg_row;","reg [7:0] sibling;")
            s=once(s,"reg bg_valid;reg [15:0] bg_key;reg [7:0] bg_reply;","reg bg_valid;")
            s=once(s,"wire bg_hit=bg_valid && bg_key=={address[16:4],address[2:0]};","")
            s=once(s," reg [15:0] held_generation;"," wire bg_hit=bg_valid && address==(held_address^22'h8);\n reg [15:0] held_generation;")
            s=once(s,"if(!request_obj&&bg_hit)bg_reply<=address[3]?bg_row[7:0]:bg_row[15:8];","bg_valid<=0;")
            s=once(s,"bg_row<=bg_word;bg_key<={held_address[16:4],held_address[2:0]};","sibling<=held_address[3]?bg_word[15:8]:bg_word[7:0];")
            s=once(s,"state==BG_HIT?bg_reply","state==BG_HIT?sibling")
        return s
    edit("nes_chr_cache611.sv",cache)
    constraints="""
# The sampled pair is held through the existing synchronized physical ACK.
foreach i {0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15} {
 set src660 [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|bg_hold[%d]} $i]]
 set dst660 [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|bg_word[%d]} $i]]
 set_max_delay 23.808 -from $src660 -to $dst660
 set_false_path -hold -from $src660 -to $dst660
}
"""
    if shared:
        constraints=constraints.replace("0 1 2 3 4 5 6 7 8","8").replace("|bg_hold[","|data_hold[").replace("|bg_word[","|reply_data[")
    edit("board.sdc",lambda s:s+constraints)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    p.add_argument("--shared",action="store_true");p.add_argument("--one-word",action="store_true");p.add_argument("--peer",action="store_true");a=p.parse_args();board(a.base,a.out,a.shared,a.one_word or a.peer,a.peer)
