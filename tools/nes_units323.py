# SPDX-License-Identifier: MIT
"""319 replacement-only domain coordinates; actual M4 serializer and host RTL."""
from nes_delta231 import once
from nes_metadata317 import native as previous

def native(d):
    previous(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned send(unsigned n){return send317(n,wire259,0);}',r'''
static unsigned boundary323(unsigned start){return start<1121?1121:start<3169?3169:3418;}
static unsigned send(unsigned n){
 unsigned op=wire259[1];
 if(op==2||op==4||op==5||op==7||op==8){
  unsigned domain=wire259[2],first=u16(wire259+11),span=op==2?n-16:u16(wire259+15),end=first+span,shift=0,base=0;
  if(op==7){if(domain>1)return fail(24);shift=domain?5:4;}
  else if(domain==3)shift=4;
  else if(domain==5){
   if(end>boundary323(first))return fail(24);
   if(first>=3169){domain=7;base=3169;shift=4;}
   else if(first>=1121){domain=6;base=1121;shift=4;}
  }else if(domain!=4)return fail(24);
  if((first-base)&((1u<<shift)-1))return fail(24);
  if((span&((1u<<shift)-1))&&!(domain==7&&end==3418))return fail(24);
  wire259[2]=domain;w16(wire259+11,(first-base)>>shift);
  w16(wire259+15,(span+((1u<<shift)-1))>>shift);
 }
 return send317(n,wire259,0);
}''')
    a=s.index('static unsigned part274(');b=s.index('static unsigned parts274(',a)
    s=s[:a]+'''static unsigned part274(const uint8_t *p,unsigned offset,const uint8_t *data,unsigned size,unsigned dry){
 if(dry)return 1;
 unsigned at=0;
 while(at<size){
  unsigned take=size-at;
  if(p[0]==2&&p[1]==5&&offset+at+take>boundary323(offset+at))take=boundary323(offset+at)-offset-at;
  for(unsigned i=0;i<16;i++)wire259[i+1]=p[i];
  w16(wire259+11,offset+at);w16(wire259+13,take);
  for(unsigned i=0;i<take;i++)wire259[17+i]=data[at+i];
  if(!send(16+take))return 0;
  at+=take;
 }
 return 1;
}
'''+s[b:]
    s=once(s,'  for(unsigned i=0;i<n;i++)wire259[i+1]=p[i];\n  if(p[0]==7)', '''  if(p[0]==4||p[0]==5||p[0]==8){
   unsigned first=u16(p+10),left=u16(p+14),at=0,period=p[0]==8?4:2;
   while(left){
    unsigned take=left;
    if(p[1]==5&&first+take>boundary323(first))take=boundary323(first)-first;
    for(unsigned i=0;i<16;i++)wire259[i+1]=p[i];
    w16(wire259+11,first);w16(wire259+15,take);
    for(unsigned i=0;i<period;i++)wire259[17+i]=p[16+((at+i)%period)];
    if(!send(16+period))return 0;
    first+=take;at+=take;left-=take;
   }
   return 1;
  }
  for(unsigned i=0;i<n;i++)wire259[i+1]=p[i];
  if(p[0]==7)''')
    p.write_text(s,newline='\n')

def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    a=s.index(' assign header[0]=');b=s.index(' assign header[16]=',a)
    s=s[:a]+''' wire unit323=active305.op==2||active305.op==4||active305.op==5||active305.op==7||active305.op==8;
 wire [7:0] domain323=active305.section;
 wire [11:0] uend323={1'b0,active305.start[10:0]}+{1'b0,active305.span[10:0]};
 wire [11:0] umax323=domain323==0?1024:domain323==1?128:domain323==3?32:domain323==4?544:domain323==5?1121:domain323==6?128:domain323==7?16:0;
 wire bad_unit323=|active305.start[15:11]|| |active305.span[15:11]||active305.span==0||uend323>umax323;
 reg [15:0] start323,span323;reg [16:0] end323;
 always @*begin
  start323=active305.start;span323=active305.span;end323={5'd0,uend323};
  if(unit323)case(domain323)
   0,3:begin start323={active305.start[11:0],4'd0};span323={active305.span[11:0],4'd0};end323={1'b0,uend323,4'd0};end
   1:begin start323={active305.start[10:0],5'd0};span323={active305.span[10:0],5'd0};end323={uend323,5'd0};end
   6:begin start323=16'd1121+{active305.start[11:0],4'd0};span323={active305.span[11:0],4'd0};end323=17'd1121+{1'b0,uend323,4'd0};end
   7:begin start323=16'd3169+{active305.start[11:0],4'd0};span323={active305.span[11:0],4'd0}-(uend323==16?16'd7:16'd0);end323=uend323==16?17'd3418:17'd3169+{1'b0,uend323,4'd0};end
   default:begin end
  endcase
 end
 assign header[0]=active305.op;assign header[1]=unit323&&domain323>=6?8'd5:domain323;
 assign header[10]=start323[7:0];assign header[11]=start323[15:8];
 assign header[12]=active305.encoded[7:0];assign header[13]=active305.encoded[15:8];
 assign header[14]=active305.op==2?8'd0:span323[7:0];assign header[15]=active305.op==2?8'd0:span323[15:8];
'''+s[b:]
    s=s.replace(':active305.span[11:0],first=active305.start[12:1],count={1\'b0,active305.span[11:1]}',":span323[11:0],first=start323[12:1],count={1'b0,span323[11:1]}")
    s=once(s,'active305.encoded,active305.span,active305.start,packet_seq,active305.section,active305.op', 'active305.encoded,header[15],header[14],start323,packet_seq,header[1],active305.op')
    s=once(s,"wire [16:0] decode_end305={1'b0,startpos}+{1'b0,outlen};",'wire [16:0] decode_end305=end323;')
    a=s.index(' reg bad_data278;');b=s.index(' wire bad_internal305=',a)
    s=s[:a]+''' wire bad_data278=sealed||bad_unit323||domain323<3||domain323>7||
   (header[0]==2?span323!=plen:header[0]==8?(plen!=4||span323[1:0]!=0):(plen!=2||span323[0]!=0))||
   (domain323==5&&startpos<scroll_length&&(startpos!=0||decode_end305<scroll_length));
 assign data_command278=header[0]==2||header[0]==4||header[0]==5||header[0]==8;
 wire bad_tile305=domain323>1||bad_unit323||plen!=4||span323>2048;
'''+s[b:]
    a=s.index(' reg [11:0] decoded_first305;');b=s.index(' wire [11:0] receipt_first282=',a)
    s=s[:a]+''' reg [11:0] receipt_base323;
 always @*case(domain323)
  0:receipt_base323=0;1:receipt_base323=1024;3:receipt_base323=1152;
  6:receipt_base323=1184;7:receipt_base323=1312;default:receipt_base323=0;
 endcase
 wire decoded_valid305=unit323&&(domain323==0||domain323==1||domain323==3||domain323==6||(domain323==7&&prelude_raw!=0));
 wire [11:0] decoded_first305=decoded_valid305?receipt_base323+{1'b0,active305.start[10:0]}:12'd0;
 wire [11:0] decoded_limit305=decoded_valid305?receipt_base323+uend323:12'd0;
'''+s[b:]
    # Pattern indexing only depends on the low two bits; independent tap position remains.
    s=once(s,'(tap_pos278-startpos)&', '(tap_pos278[1:0]-startpos[1:0])&')
    s=once(s,"8'h66:control=active305.span[7:0];8'h67:control=active305.span[15:8];", "8'h66:control=header[14];8'h67:control=header[15];")
    p.write_text(s,newline='\n')
