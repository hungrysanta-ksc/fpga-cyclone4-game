"""Recopy only dirty 1 KiB CHR pages. Preserve complete frozen snapshots for the consumer."""
import argparse
from pathlib import Path
from prepare_ff3_menu_board import menu_board
from prepare_nes_kirby1023 import edit


def board1045(board, client):
    menu_board(board, client)
    # Bit 2 clips only sprites in the left eight pixels. Rows already encode
    # the BG left edge and the sprite enable separately.
    edit(board, 'nes_native_raster181.sv',
         ("((display_mask & 8'hef)!=8'h08 && (display_mask & 8'hef)!=8'h0e)",
          "((display_mask & 8'he9)!=8'h08 || (display_mask[4] && display_mask[2]!=display_mask[1]))"))
    edit(board,'nes_checkpoint_memory.sv',
         ('output wire chr_changed,','output wire chr_changed, output wire [2:0] changed_page,'),
         (' wire [7:0] cpu_data=', ' assign changed_page=ppu_address[12:10];\n wire [7:0] cpu_data='))
    edit(board,'nes_live_joint.sv',
         ('nes_checkpoint_memory #', 'wire [2:0] changed_page;\n nes_checkpoint_memory #'),
         ('.chr_changed(chr_changed)', '.chr_changed(chr_changed),.changed_page(changed_page)'),
         ('.changed(chr_changed)', '.changed(chr_changed),.changed_page(changed_page)'))
    edit(board,'nes_chr_snapshot.sv',
         (' input wire [15:0] start_gen', ' input wire [2:0] changed_page,\n input wire [15:0] start_gen'),
         ('SAMPLE=7, LEAD=8;', 'SAMPLE=7, LEAD=8, SEEK=9;'),
         (' reg held, dirty;', ''' reg held;
 reg [7:0] dirty;
 // Clear on starting a copy. A later write to that page, even on the
 // selection edge or final byte, requires another pass before publication.
 genvar p;
 generate for(p=0;p<8;p=p+1) begin: page_tracking
   always @(posedge clk)
     if(reset || (changed && changed_page==p)) dirty[p]<=1;
     else if(state==SEEK && scan_addr[12:10]==p) dirty[p]<=0;
 end endgenerate'''),
         ('held<=0;dirty<=0;conflict<=0;', 'held<=0;conflict<=0;'),
         ('owner<=0;state<=FETCH;', 'owner<=0;state<=SEEK;'),
         ('    dirty<=1;\n', ''),
         ('    FETCH:state<=SETUP;', '''    SEEK:begin
     if(!(|dirty) && !changed)state<=CLEAN;
     else if(dirty[scan_addr[12:10]])state<=FETCH;
     else scan_addr[12:10]<=scan_addr[12:10]+1'b1;
    end
    FETCH:state<=SETUP;'''),
         ('''     if(&scan_addr)begin
      scan_addr<=0;dirty<=0;
      state<=(dirty||changed)?FETCH:CLEAN;
     end else begin scan_addr<=scan_addr+1'b1;state<=FETCH;end''',
          '''     scan_addr<=scan_addr+1'b1;
     state<=(&scan_addr[9:0])?SEEK:FETCH;'''),
         ('begin scan_addr<=0;dirty<=0;state<=FETCH;end', 'begin state<=SEEK;end'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('board',type=Path)
    p.add_argument('client',type=Path)
    args=p.parse_args()
    board1045(args.board,args.client)
