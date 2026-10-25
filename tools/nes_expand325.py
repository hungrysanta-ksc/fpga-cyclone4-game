# SPDX-License-Identifier: MIT
"""319 compressed ingress -> single expansion; retain tile double buffering."""
from nes_delta231 import once

def apply(d):
 original_aperture=(d/'nes_bulk_aperture188.sv').read_text()
 p=d/'nes_mux260.sv';s=p.read_text()
 declarations=" wire [15:0] startpos={header[11],header[10]};\n wire [15:0] outlen=header[0]==2?plen:{header[15],header[14]};\n"
 s=once(s,declarations,'')
 s=once(s,' wire mput=state==PUT'," wire [15:0] startpos={header[11],header[10]};\n wire [15:0] outlen=header[0]==2?{header[13],header[12]}:{header[15],header[14]};\n wire mput=state==PUT")
 s=once(s,' wire mput=state==PUT&&owner==MAP&&!prelude_mode;', ''' localparam EXPAND325=57;
 reg [31:0] seed325;reg [11:0] expanded325;reg zero325;
 wire repeat325=data_command278&&header[0]!=2;
 wire [11:0] output325=zero325?12'd2:outlen[11:0];
 wire [1:0] lane325=expanded325[1:0]&(header[0]==8?2'd3:2'd1);
 wire mput=(state==PUT||state==EXPAND325)&&owner==MAP&&!prelude_mode;
 wire [7:0] payload325=state==EXPAND325?seed325[lane325*8+:8]:held;
 wire [15:0] destination325=(header[1]==3?16'h6000:header[1]==4?16'h6200:16'h6500)+{identity[48],15'd0}+startpos;
 wire [15:0] ppu325=startpos>>1;''')
 s=s.replace('12\'d2048:length',"12'd2048:(data_command278?outlen[11:0]:length)")
 s=s.replace('owner==TILE?tdata:held','owner==TILE?tdata:payload325').replace('k==0?tdata:held','k==0?tdata:payload325')
 a=s.index(' reg tap_seen278');b=s.index(' // Original descriptor stays',a)
 s=s[:a]+''' reg tap_seen278,tap_fault278;
 reg [1:0] tap_state278;reg [12:0] tap_pos278;
 reg [7:0] tap_value278;
 assign crc_reset287=state==CHECK;
 wire [11:0] offset325=address-24'h400800;
 wire [15:0] tap_address278=startpos+{4'd0,offset325};
 wire tap_capture278=state==DMA&&data_command278&&!invalidate_banks&&!tap_seen278&&
  !read_n&&write_n&&bus_valid&&address>=24'h400800&&address<24'h401800;
 wire tap_raw278=tap_pos278>=3169;
 wire [12:0] tap_relative278=tap_pos278-13'd3169;
 wire tap_start278=tap_state278==1,tap_byte278=tap_state278==2,tap_idle278=tap_state278==0;
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin tap_seen278<=0;tap_fault278<=0;tap_state278<=0;tap_pos278<=0;tap_value278<=0;end
  else if(rst)begin tap_seen278<=0;tap_state278<=0;end
  else begin
   if(read_n)tap_seen278<=0;
   if(state==CHECK)begin if(!tap_idle278)tap_fault278<=1;tap_seen278<=0;end
   if(tap_capture278)begin
    tap_seen278<=1;
    if(header[1]==5&&!zero325&&(tap_address278<scroll_length||(prelude_raw!=0&&tap_address278>=3169)))begin
     if(!tap_idle278)tap_fault278<=1;
     else begin
      tap_pos278<=tap_address278[12:0];tap_value278<=aperture_data;
      tap_state278<=(tap_address278==0||(tap_address278>=3169&&(tap_address278-3169)%16==0))?1:2;
     end
    end
   end
   case(tap_state278)
    1:if(range_ready)tap_state278<=2;
    2:if(ordinary_hash_ready)tap_state278<=3;
    3:if(range_ready||ordinary_hash_ready)tap_state278<=0;
    default:;
   endcase
  end
 end
'''+s[b:]
 s=once(s,"   8'h60:control=header[0];8'h61:control=header[1];\n   8'h62:control=startpos[7:0];8'h63:control=startpos[15:8];\n   8'h64:control=plen[7:0];8'h65:control=plen[15:8];\n   8'h66:control=active305.span[7:0];8'h67:control=active305.span[15:8];", """   8'h60:control={7'd0,zero325};8'h61:control=header[1];
   8'h62:control=destination325[7:0];8'h63:control=destination325[15:8];
   8'h64:control=chunk_length[7:0];8'h65:control={4'd0,chunk_length[11:8]};
   8'h66:control=ppu325[7:0];8'h67:control=ppu325[15:8];""")
 s=once(s,"   scroll_length<=0;ordinary_reads<=0;tile_proven<=0;", "   scroll_length<=0;ordinary_reads<=0;tile_proven<=0;seed325<=0;expanded325<=0;zero325<=0;")
 s=once(s,"else if(begin_ready)begin at<=0;if(!batch)","else if(begin_ready)begin seed325<=0;expanded325<=0;zero325<=0;at<=0;if(!batch)")
 s=once(s,'      end else begin held<=qdata;state<=PUT;end', '''      end else if(repeat325&&!prelude_mode)begin
       seed325[at[1:0]*8+:8]<=qdata;
       if(at+1==plen)begin
        zero325<=header[0]==5&&header[1]==5&&startpos==21&&outlen==1100&&seed325[7:0]==0&&qdata==0;
        state<=EXPAND325;
       end else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else begin held<=qdata;state<=PUT;end''')
 s=once(s,'     SEAL:begin', '''     EXPAND325:if(put_ready)begin
      if(expanded325+1==output325)state<=SEAL;
      else expanded325<=expanded325+1'b1;
     end
     SEAL:begin''')
 s=s.replace("rs&&!rp&&ap[23:11]==13'h801","rs&&!rp&&ap>=24'h400800&&ap<24'h401800")
 s=s.replace('.begin_valid(owner==TILE?tbeg:mbeg)', '.wide325(owner==MAP&&data_command278),.begin_valid(owner==TILE?tbeg:mbeg)')
 s=s.replace('.begin_valid(k==0?tbeg:mbeg)', '.wide325(k==1&&data_command278),.begin_valid(k==0?tbeg:mbeg)')
 p.write_text(s,newline='\n')
 p=d/'nes_bulk_aperture188.sv'
 # Ordinary commands own the entire aperture; tile/map retain their original
 # ping-pong chunks. Ownership cannot change while any tile chunk is live.
 s=original_aperture
 s=once(s,' input wire clk, reset, active, stop,',' input wire clk, reset, active, stop, input wire wide325,')
 s=s.replace('storage[{writer,count[10:0]}]','storage[wide325?count:{writer,count[10:0]}]')
 s=s.replace('begin_length>2048',"begin_length>(wide325?12'd4095:12'd2048)")
 s=s.replace("address_sync[23:11]==13'h801&&\n                 {1'b0,address_sync[10:0]}<lengths[reader]", "(wide325?(address_sync>=24'h400800&&address_sync<24'h401800):(address_sync[23:11]==13'h801))&&\n                 (wide325?(address_sync-24'h400800):{1'b0,address_sync[10:0]})<lengths[reader]")
 s=s.replace("wire selected=address[23:11]==13'h801;", "wire selected=wide325?(address>=24'h400800&&address<24'h401800):(address[23:11]==13'h801);\n wire [11:0] wide_offset325=address_sync-24'h400800;")
 s=s.replace('storage[{reader,address_sync[10:0]}]','storage[wide325?wide_offset325:{reader,address_sync[10:0]}]')
 p.write_text(s,newline='\n')
