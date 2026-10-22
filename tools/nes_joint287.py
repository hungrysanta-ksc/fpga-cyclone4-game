# SPDX-License-Identifier: MIT
"""Single post-ACK receipt walk; validator owns provisional CRC coverage."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'module nes_output260', 'module nes_output260')
    s=once(s,'output wire grant278,','output wire crc_reset287,\noutput wire grant278,')
    s=once(s,' reg ordinary_mode;reg [11:0] opos,oend;', ' reg ordinary_mode;reg [8:0] opos,oend;')
    s=once(s,' reg [15:0] tap_crc_mask278;', ' assign crc_reset287=state==CHECK;')
    s=s.replace('tap_crc_mask278<=0;','').replace('   if(crc_done278)tap_crc_mask278[crc_index278]<=1;\n','')
    a=s.index(' // One descriptor is held');b=s.index(' wire manifest_byte282=',a)
    s=s[:a]+''' // Original descriptor stays held through the complete independent RAM walk.
 wire [16:0] descriptor_end287={1'b0,startpos}+{1'b0,outlen};
 reg [11:0] receipt_first282,receipt_count282;reg receipt_valid282;
 reg [11:0] receipt_limit287;
 always @*begin
  receipt_first282=0;receipt_count282=0;receipt_limit287=0;receipt_valid282=0;
  if(state==OTILE||state==OSELECT)begin
   if(header[0]==7)begin
    receipt_first282=(header[1]==1?12'd1024:0)+(startpos>>(header[1]==1?5:4));
    receipt_limit287=(header[1]==1?12'd1024:0)+(descriptor_end287>>(header[1]==1?5:4));
   end else if(header[1]==3)begin
    receipt_first282=1152+(startpos>>4);receipt_limit287=1152+(descriptor_end287>>4);
   end else if(header[1]==5&&descriptor_end287>1121)begin
    receipt_first282=startpos<1121?12'd1184:startpos<3169?12'd1184+((startpos-16'd1121)>>4):12'd1312+((startpos-16'd3169)>>4);
    receipt_limit287=descriptor_end287<=3169?12'd1184+((descriptor_end287-17'd1121)>>4):
       prelude_raw==0?12'd1312:12'd1312+((descriptor_end287-17'd3169+17'd15)>>4);
    if(receipt_first282>receipt_limit287)receipt_first282=receipt_limit287;
   end
   receipt_count282=receipt_limit287-receipt_first282;
   receipt_valid282=receipt_count282!=0;
  end
 end
''' +s[b:]
    s=once(s,'ordinary_mode<=1;opos<=startpos[11:0];oend<=startpos[11:0]+outlen[11:0];','ordinary_mode<=1;')
    a=s.index('       else begin opos<=(header[1]==1?');b=s.index('\n      end else if(header[0]==15)',a)
    s=s[:a]+'       else begin if(pattern278!=token)failed<=1;else state<=OTILE;end'+s[b:]
    s=once(s,'       state<=OSELECT;', '''       if(header[1]==5&&descriptor_end287>1121&&
          ((startpos>1121&&startpos<3169&&(startpos-16'd1121)%16!=0)||
           (descriptor_end287<3169&&(descriptor_end287-17'd1121)%16!=0)))failed<=1;
       else state<=OSELECT;''')
    a=s.index('     OTILE:if(range_ready)begin');b=s.index('     ORLE:if(range_ready)',a)
    s=s[:a]+'''     OTILE,OSELECT:if(range_ready)state<=ORET;
'''+s[b:]
    assert 'tap_crc_mask278' not in s and 'receipt_end282' not in s
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,' input wire clk,reset,abort_source,',' input wire crc_reset287,v_descriptor287,\n input wire clk,reset,abort_source,')
    s=once(s,' reg active,initialized,', ' reg [15:0] crc_mask287;\n reg active,initialized,')
    s=once(s,' wire [12:0] domain_end283=v_map_range?13\'d2048:', " wire [12:0] domain_end283=v_map_range?13'd2048:(v_descriptor287&&v_first>=1184)?13'd1328:")
    s=once(s,' wire [7:0] v_nextmask=first_mask283&last_mask283;', ''' wire [7:0] v_nextmask=first_mask283&last_mask283;
 wire crc_covered287=v_mapmode||v_bit_at<1312||
   (((v_bit_at[3]?crc_mask287[15:8]:crc_mask287[7:0])&v_mask)==v_mask);''')
    s=once(s,'v_we=state==V_RWRITE&&(ram_q&v_mask)==0;', 'v_we=state==V_RWRITE&&(ram_q&v_mask)==0&&crc_covered287;')
    s=once(s,'   state<=V_CLEARALL;', '   crc_mask287<=0;state<=V_CLEARALL;')
    s=once(s,'  else if(!fault)begin','  else if(!fault)begin\n   if(crc_reset287)crc_mask287<=0;else if(state==H_WRITEHI)crc_mask287[hash_index]<=1;')
    s=once(s,'(!v_map_range&&v_first>=1312&&v_count!=1)', '(!v_descriptor287&&!v_map_range&&v_first>=1312&&v_count!=1)')
    s=once(s,'V_RWRITE:if(v_q&v_mask)fault<=2;', 'V_RWRITE:if(!crc_covered287)fault<=7;else if(v_q&v_mask)fault<=2;')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text();s=once(s,'module nes_joint257(', 'module nes_joint257(input wire crc_reset287,v_descriptor287,')
    s=once(s,'nes_validator278 validator(', 'nes_validator278 validator(.crc_reset287(crc_reset287),.v_descriptor287(v_descriptor287),')
    p.write_text(s,encoding='utf-8',newline='\n')
    # The same generated boundary is named joint266 in simulation and board.
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' nes_output260 #', ' wire crc_reset287;\n nes_output260 #')
    s=once(s,' flow(.manifest_at282', ' flow(.crc_reset287(crc_reset287),.manifest_at282')
    s=once(s,'nes_joint257 core(', 'nes_joint257 core(.crc_reset287(crc_reset287),.v_descriptor287(v_range_valid),')
    p.write_text(s,encoding='utf-8',newline='\n')
