"""Materialize a fixed-ARM comparison of rolling and paired RAM match searches."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import evidence,digest
from nes_raw506 import once


def board(base,out,mode):
    assert digest(base/"output_files/board.fit.rpt")==evidence("credit654-verification.json")["fit"]["fit_report"]
    names=list(evidence("trial613-package.json")["inputs"])+["nes_geometry_sender653.sv"]
    out.mkdir(parents=True,exist_ok=False)
    for name in names:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/name,target)
    codec=out/"nes_geometry_sender653.sv"
    s=codec.read_text()
    # The address read by CMP_B is the reference. A successful compare
    # advances from it by distance+1 byte. The current byte is never
    # reconstructed from origin+length, and even offsets preserve byte parity.
    start=s.index(" wire [7:0] scan=");end=s.index(" assign done=",start)
    s=s[:start]+""" wire [7:0] back={distance,1'b0};
 wire [7:0] step_delta=state==CMP_A ? -back :
                       state==CMP_B ? back+8'd1 : 8'd1;
 wire [7:0] advanced=address[7:0]+step_delta;
"""+s[end:]
    s=once(s,"if(lane==3)state<=CHOOSE;else begin lane<=lane+1'b1;state<=SEARCH;end",
           """address<={1'b1,index,1'b0};
   if(lane==3)state<=CHOOSE;else begin lane<=lane+1'b1;state<=SEARCH;end""")
    s=once(s,"length<=0;best<=0;state<=SEARCH;end",
           "length<=0;best<=0;address<=9'd256;state<=SEARCH;end")
    a=s.index("   SEARCH:");b=s.index("   CHOOSE:",a)
    s=s[:a]+"""   SEARCH:if(distance>index || address[7:1]==cells || length==32)finish_lane();
    else state<=CMP_A;
   CMP_A:begin first<=q;get({1'b1,advanced},CMP_B);end
   CMP_B:if(first!=q)finish_lane();
    else begin if(address[0])length<=length+1'b1;address<={1'b1,advanced};state<=SEARCH;end
"""+s[b:]
    s=once(s,"STEP:begin lane<=0;","STEP:begin address<={1'b1,index,1'b0};lane<=0;")
    s=once(s,"get({1'b1,index,1'b1},DIGEST)","get({1'b1,advanced},DIGEST)")
    s=once(s,"get({1'b1,index+7'd1,1'b0},DIGEST)","get({1'b1,advanced},DIGEST)")
    s=once(s,"get({1'b1,index,1'b1},LITERAL)","get({1'b1,advanced},LITERAL)")
    s=once(s,"get({1'b1,index,1'b1},RAW_HIGH)","get({1'b1,advanced},RAW_HIGH)")
    s=once(s,"get({1'b1,index+7'd1,1'b0},RAW_LOW)","get({1'b1,advanced},RAW_LOW)")
    s=once(s,"get({1'b0,meta+8'd1},FOLD)","get({1'b0,advanced},FOLD)")
    if mode in ("pair","mask","m9k"):
        # Both physical read ports address cells on one host edge. Use a
        # 16-bit word with byte enables; CPU/SPI still see the same bytes.
        s=once(s,"input wire [7:0] q,","input wire [7:0] q,input wire same_cell,output wire [6:0] reference,")
        a=s.index(" wire [7:0] back=");b=s.index(" assign done=",a)
        s=s[:a]+""" assign reference=address[7:1]-distance;
 wire [7:0] advanced=address[7:0]+(state==CMP_A?8'd2:8'd1);
"""+s[b:]
        a=s.index("   CMP_A:");b=s.index("   CHOOSE:",a)
        s=s[:a]+"""   CMP_A:if(!same_cell)finish_lane();
    else begin length<=length+1'b1;address<={1'b1,advanced};state<=SEARCH;end
"""+s[b:]
        f=out/"nes_native_spi165.sv";src=f.read_text()
        src=once(src,'reg [7:0] buffer[0:511];','reg [15:0] buffer[0:255];')
        src=once(src,".q(read_byte),",".q(read_byte),.same_cell(same_cell),.reference(reference),")
        src=once(src," nes_geometry_sender653 codec"," wire [6:0] reference;wire same_cell;\n nes_geometry_sender653 codec")
        a=src.index(" always @(posedge clk)begin\n  read_byte<=buffer");b=src.index(" reg [7:0] shift",a)
        src=src[:a]+""" // Port A is the input/serializer/codec write owner, or the search
 // reference reader when idle. Port B serves the cursor and SPI reads.
 wire cell_write=take_cell || cell_tail;
 wire do_write=!reset && (cell_write || write_serial || (active && wen652));
 wire [8:0] dest=cell_write?{1'b1,cells,cell_tail}:write_serial?{1'b0,used[7:0]}:{1'b0,wa652};
 wire [7:0] data_in=cell_write?(cell_tail?{1'b0,cell_upper}:record_data[7:0]):
                    write_serial?pack_byte:wd652;
 wire [7:0] port_a=do_write?dest[8:1]:{1'b1,reference};
 wire [8:0] src=active?addr652:{1'b0,spi_index};
 reg [15:0] current_word,reference_word;reg high_byte;
 always @(posedge clk)begin
  if(do_write && !dest[0])buffer[port_a][7:0]<=data_in;
  if(do_write && dest[0])buffer[port_a][15:8]<=data_in;
  reference_word<=buffer[port_a];
  current_word<=buffer[src[8:1]];high_byte<=src[0];
 end
 assign same_cell=current_word==reference_word;
 always @*read_byte=high_byte?current_word[15:8]:current_word[7:0];
"""+src[b:]
        if mode=="m9k":
            # Byte enables on the same registered address as port-A reads.
            # Inferred split-byte arrays can be duplicated by the Lite MAP.
            src=once(src,' (* ramstyle="M9K" *) reg [15:0] buffer[0:255];','')
            a=src.index(" reg [15:0] current_word,reference_word;");b=src.index(" assign same_cell",a)
            src=src[:a]+""" wire [15:0] current_word,reference_word;reg high_byte;
 always @(posedge clk)high_byte<=src[0];
 altsyncram #(.operation_mode("BIDIR_DUAL_PORT"),.ram_block_type("M9K"),
  .intended_device_family("Cyclone IV E"),.width_a(16),.widthad_a(8),.numwords_a(256),
  .width_b(16),.widthad_b(8),.numwords_b(256),.width_byteena_a(2),.byte_size(8),
  .address_reg_b("CLOCK0"),.rdcontrol_reg_b("CLOCK0"),.wrcontrol_wraddress_reg_b("CLOCK0"),
  .indata_reg_b("CLOCK0"),.byteena_reg_b("CLOCK0"),
  .outdata_reg_a("UNREGISTERED"),.outdata_reg_b("UNREGISTERED"),
  .read_during_write_mode_mixed_ports("DONT_CARE"),
  .read_during_write_mode_port_a("NEW_DATA_NO_NBE_READ")) cell_ram(
  .clock0(clk),.address_a(port_a),.address_b(src[8:1]),
  .data_a({data_in,data_in}),.byteena_a({dest[0],!dest[0]}),.wren_a(do_write),
  .data_b(16'd0),.byteena_b(1'b1),.wren_b(1'b0),.rden_a(1'b1),.rden_b(1'b1),
  .q_a(reference_word),.q_b(current_word));
"""+src[b:]
        f.write_text(src,newline="\n")
    if mode in ("mask","m9k"):
        # One forward cursor/length across all four distances. At each cell
        # discard mismatches, then advance only after all survivors were tested.
        s=once(s,"reg [5:0] length,best;","reg [5:0] best;reg [3:0] live;")
        start=s.index(" task finish_lane;");end=s.index(" // Original kind-",start)
        s=s[:start]+""" function automatic [1:0] earliest(input [3:0] bits);
  earliest=bits[0]?0:bits[1]?1:bits[2]?2:3;
 endfunction
 wire [3:0] keep=same_cell?live:live & ~(4'b0001<<lane);
 wire [3:0] higher=keep & (lane==0?4'b1110:lane==1?4'b1100:lane==2?4'b1000:4'b0000);
"""+s[end:]
        s=once(s,"lane<=0;length<=0;best<=0;address<=9'd256;state<=SEARCH;",
               "lane<=0;live<=0;best<=0;address<=9'd256;state<=SEARCH;")
        a=s.index("   SEARCH:");b=s.index("   CHOOSE:",a)
        s=s[:a]+"""   SEARCH:if(live==0)state<=CHOOSE;else state<=CMP_A;
   CMP_A:begin
    live<=keep;
    if(keep==0)state<=CHOOSE;
    else if(higher!=0)begin lane<=earliest(higher);state<=SEARCH;end
    else begin
     best<=best+1'b1;best_lane<=earliest(keep);lane<=earliest(keep);
     address<={1'b1,advanced};
     state<=(best==31 || advanced[7:1]==cells)?CHOOSE:SEARCH;
    end
   end
"""+s[b:]
        s=once(s,"index<=index+best;state<=STEP;","index<=address[7:1];state<=STEP;")
        s=once(s,"lane<=0;length<=0;best<=0;half<=0;state<=index==cells?CHOOSE:SEARCH;",
               """lane<=0;live<={index>=33,index>=4,index>=2,index!=0};
    best<=0;half<=0;state<=index==cells?CHOOSE:SEARCH;""")
    codec.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    p.add_argument("mode",choices=("walk","pair","mask","m9k"));a=p.parse_args();board(a.base,a.out,a.mode)
