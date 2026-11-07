"""Build 652 from the measured grant binary and the physical MMC643 board."""
import argparse
import re
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def arm(base, out):
    assert digest(base/"src/obj-nes-100/firmware.stm")==evidence("end651-verification.json")["phases"]["1"]["grant"]["firmware"]
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log","base-*","*.json"))
    path=out/"src/crc32.c"
    code=path.read_text()
    start=code.index("static const uint32_t crc32_table")
    end=code.index("};",start)+2
    values=[int(v,16) for v in re.findall(r"0x([0-9a-fA-F]+)",code[start:end])]
    assert len(values)==256
    lo,hi=values[:16],values[::16]
    assert all(lo[i&15]^hi[i>>4]==v for i,v in enumerate(values))
    def table(name,values):
        return "static const uint32_t "+name+"[16] = {\n"+",\n".join("  "+", ".join(f"0x{x:08x}" for x in values[i:i+4]) for i in range(0,16,4))+"\n};"
    code=code[:start]+table("crc32_low",lo)+"\n"+table("crc32_high",hi)+code[end:]
    path.write_text(once(code,"crc32_table[tbl_idx]","crc32_low[tbl_idx & 15] ^ crc32_high[tbl_idx >> 4]"),newline="\n")


def board(base,out):
    assert digest(base/"output_files/board.sof")==evidence("reject643-package.json")["board"]["SHA"]["board.sof"]
    names=evidence("trial613-package.json")["inputs"]
    out.mkdir(parents=True,exist_ok=False)
    for name in names:
        target=out/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/name,target)
    spi=out/"nes_native_spi165.sv"
    s=spi.read_text()
    assert digest(spi)==names["nes_native_spi165.sv"]
    s=once(s,"buffer[0:255]","buffer[0:1023]")
    s=once(s," always @(posedge clk)read_byte<=buffer[byte_count-9'd1];", """
 reg [2:0] blocks_left;reg has_header;
 wire transform=sealed && blocks_left!=0;
 wire done652,packed652,wen652;wire [9:0] addr652,wa652;
 wire [7:0] wd652;wire [8:0] len652;wire [15:0] crc652;
 wire active=transform && !done652;
 wire available=sealed && !active;
 wire compact=transform && done652 && packed652;
 wire [8:0] public_size=compact?len652:used;
 wire [15:0] public_crc=compact?crc652:block_crc;
 wire [7:0] spi_index=byte_count[7:0]-1'b1;
 nes_geometry_sender652 codec(.clk(clk),.reset(reset),.run(transform),.raw_size(used),
  .has_header(has_header),.q(read_byte),.address(addr652),.write_en(wen652),
  .write_address(wa652),.write_data(wd652),.done(done652),.packed_ok(packed652),
  .size(len652),.wire_crc(crc652));
 always @(posedge clk)begin
  read_byte<=buffer[active?addr652:{1'b0,compact,spi_index}];
  if(!reset && (encoding || (active && wen652)))
   buffer[encoding?{2'b0,used[7:0]}:wa652]<=encoding?pack_byte:wd652;
 end
""")
    s=once(s,"buffer[used]<=pack_byte;","")
    s=once(s,"used<=0;token<=0;","used<=0;blocks_left<=0;has_header<=0;token<=0;")
    s=once(s,"if(record_valid&&record_ready)begin held<=record_data;", """if(record_valid&&record_ready)begin
     if(used==0)begin
      has_header<=record_data[95:93]==7 && record_data[76:64]==0;
      if(record_data[95:93]==7 && record_data[76:64]==0)blocks_left<=7;
     end
     held<=record_data;""")
    s=once(s,"!ack_valid,sealed","!ack_valid,available")
    s=s.replace("7'd0,used[8]","7'd0,public_size[8]").replace("),used[7:0]);","),public_size[7:0]);").replace("token,7'd0,used,status_crc","token,7'd0,public_size,status_crc")
    s=s.replace("byte_count<=used)","byte_count<=public_size)").replace("byte_count==used+","byte_count==public_size+").replace("reply=block_crc[","reply=public_crc[")
    s=once(s,"if(!sealed||!read_seen","if(!available||!read_seen")
    s=once(s,"else begin sealed<=0;read_seen<=0;","else begin if(blocks_left!=0)blocks_left<=blocks_left-1'b1;sealed<=0;read_seen<=0;")
    s=once(s,"reading<=sealed;","reading<=available;")
    spi.write_text(s,newline="\n")
    shutil.copyfile(Path(__file__).with_name("nes_geometry_sender652.sv"),out/"nes_geometry_sender652.sv")
    with (out/"board.qsf").open("a",newline="\n") as f:f.write("\nset_global_assignment -name SYSTEMVERILOG_FILE nes_geometry_sender652.sv\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path);p.add_argument("out",type=Path)
    p.add_argument("--board",action="store_true");a=p.parse_args();(board if a.board else arm)(a.source,a.out)
