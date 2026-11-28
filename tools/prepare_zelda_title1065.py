"""Exclude transparent OBJ rows only after both CHR fetches pass the pair checks."""
from shutil import copytree
from prepare_nes_headers1064 import OUT as PREVIOUS
from prepare_sxrom1065 import OUT

BOARD=OUT/"board-zelda"

def apply(board):
    def change(file,a,b):
        p=board/file
        s=p.read_text()
        if s.count(a)!=1: raise ValueError((file,a))
        p.write_text(s.replace(a,b))
    for name in ("nes_native_planes165","nes_native_frame201","nes_native_capture201"):
        change(name+".sv","input wire ppu_read,ppu_valid","input wire [7:0] pattern_data,input wire ppu_read,ppu_valid")
    change("nes_live_joint.sv",".ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid)",".pattern_data(ppumem_din),.ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid)")
    change("nes_native_frame201.sv",".ppu_read(ppu_read),.ppu_valid(ppu_valid)",".pattern_data(pattern_data),.ppu_read(ppu_read),.ppu_valid(ppu_valid)")
    change("nes_native_planes165.sv"," wire mark=mark_low || mark_high;",""" wire mark=mark_low || mark_high;
 // Same CHR RAM bytes sampled by the live PPU at each sprite shifter load.
 // A transparent row cannot win sprite priority or contribute a pixel.
 reg low_has_ink;
 always @(posedge clk) if(mark_low) low_has_ink<=|pattern_data;
 wire visible_pair=!is_obj || low_has_ink || (|pattern_data);""")
    change("nes_native_planes165.sv","if(mark_high)begin event_valid","if(mark_high && visible_pair)begin event_valid")
    for f in ("rtl/ppu.sv","rtl/nes.v","nes_probe.sv"):
        change(f,"output wire native_scroll_access,","output wire native_scroll_access, native_addr_write,")
    for f in ("rtl/nes.v","nes_probe.sv"):
        change(f,".native_scroll_access(native_scroll_access),",".native_addr_write(native_addr_write),.native_scroll_access(native_scroll_access),")
    change("rtl/ppu.sv","assign native_scroll_access=", "assign native_addr_write=(write && ppu_ain==6) || native_scroll_effect;\nassign native_scroll_access=")
    change("nes_live_joint.sv","wire capture_begin611,","wire native_addr_write;\n wire capture_begin611,")
    change("nes_live_joint.sv",".pattern_data(ppumem_din)",".address_change(native_addr_write),.pattern_data(ppumem_din)")
    for f in ("nes_native_capture201.sv","nes_native_frame201.sv","nes_native_planes165.sv"):
        change(f,"input wire [7:0] pattern_data","input wire address_change,input wire [7:0] pattern_data")
    change("nes_native_frame201.sv",".pattern_data(pattern_data)",".address_change(address_change),.pattern_data(pattern_data)")
    change("nes_native_planes165.sv"," wire raw_target=", """ // The CPU can replace v during a visible background fetch. Capture the
 // complete composited line and require its raw receipt at row_commit.
 wire split_write=capturing && ppu_ce && visible_line && dot>=2 && dot<=256 &&
                  display_mask[3] && address_change;
 wire raw_target=""")
    change("nes_native_planes165.sv","!is_obj && render_change &&","!is_obj && (render_change || split_write) &&")
    change("nes_native_planes165.sv","wire cancel_pair=render_change &&","wire cancel_pair=(render_change || split_write) &&")
    change("nes_native_planes165.sv","   if(render_change)begin","   if(split_write)begin raw_current<=1; if(cancel_pair)pair_pending<=0;end\n   if(render_change)begin")

def prepare():
    copytree(PREVIOUS/"board-1",BOARD,dirs_exist_ok=True)
    apply(BOARD)

if __name__=="__main__": prepare()
