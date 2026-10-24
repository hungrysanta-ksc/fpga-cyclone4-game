# SPDX-License-Identifier: MIT
"""Actual read-owned private receipt jobs; exact token ACK publishes completion."""
from nes_delta231 import once
from nes_execute334 import native as previous_native


def native(d):
    previous_native(d)
    p=d/'nes_refill267.c';s=p.read_text()
    a=s.index('static unsigned crc16(');b=s.index('\n',a)
    s=s[:a]+'''unsigned plan_crc336(const uint8_t *p,unsigned n){
 static const uint16_t table336[16]={0x0000,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,
  0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 unsigned c=65535;
 while(n--){c^=(unsigned)*p++<<8;c=((c<<4)^table336[c>>12])&65535;c=((c<<4)^table336[c>>12])&65535;}
 return c;
}'''+s[b:]
    s=once(s,'unsigned c=crc16(q+3,len);','unsigned c=plan_crc336(q+3,len);')
    p.write_text(s,newline='\n')


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'output wire [7:0] expected_data332,', 'output wire jobs_committed336,output wire [7:0] expected_data332,')
    s=once(s,'reg [11:0] read_count;', '')
    s=once(s,' reg tap_seen278,tap_fault278;', ' reg [11:0] read_count;\n reg tap_seen278,tap_fault278;')
    s=once(s,'  logic [11:0] receipt_first,receipt_end;\n','')
    s=once(s,'reg [1:0] tap_state278;reg [12:0] tap_pos278;','reg [2:0] tap_state278;reg [15:0] tap_pos278;reg read_pending336;')
    s=once(s,'wire tap_capture278=state==DMA&&data_command278', 'wire tap_capture278=state==DMA&&chunk_ready')
    a=s.index(' always @(posedge host_clk or posedge reset)begin\n  if(reset)begin tap_seen278');b=s.index(' // One command handshake;',a)
    s=s[:a]+''' // A job is derived only from a tagged aperture response. Descriptor
 // admission remains in CHECK/DCHECK; no receipt first/end snapshot survives.
 wire map336=header[0]==12||header[0]==14;
 wire [15:0] tail336=tap_pos278-16'd1121;
 reg unit_valid336;reg [11:0] unit336;
 always @*begin
  unit_valid336=0;unit336=0;
  if(map336)begin unit_valid336=tap_pos278[0];unit336=tap_pos278[12:1];end
  else if(header[0]==7)begin
   if(header[1]==0)begin unit_valid336=tap_pos278[3:0]==15;unit336={2'd0,tap_pos278[13:4]};end
   else begin unit_valid336=tap_pos278[4:0]==31;unit336=12'd1024+{5'd0,tap_pos278[11:5]};end
  end else if(header[1]==3)begin unit_valid336=tap_pos278[3:0]==15;unit336=12'd1152+{7'd0,tap_pos278[8:4]};end
  else if(header[1]==5&&tap_pos278>=1121&&tap_pos278<3418)begin
   unit_valid336=(tap_pos278<3169||prelude_raw!=0)&&(tail336[3:0]==15||tap_pos278==3417);
   unit336=12'd1184+{4'd0,tail336[11:4]};
  end
 end
 wire receipt_valid282=tap_state278==4&&unit_valid336;
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin tap_seen278<=0;tap_fault278<=0;tap_state278<=0;tap_pos278<=0;tap_value278<=0;read_pending336<=0;end
  else if(rst)begin tap_seen278<=0;tap_state278<=0;read_pending336<=0;end
  else if(!fault)begin
   if(read_n)tap_seen278<=0;
   if(state==CHECK)begin if(!tap_idle278||read_pending336)tap_fault278<=1;tap_seen278<=0;end
   if(!invalidate_banks&&rs&&!rp&&ap>=24'h400800&&ap<24'h401800)begin
    if(!read_pending336)tap_fault278<=1;
    read_pending336<=0;
   end
   if(tap_capture278)begin
    tap_seen278<=1;
    if(!tap_idle278||read_pending336||offset325!=read_count||read_count>=chunk_length)tap_fault278<=1;
    else begin
     read_pending336<=1;tap_pos278<=tap_address278;tap_value278<=aperture_data;
     if(data_command278&&header[1]==5&&!zero325&&(tap_address278<scroll_length||(prelude_raw!=0&&tap_address278>=3169)))
      tap_state278<=(tap_address278==0||(tap_address278>=3169&&(tap_address278-3169)%16==0))?1:2;
     else tap_state278<=4;
    end
   end
   case(tap_state278)
    1:if(range_ready)tap_state278<=2;
    2:if(ordinary_hash_ready)tap_state278<=3;
    3:if(range_ready||ordinary_hash_ready)tap_state278<=4;
    4:if(!unit_valid336)tap_state278<=0;else if(range_ready)tap_state278<=5;
    5:if(range_ready)tap_state278<=0;
    default:;
   endcase
  end
 end
''' +s[b:]
    s=once(s,'assign ordinary_range=receipt_valid282&&range_ready&&!rst;', 'assign ordinary_range=receipt_valid282&&!map336&&range_ready&&!rst&&!fault;')
    s=once(s,'assign ordinary_first=receipt_first282;assign ordinary_end300=receipt_limit287;', "assign ordinary_first=unit336;assign ordinary_end300=12'd1;")
    s=once(s,'assign range_first=first;assign range_count=count;assign range_valid=state==SEND&&!data_command278&&header[0]!=7&&range_ready&&!rst;', "assign range_first=unit336;assign range_count=12'd1;assign range_valid=receipt_valid282&&map336&&range_ready&&!rst&&!fault;")
    s=once(s,'wire good_consume=chunk_ready&&', 'wire good_consume=tap_idle278&&!read_pending336&&range_ready&&chunk_ready&&')
    s=once(s,' assign staged=chunk_ready', ' assign jobs_committed336=!chunk_ready&&tap_idle278&&!read_pending336&&!rst&&!fault;\n assign staged=chunk_ready')
    s=once(s,'active305.endpos<=decode_end305;active305.receipt_first<=decoded_first305;active305.receipt_end<=decoded_limit305;', 'active305.endpos<=decode_end305;')
    # No second post-ACK receipt traversal. These states now only retire the
    # already drained private job at the existing exact ordered token ACK.
    s=once(s,'     SEND:if(mready)state<=XWAIT298;', '     SEND:if(tap_idle278&&range_ready)state<=CONSUME;')
    p.write_text(s,newline='\n')

    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,'assign v_all_consumed=1;', '')
    s=once(s,' flow(', ' flow(.jobs_committed336(v_all_consumed),')
    p.write_text(s,newline='\n')

    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'reg [11:0] v_bit_at,v_end283,v_map_end;', 'reg [11:0] v_bit_at,v_map_end;')
    a=s.index(' // Admission computes');b=s.index(' wire crc_covered287=',a)
    s=s[:a]+''' // A single completed unit, qualified by the actual response owner.
 // There is no autonomous descriptor range replay or exclusive end register.
 wire [7:0] v_nextmask=8'h01<<v_bit_at[2:0];
'''+s[b:]
    a=s.index(' task advance_range;');b=s.index(' task advance_check;',a);s=s[:a]+s[b:]
    s=s.replace('v_end283<=0;','')
    a=s.index('      if(rec_i!=0||(map_phase305||cursor!=0)||(v_descriptor287?');b=s.index('\n     end else if(v_finish_valid)',a)
    s=s[:a]+'''      if(rec_i!=0||map_phase305||cursor!=0||v_count!=1||
         (v_map_range?(v_first>=2048||v_first<v_map_end):v_first>=1328))fault<=2;
      else begin v_bit_at<=v_first;v_mapmode<=v_map_range;
       if(v_map_range)v_map_end<=v_first+12'd1;
       state<=V_RREAD;
      end'''+s[b:]
    s=s.replace('else if(v_mapmode)advance_range();','else if(v_mapmode)state<=V_ACTIVE;').replace('V_PWRITE:advance_range();','V_PWRITE:state<=V_ACTIVE;')
    p.write_text(s,newline='\n')
