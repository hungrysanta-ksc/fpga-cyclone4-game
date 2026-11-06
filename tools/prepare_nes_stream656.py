"""Materialize a 655 walk board with one linear output/recovery controller."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import evidence,digest
from nes_raw506 import once

def board(base,out,mode):
    pins=evidence("search655-verification.json")["modes"]["walk"]
    assert digest(base/"output_files/board.fit.rpt")==pins["fit"]["fit_report"]
    for name,pin in pins["rtl"].items():assert digest(base/name)==pin
    out.mkdir(parents=True,exist_ok=False)
    for name in evidence("trial613-package.json")["inputs"]:
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,path)
    shutil.copyfile(Path(__file__).with_name("nes_stream656.sv"),out/"nes_geometry_sender653.sv")
    f=out/"nes_native_spi165.sv";s=f.read_text()
    s=once(s,"nes_geometry_sender653 codec(",f"nes_geometry_sender653 #(.INGRESS_CRC({int(mode!='stream')})) codec(")
    s=once(s,".cells(cells),",""".cells(cells),
  .cell_write(take_cell || cell_tail),.first_cell(take_cell && cells==0),
  .input_byte(cell_tail?{1'b0,cell_upper}:record_data[7:0]),""")
    if mode=="owner":
        # One output cursor for ordinary, compression and legacy fallback.
        # Revisit the final bytes for CRC in every case, including non-map.
        codec=out/"nes_geometry_sender653.sv";v=codec.read_text()
        v=once(v,"input wire cell_write,first_cell,", "input wire [7:0] outpos,output wire rewind,input wire cell_write,first_cell,")
        v=once(v,"reg [7:0] outpos,first;","reg [7:0] first;")
        v=once(v,"assign group_start=base+{address[7:3],2'b00};","assign group_start=base;")
        v=once(v," assign write_address=outpos;"," assign write_address=outpos;\n assign rewind=run && !wait_read && state==CHOOSE && fallback;")
        v=once(v,"   if(write_en)outpos<=outpos+1'b1;\n","")
        v=once(v,"outpos<=prefix;matched<=0;","matched<=0;")
        v=once(v,"if(INGRESS_CRC)state<=HEADER;","if(cells==0)begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end\n     else if(INGRESS_CRC)state<=HEADER;")
        v=once(v,"if(advanced=={cells,1'b0})state<=FINISHED;","if(advanced=={cells,1'b0})begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end")
        codec.write_text(v,newline="\n")
        s=once(s,"wire transform=sealed && cells!=0;","wire transform=sealed;wire rewind;")
        s=once(s,"wire compact=transform && done652 && packed652;","wire compact=transform && cells!=0 && done652 && packed652;")
        s=once(s,"wire [8:0] public_size=compact?len652:used;","wire [8:0] public_size=used;")
        s=once(s,"wire [15:0] public_crc=compact?crc652:block_crc;","wire [15:0] public_crc=crc652;")
        s=once(s,"crc16(encoding?block_crc:crc_arg,encoding?pack_byte:crc_byte)","crc16(crc_arg,crc_byte)")
        s=once(s,".cell_write(take_cell", ".outpos(used[7:0]),.rewind(rewind),.cell_write(take_cell")
        s=once(s,"else if(write_serial)buffer[{1'b0,used[7:0]}]<=pack_byte;\n   else if(active && wen652)buffer[{1'b0,wa652}]<=wd652;",
                 "else if(write_serial || (active && wen652))buffer[{1'b0,used[7:0]}]<=write_serial?pack_byte:wd652;")
        s=once(s,"if(byte_valid)begin used<=used+1'b1;block_crc<=folded;end","if(byte_valid)used<=used+1'b1;")
        s=once(s,"if(raw_emit)begin\n","if(raw_emit)begin\n    cell_base<=cell_base+13'd4;\n")
        s=once(s,"   if(encoding)begin","   if(active && wen652)used<=used+1'b1;\n   if(rewind)used<=has_header?9'd12:9'd0;\n   if(encoding)begin")
        s=s.replace("token,block_crc;","token;").replace("block_crc<=16'hffff;","")
    if mode=="fused":
        # Keep the original CDC control and capture register at the destination.
        # Once accepted, that host-clock word can become the serializer; a new
        # capture must wait until the SPI endpoint is ready to own another word.
        mb=out/"nes_native_mailbox165.sv";v=mb.read_text()
        v=once(v,"parameter WIDTH=96","parameter WIDTH=96,parameter SHARE_WORD=0")
        v=once(v,"output wire [WIDTH-1:0] dst_data","output wire [WIDTH-1:0] dst_data,\n input wire word_write,input wire [WIDTH-1:0] word_next")
        v=once(v,"if(!valid&&!capture&&req_sync[1]!=acknowledge)","if(!valid&&!capture&&req_sync[1]!=acknowledge && (!SHARE_WORD || dst_ready))")
        v=once(v,"if(capture)begin received<=held;valid<=1;capture<=0;end",
               "if(capture)begin received<=held;valid<=1;capture<=0;end\n    else if(SHARE_WORD && word_write)received<=word_next;")
        mb.write_text(v,newline="\n")
        top=out/"nes_live_joint.sv";v=top.read_text()
        v=once(v,"nes_native_mailbox165 #(.WIDTH(96)) native_records(",
             "wire word_write656;wire [95:0] word_next656;\nnes_native_mailbox165 #(.WIDTH(96),.SHARE_WORD(1)) native_records(.word_write(word_write656),.word_next(word_next656),")
        v=once(v,"nes_native_spi165 native_spi(","nes_native_spi165 native_spi(.word_write(word_write656),.word_next(word_next656),")
        top.write_text(v,newline="\n")
        s=once(s,"output reg fault","output reg fault,output wire word_write,output wire [95:0] word_next")
        s=once(s,"reg [95:0] held;","wire [95:0] held={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};")
        s=once(s," assign packed652=!raw_format;",""" // Store the next serializer value in mailbox bit order. Reading a
 // pending immutable record never overlaps raw replay or a byte shift.
 wire [95:0] ordered_next=encoding ? {held[87:0],8'd0} :
   raw_emit ? {4'h1,group_start[11:0],map_generation,1'b0,group_count,held[59:0]} :
              {36'd0,(addr652[2:1]==0 ? 45'd0 : held[44:0]),cell_word};
 assign word_next={ordered_next[95:93],ordered_next[79:64],ordered_next[92:80],ordered_next[63:0]};
 assign word_write=!reset && (encoding || raw_emit || raw_load);
 assign packed652=!raw_format;""")
        s=once(s,"encoding<=0;held<=0;position<=0;","encoding<=0;position<=0;")
        s=once(s,"     held<={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};\n","")
        s=once(s,"end else if(raw_load)held[59:0]<={held[44:0],cell_word};\n   else if(raw_emit)begin","end else if(raw_emit)begin")
        s=once(s,"    held<={4'h1,group_start[11:0],map_generation,1'b0,group_count,held[59:0]};\n","")
        s=once(s,"held<={held[87:0],8'd0};position","position")
    if mode=="late":
        # The original destination mailbox holds its bytes until ACK. Consume
        # an ordinary record only on the last serializer edge, and do not
        # allocate another copy. The fallback packer now holds just four cells.
        s=once(s,"reg [95:0] held;","reg [59:0] raw_payload;")
        s=once(s," wire [7:0] pack_byte=held[95:88];",""" reg [7:0] pack_byte;
 wire raw_output=sealed && raw_format;
 wire [15:0] byte_tag=raw_output?{4'h1,group_start[11:0]}:{record_data[95:93],record_data[76:64]};
 wire [15:0] byte_gen=raw_output?map_generation:record_data[92:77];
 always @*case(position)
  0:pack_byte=byte_tag[15:8];1:pack_byte=byte_tag[7:0];
  2:pack_byte=byte_gen[15:8];3:pack_byte=byte_gen[7:0];
  default:if(raw_output)pack_byte=position==4?{1'b0,group_count,raw_payload[59:56]}:raw_payload[55:48];
          else pack_byte=record_data[((3'd3-position[2:0]) & 3'd7)*8+:8];
 endcase""")
        # Move declarations ahead of the byte selector (no implicit nets).
        a=s.index(" wire raw_load,raw_emit,raw_format;");b=s.index(" reg cell_tail",a)
        decl=s[a:b];s=s[:a]+s[b:];s=once(s," reg [7:0] pack_byte;",decl+" reg [7:0] pack_byte;")
        s=once(s,"assign record_ready=!cell_tail&&!reset&&!sealed&&!encoding&&used<=244;",
            """wire accepting=!cell_tail && !reset && !sealed && !encoding && used<=244;
 assign record_ready=map_cell?accepting:(!reset && !sealed && encoding && position==11);""")
        s=once(s,"end else if(record_valid&&record_ready)begin","end else if(record_valid && accepting)begin")
        s=once(s,"encoding<=0;held<=0;position<=0;","encoding<=0;raw_payload<=0;position<=0;")
        s=once(s,"     held<={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};\n","")
        s=once(s,"if(raw_load)held[59:0]<={held[44:0],cell_word};",
            "if(raw_load)raw_payload<={(addr652[2:1]==0?45'd0:raw_payload[44:0]),cell_word};")
        s=once(s,"    held<={4'h1,group_start[11:0],map_generation,1'b0,group_count,held[59:0]};\n","")
        s=once(s,"held<={held[87:0],8'd0};position<=position+1'b1;",
               """if(raw_output && position>=5)raw_payload<={raw_payload[51:0],8'd0};
    position<=position+1'b1;""")
    if mode=="header":
        # The serializer emits the ten compact-header bytes from the FINAL
        # accepted cell's CRC. An aborted or raw frame hashes its actual page.
        codec=out/"nes_geometry_sender653.sv";v=codec.read_text()
        v=once(v,"input wire cell_write,first_cell,", "input wire [7:0] used_bytes,input wire cell_write,first_cell,")
        a=v.index("   HEADER:case");b=v.index("   CHOOSE:",a);v=v[:a]+v[b:]
        v=once(v,"outpos<=prefix;matched<=0;","outpos<=prefix+8'd10;matched<=0;")
        a=v.index("     if(INGRESS_CRC)");b=v.index("    STEP:",a)
        v=v[:a]+"""     if(cells==0)begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end
     else state<=STEP;end
    CRC_SCAN:begin crc<=folded;
     if(advanced==((raw || cells==0)?used_bytes:outpos))state<=FINISHED;
     else fetch({1'b0,advanced},CRC_SCAN);end
"""+v[b:]
        v=once(v,"if(advanced=={cells,1'b0})state<=FINISHED;","if(advanced=={cells,1'b0})begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end")
        codec.write_text(v,newline="\n")
        s=once(s,"wire transform=sealed && cells!=0;","reg emitting_header;wire transform=sealed && !emitting_header;")
        s=once(s,"wire available=sealed && !active;","wire available=sealed && !emitting_header && !active;")
        s=once(s,"wire compact=transform && done652 && packed652;","wire compact=transform && cells!=0 && done652 && packed652;")
        s=once(s,"wire [15:0] public_crc=compact?crc652:block_crc;","wire [15:0] public_crc=crc652;")
        s=once(s,"crc16(encoding?block_crc:crc_arg,encoding?pack_byte:crc_byte)","crc16(crc_arg,crc_byte)")
        s=once(s,".cell_write(take_cell", ".used_bytes(used[7:0]),.cell_write(take_cell")
        s=once(s,"used<=0;has_header<=0;cell_tail","emitting_header<=0;used<=0;has_header<=0;cell_tail")
        s=once(s,"cells<=cells+1'b1;if(cell_last)sealed<=1;", """cells<=cells+1'b1;
    if(cell_last)begin
     sealed<=1;emitting_header<=1;encoding<=1;position<=0;total<=6;terminal<=0;
     held<={16'hffff,map_generation,16'd0,3'd0,cell_base,9'd0,cells+7'd1,folded};
    end""")
        s=once(s,"if(byte_valid)begin used<=used+1'b1;block_crc<=folded;end","if(byte_valid)used<=used+1'b1;")
        s=once(s,"if(position==11)begin encoding<=0;if(used+1>244 || terminal)sealed<=1;end","""if(position==11)begin
     encoding<=0;
     if(emitting_header)begin emitting_header<=0;used<=has_header?9'd12:9'd0;end
     else if(used+1>244 || terminal)sealed<=1;
    end""")
        s=s.replace("token,block_crc;","token;").replace("block_crc<=16'hffff;","")
    f.write_text(s,newline="\n")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("base","out"):p.add_argument(k,type=Path)
    p.add_argument("mode",choices=("stream","ingress","owner","fused","late","header"))
    a=p.parse_args();board(a.base,a.out,a.mode)
