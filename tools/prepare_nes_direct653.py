"""Receive map cells directly in the source SPI M9K, keeping the existing ARM decoder."""
import argparse
from pathlib import Path
import shutil
from check_nes_fault641 import digest,evidence
from nes_raw506 import once


def prepare(base,out):
    pins=evidence("sender652-verification.json")
    assert digest(base/"nes_native_spi165.sv")==pins["candidate_fit"]["spi"]
    out.mkdir(parents=True,exist_ok=False)
    for name in evidence("trial613-package.json")["inputs"]:
        target=out/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/name,target)
    f=out/"nes_native_export203.sv";s=f.read_text()
    start=s.index("    else if(query_kind==0&&!map_repeat)")
    end=s.index("    else if(query_kind==1",start)
    s=s[:start]+"""    else if(query_kind==0)
     // Private mailbox cell. Bit 63 marks the actual last cell of the map.
     tx_data={3'd0,generation,pack_start,(query_index==limit),48'd0,held_data[14:0]};
"""+s[end:]
    s=once(s,"    else if(query_kind==0 && map_repeat)\n     tx_data={3'd6,generation,5'b10000,count_minus_one,48'd0,held_data[15:0]};\n","")
    start=s.index("     end else if(query_kind==0)begin")
    end=s.index("     end else if(query_kind==4)begin",start)
    s=s[:start]+"""     end else if(query_kind==0)begin
      if(data[63:15]!=0)fail(3);
      else begin held_data<=data;pack_count<=1;query_index<=query_index+1'b1;state<=VALUE;end
"""+s[end:]
    f.write_text(s,newline="\n")
    f=out/"nes_native_spi165.sv";s=f.read_text()
    s=once(s," assign record_ready="," reg cell_tail,cell_last;reg [6:0] cell_upper,cells;reg [12:0] cell_base;\n wire map_cell=record_data[95:93]==0;\n assign record_ready=!cell_tail&&")
    s=once(s," reg [2:0] blocks_left;reg has_header;"," reg has_header;")
    s=once(s,"sealed && blocks_left!=0","sealed && cells!=0")
    start=s.index(" nes_geometry_sender652 codec")
    end=s.index(" reg [7:0] shift",start)
    s=s[:start]+""" wire take_cell=record_ready && record_valid && map_cell;
 wire [15:0] crc_arg;wire [7:0] crc_byte;wire [15:0] wire_crc653;
 wire [15:0] folded=crc16(encoding?block_crc:crc_arg,encoding?pack_byte:crc_byte);
 nes_geometry_sender653 codec(.clk(clk),.reset(reset),.run(transform),.cells(cells),
  .base(cell_base),.generation(held[92:77]),.has_header(has_header),.q(read_byte),
  .address(addr652),.write_en(wen652),.write_address(wa652),.write_data(wd652),
  .done(done652),.size(len652),.crc(wire_crc653),.crc_data(crc_byte),
  .crc_arg(crc_arg),.folded(folded));
 assign packed652=1'b1;
 assign crc652=wire_crc653;
 always @(posedge clk)begin
  read_byte<=buffer[active?addr652:{1'b0,compact,spi_index}];
  if(!reset)begin
   if(take_cell || cell_tail)buffer[{2'b10,cells,cell_tail}]<=cell_tail?{1'b0,cell_upper}:record_data[7:0];
   else if(encoding)buffer[{2'b00,used[7:0]}]<=pack_byte;
   else if(active && wen652)buffer[wa652]<=wd652;
  end
 end
"""+s[end:]
    s=once(s,"used<=0;blocks_left<=0;has_header<=0;","used<=0;has_header<=0;cell_tail<=0;cell_last<=0;cells<=0;cell_upper<=0;cell_base<=0;")
    s=once(s,"   if(record_valid&&record_ready)begin","""   if(take_cell)begin
    cell_upper<=record_data[14:8];cell_tail<=1;
    if(!cells)cell_base<=record_data[76:64];
    held[92:77]<=record_data[92:77];
    cell_last<=record_data[63] || cells==(has_header?79:83);
   end else if(cell_tail)begin
    cell_tail<=0;cells<=cells+1'b1;if(cell_last)sealed<=1;
   end else if(record_valid&&record_ready)begin
    // ABORT may arrive between cells and the map seal. Drop tentative
    // cells so the ordinary E002 record owns this token on the wire.
    if(record_data[95:93]==7 && record_data[76:64]==2)cells<=0;""")
    s=s.replace("      if(record_data[95:93]==7 && record_data[76:64]==0)blocks_left<=7;\n","")
    s=once(s,"block_crc<=crc16(block_crc,pack_byte);","block_crc<=folded;")
    s=once(s,"if(blocks_left!=0)blocks_left<=blocks_left-1'b1;","cells<=0;has_header<=0;")
    f.write_text(s,newline="\n")
    shutil.copyfile(Path(__file__).with_name("nes_geometry_sender653.sv"),out/"nes_geometry_sender653.sv")
    f=out/"board.qsf";f.write_text(once(f.read_text(),"nes_geometry_sender652.sv","nes_geometry_sender653.sv"),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();prepare(a.base,a.out)
