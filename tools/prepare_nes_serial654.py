"""Replace the 653 fallback writer with the ordinary serializer and one output page."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once


def prepare(base,out):
    signatures=evidence("direct653-verification.json")["RTL"]
    for name,pin in signatures.items():assert digest(base/name)==pin
    out.mkdir(parents=True,exist_ok=False)
    for name in evidence("trial613-package.json")["inputs"]:
        dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,dst)
    f=out/"nes_geometry_sender653.sv";s=(base/f.name).read_text()
    s=once(s,"output reg [9:0] address","""input wire serial_busy,output wire raw_load,raw_emit,output wire [14:0] cell_word,
 output wire [12:0] group_start,output reg [2:0] group_count,output reg raw,
 output reg [8:0] address""")
    s=s.replace("output reg [9:0] write_address","output reg [7:0] write_address").replace("input [9:0] a","input [8:0] a")
    s=s.replace("{2'b10,","{1'b1,").replace("get(10'd512","get(9'd256").replace("{2'b01,meta+8'd1}","{1'b0,meta+8'd1}").replace("get(10'd256,FOLD)","get(9'd0,FOLD)")
    s=once(s,"write_address<={2'b01,a}","write_address<=a")
    s=once(s,"reg half,matched,raw;","reg half,matched;")
    s=once(s,"RAW_GET=14,RAW_BIT=15,FINISHED=16","RAW_LOW=14,RAW_HIGH=15,RAW_EMIT=16,RAW_WAIT=17,FINISHED=18")
    a=s.index(" reg [1:0] slot;");b=s.index(" always @(posedge clk)",a)
    s=s[:a]+""" assign raw_load=run && state==RAW_HIGH;
 assign raw_emit=run && state==RAW_EMIT;
 assign cell_word={q[6:0],first};
 assign group_start=base+index-group_count;
"""+s[b:]
    s=once(s,"if(index==cells)begin meta<=0;state<=HEADER;","if(index==cells)begin meta<=prefix;state<=HEADER;")
    s=once(s,"if(!matched)begin raw<=1;outpos<=prefix;index<=0;end","if(!matched)begin raw<=1;index<=0;state<=RAW_HEAD;end")
    a=s.index("   HEADER:");b=s.index("     case(meta-prefix)",a)
    s=s[:a]+"   HEADER:begin\n"+s[b:]
    a=s.index("   PREFIX:");b=s.index("   FOLD:",a)
    s=s[:a]+"""   RAW_HEAD:begin group_count<=0;get({1'b1,index,1'b0},RAW_LOW);end
   RAW_LOW:begin first<=q;get({1'b1,index,1'b1},RAW_HIGH);end
   RAW_HIGH:begin
    index<=index+1'b1;group_count<=group_count+1'b1;
    if(group_count==3 || index+1'b1==cells)state<=RAW_EMIT;
    else get({1'b1,index+7'd1,1'b0},RAW_LOW);
   end
   RAW_EMIT:state<=RAW_WAIT;
   RAW_WAIT:if(!serial_busy)state<=index==cells?FINISHED:RAW_HEAD;
"""+s[b:]
    f.write_text(s,newline="\n")
    f=out/"nes_native_spi165.sv";s=f.read_text().replace("buffer[0:1023]","buffer[0:511]")
    a=s.index(" wire [15:0] tag=");b=s.index(" reg cell_tail",a)
    s=s[:a]+""" reg terminal; reg [15:0] map_generation;
 wire [7:0] pack_byte=held[95:88];
 wire byte_valid=position<4 || position>=total;
 wire write_serial=encoding && byte_valid;
 wire raw_load,raw_emit,raw_format;
 wire [14:0] cell_word;wire [12:0] group_start;wire [2:0] group_count;
"""+s[b:]
    s=s.replace("wire [9:0] addr652,wa652;","wire [8:0] addr652;wire [7:0] wa652;")
    s=s.replace(".generation(held[92:77])",".generation(map_generation)").replace(".crc_arg(crc_arg),.folded(folded)", """.crc_arg(crc_arg),.folded(folded),.serial_busy(encoding),.raw_load(raw_load),
  .raw_emit(raw_emit),.raw(raw_format),.cell_word(cell_word),.group_count(group_count),.group_start(group_start)""")
    s=once(s,"assign packed652=1'b1;","assign packed652=!raw_format;")
    s=s.replace("{1'b0,compact,spi_index}","{1'b0,spi_index}").replace("{2'b10,cells,cell_tail}","{1'b1,cells,cell_tail}")
    s=s.replace("else if(encoding)buffer[{2'b00,used[7:0]}]","else if(write_serial)buffer[{1'b0,used[7:0]}]").replace("buffer[wa652]","buffer[{1'b0,wa652}]")
    s=once(s,"cell_base<=0;token","cell_base<=0;map_generation<=0;terminal<=0;token")
    s=once(s,"held[92:77]<=record_data[92:77];","map_generation<=record_data[92:77];")
    a=s.index("     held<=record_data;");b=s.index("   if(!ss[1]",a)
    s=s[:a]+"""     terminal<=record_data[95:93]==7 && record_data[76:64]!=0 && record_data[76:64]<13'h800;
     held<={record_data[95:93],record_data[76:64],record_data[92:77],record_data[63:0]};
     position<=0;total<=12-width(record_data[95:93]);encoding<=1;
   end else if(raw_load)held[59:0]<={held[44:0],cell_word};
   else if(raw_emit)begin
    held<={4'h1,group_start[11:0],map_generation,1'b0,group_count,held[59:0]};
    position<=0;total<=4;terminal<=0;encoding<=1;
   end
   if(encoding)begin
    held<={held[87:0],8'd0};position<=position+1'b1;
    if(byte_valid)begin used<=used+1'b1;block_crc<=folded;end
    if(position==11)begin encoding<=0;if(used+1>244 || terminal)sealed<=1;end
   end
"""+s[b:]
    # A request CRC and the actual response CRC advance on the same sampled bit.
    a=s.index(" function automatic [7:0] crc8");b=s.index(" reg terminal",a)
    s=s[:a]+""" function automatic [7:0] step8(input [7:0] c,input bit_in);
  step8={c[6:0],1'b0} ^ ((c[7]^bit_in)?8'h07:8'h00);
 endfunction
"""+s[b:]
    s=s.replace("shift,command,arg,arg_not,received_crc,tail,request_crc","shift,command,request_crc").replace("reg [23:0] offset;reg reading;reg [55:0] snapshot","reg [15:0] offset;reg reading,arg,bad;reg [47:0] snapshot")
    a=s.index("  status_crc=crc8");b=s.index("  reply=0;",a);s=s[:a]+s[b:]
    a=s.index("  end else case(byte_count)");b=s.index("\n end",a)
    s=s[:a]+"""  end else reply=byte_count==7?status_crc:snapshot[47:40];"""+s[b:]
    s=s.replace("arg_not<=0;received_crc<=0;tail<=0;","bad<=0;status_crc<=0;")
    s=once(s,"request_crc<=0;command<=0;miso_hold<=0;","request_crc<=0;status_crc<=0;bad<=0;command<=0;miso_hold<=0;")
    s=once(s,"received_crc!=request_crc||tail!=8'ha5||arg_not!=~arg","bad")
    s=s.replace("offset!={8'd0,token}","offset!=token").replace("offset[23:16]!=0||arg>1||ack_valid","ack_valid").replace("ack_accept<=arg[0]","ack_accept<=arg")
    s=once(s,"    if(bit_count==7)begin","""    if(byte_count<6)request_crc<=step8(request_crc,mosi[1]);
    if(byte_count>=1 && byte_count<=6)status_crc<=step8(status_crc,miso_hold);
    if(bit_count==7)begin""")
    s=once(s,"if(byte_count<6)request_crc<=crc8(request_crc,incoming);","if(byte_count>=1 && byte_count<=6)snapshot<={snapshot[39:0],8'd0};")
    s=s.replace("token,7'd0,public_size,status_crc","token,7'd0,public_size")
    s=once(s,"1:offset[23:16]<=incoming;","1:if(incoming!=0)bad<=1;")
    s=once(s,"4:arg<=incoming;5:arg_not<=incoming;6:received_crc<=incoming;7:tail<=incoming;","""4:begin arg<=incoming[0];if(|incoming[7:1])bad<=1;end
      5:if(incoming!=~{7'd0,arg})bad<=1;
      6:if(incoming!=request_crc)bad<=1;
      7:if(incoming!=8'ha5)bad<=1;""")
    f.write_text(s,newline="\n")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();prepare(a.base,a.out)
