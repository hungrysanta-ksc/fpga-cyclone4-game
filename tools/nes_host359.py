# SPDX-License-Identifier: MIT
"""Replace host tap continuation FSM with the independent validator's RAM executor; source338 retained."""
from nes_delta231 import once
def apply(d,board=False):
 p=d/'nes_mux260.sv';s=p.read_text();s=once(s,'module nes_output260 #(parameter SHARED=1,parameter [31:0] INITIAL_TOKEN=1)(', 'module nes_output260 #(parameter SHARED=1,parameter [31:0] INITIAL_TOKEN=1)(output wire [33:0] read359,input wire ready359,private359,')
 a=s.index(' reg [2:0] tap_state278');b=s.index(' // One command handshake;',a)
 s=s[:a]+''' wire [11:0] offset325=address-24'h400800;
 wire [15:0] tap_address278=startpos+{4'd0,offset325};
 wire tap_capture278=state==DMA&&chunk_ready&&!invalidate_banks&&!tap_seen278&&
  !read_n&&write_n&&bus_valid&&address>=24'h400800&&address<24'h401800;
 reg read_pending336;
 wire tap_idle278=ready359;
 wire [2:0] tap_state278=private359?3'd5:ready359?3'd0:3'd3;
 wire [7:0] tap_value278=aperture_data;
 wire tap_byte278=read359[33]&&read359[32];
 wire map336=header[0]==12||header[0]==14;
 wire [11:0] unit336=0;
 assign crc_reset287=state==CHECK;
 wire crc359=data_command278&&header[1]==5&&!zero325&&
  (tap_address278<scroll_length||(prelude_raw!=0&&tap_address278>=3169));
 wire start359=tap_address278==0||(tap_address278>=3169&&(tap_address278-3169)%16==0);
 assign read359={tap_capture278&&tap_idle278&&!read_pending336&&offset325==read_count&&read_count<chunk_length&&!rst&&!fault,
  crc359,start359,header[0][3:0],header[1][2:0],tap_address278,aperture_data};
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin tap_seen278<=0;tap_fault278<=0;read_pending336<=0;end
  else if(rst)begin tap_seen278<=0;read_pending336<=0;end
  else if(!fault)begin
   if(read_n)tap_seen278<=0;
   if(state==CHECK)begin if(!tap_idle278||read_pending336)tap_fault278<=1;tap_seen278<=0;end
   if(!invalidate_banks&&rs&&!rp&&ap>=24'h400800&&ap<24'h401800)begin
    if(!read_pending336)tap_fault278<=1;read_pending336<=0;
   end
   if(tap_capture278)begin tap_seen278<=1;
    if(!read359[33])tap_fault278<=1;else read_pending336<=1;
   end
  end
 end
'''+s[b:]
 for x,y in [('assign ordinary_range=receipt_valid282&&!map336&&range_ready&&!rst&&!fault;','assign ordinary_range=0;'),('assign ordinary_byte=metadata313?held:tap_byte278?tap_value278:qdata;','assign ordinary_byte=metadata313?held:qdata;'),('assign ordinary_hash_start=tap_start278&&range_ready&&!rst&&!fault;','assign ordinary_hash_start=0;'),("assign ordinary_hash_kind=tap_raw278?2'd0:2'd1;","assign ordinary_hash_kind=0;"),('assign ordinary_hash_index=tap_relative278[7:4];assign ordinary_hash_byte=tap_byte278&&!rst;','assign ordinary_hash_index=0;assign ordinary_hash_byte=0;'),('assign range_valid=receipt_valid282&&map336&&range_ready&&!rst&&!fault;','assign range_valid=0;')]:s=once(s,x,y)
 p.write_text(s,newline='\n')
 p=d/'nes_validator278.sv';s=p.read_text();s=once(s,'module nes_validator278(', 'module nes_validator278(input wire [33:0] read359,output wire ready359,private359,')
 s=once(s,'input wire h_valid,input wire [7:0] h_data,','input wire legacy_h_valid,input wire [7:0] legacy_h_data,')
 at=s.index(' wire [7:0] crc_byte=')
 s=s[:at]+''' reg job359,byte_pending359,unit_pending359;reg [7:0] byte359;
 wire [3:0] op359=read359[30:27];wire [2:0] section359=read359[26:24];
 wire [15:0] pos359=read359[23:8],tail359=pos359-16'd1121;
 wire map359=op359==12||op359==14;
 reg unit_valid359;reg [11:0] unit359;
 always @*begin
  unit_valid359=0;unit359=0;
  if(map359)begin unit_valid359=pos359[0];unit359=pos359[12:1];end
  else if(op359==7)begin
   if(section359==0)begin unit_valid359=pos359[3:0]==15;unit359={2'd0,pos359[13:4]};end
   else begin unit_valid359=pos359[4:0]==31;unit359=12'd1024+{5'd0,pos359[11:5]};end
  end else if(section359==3)begin unit_valid359=pos359[3:0]==15;unit359=12'd1152+{7'd0,pos359[8:4]};end
  else if(section359==5&&pos359>=1121&&pos359<3418)begin
   unit_valid359=(pos359<3169||v_raw!=0)&&(tail359[3:0]==15||pos359==3417);
   unit359=12'd1184+{4'd0,tail359[11:4]};
  end
 end
 assign ready359=!reset&&!abort_source&&!fault&&!job359&&!private359;
 assign private359=state==V_RREAD||state==V_RWRITE||state==V_PREAD||state==V_PWRITE;
 wire h_valid=legacy_h_valid||(job359&&byte_pending359);
 wire [7:0] h_data=job359?byte359:legacy_h_data;
 wire unit_event359=(read359[33]&&ready359&&!read359[32]&&unit_valid359)||
  (state==V_ACTIVE&&job359&&!byte_pending359&&unit_pending359);
 wire [11:0] unit_first359=job359?v_bit_at:unit359;
 wire unit_map359=job359?v_mapmode:map359;
''' +s[at:]
 s=once(s,'map_phase305<=0;crc_mask287<=0;state<=V_CLEARALL;', 'job359<=0;byte_pending359<=0;unit_pending359<=0;byte359<=0;map_phase305<=0;crc_mask287<=0;state<=V_CLEARALL;')
 s=once(s,'end else if(abort_source)begin if(!fault)fault<=4;active<=0;seal_state<=0;end', 'end else if(abort_source)begin job359<=0;byte_pending359<=0;unit_pending359<=0;if(!fault)fault<=4;active<=0;seal_state<=0;end')
 s=once(s,'if(grant278)begin', '''if(job359&&byte_pending359&&(state==H_BYTES||state==H_SCROLL))byte_pending359<=0;
   if(job359&&!byte_pending359&&(state==H_BYTES||state==H_SCROLL))job359<=0;
   if(read359[33])begin
    if(!ready359||legacy_h_valid||(state!=V_ACTIVE&&state!=H_BYTES&&state!=H_SCROLL))fault<=2;
    else begin
     v_bit_at<=unit359;v_mapmode<=map359;unit_pending359<=unit_valid359;
     if(unit_valid359&&(map359?(unit359>=2048||unit359<v_map_end):unit359>=1328))fault<=2;
     if(map359&&unit_valid359)v_map_end<=unit359+12'd1;
     if(read359[32])begin
      job359<=1;byte_pending359<=1;byte359<=read359[7:0];
      if(read359[31])begin
       if(state!=V_ACTIVE)fault<=7;
       else if(pos359>=3169)begin
        if(map_phase305||cursor!=0||v_raw==0)fault<=7;
        else begin hash_index<=(pos359-3169)>>4;hash_lane<=0;checksum<=16'hffff;state<=H_BYTES;end
       end else if(!map_phase305&&cursor==0&&!scroll_seen)begin h_count<=0;checksum<=16'hffff;digest_ready<=0;state<=H_LENLOREAD;end
       else fault<=7;
      end else if(state!=H_BYTES&&state!=H_SCROLL)fault<=7;
     end else if(state!=V_ACTIVE)fault<=7;
     else if(unit_valid359)state<=V_RREAD;
    end
   end else if(grant278)begin''')
 s=once(s,'V_ACTIVE:begin\n     if(v_begin_valid)', '''V_ACTIVE:begin
     if(job359&&!byte_pending359)begin job359<=0;unit_pending359<=0;if(unit_pending359)state<=V_RREAD;end
     else if(v_begin_valid)''')
 p.write_text(s,newline='\n')
 p=d/'nes_joint257.sv';s=p.read_text();s=once(s,'module nes_joint257(', 'module nes_joint257(input wire [33:0] read359,output wire ready359,private359,')
 s=once(s,'nes_validator278 validator(', 'nes_validator278 validator(.read359(read359),.ready359(ready359),.private359(private359),')
 a=s.index('nes_validator278 validator(');s=s[:a]+s[a:].replace('.h_valid(h_valid),.h_data(h_data)', '.legacy_h_valid(h_valid),.legacy_h_data(h_data)')
 p.write_text(s,newline='\n')
 p=d/'nes_joint266.sv';s=p.read_text();a=s.index('nes_output260 #');s=s[:a]+'wire [33:0] read359;wire ready359,private359;\n '+s[a:]
 s=once(s,'flow(', 'flow(.read359(read359),.ready359(ready359),.private359(private359),');s=once(s,'nes_joint257 core(', 'nes_joint257 core(.read359(read359),.ready359(ready359),.private359(private359),');p.write_text(s,newline='\n')
