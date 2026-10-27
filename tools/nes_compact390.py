# SPDX-License-Identifier: MIT
"""Connect the real M4 producer and the bounded metadata WRAM namespace."""
from nes_delta231 import ROOT,once

def arm(d):
 p=d/'nes_output264.c';s=p.read_text()
 s=once(s,'static unsigned begin,seal,requirements264;', 'void reset_plan390(void);unsigned step_plan390(uint8_t *);static unsigned sent_plan390;static unsigned emit_plan390(unsigned);\nstatic unsigned begin,seal,requirements264;')
 s=once(s,'  if(p[0]==9&&p[1]==2){','  if(p[0]==9&&p[1]==2){\n   if(state259.serial>=3&&!emit_plan390(1))return 0;')
 # First isolate the ABI: publish immediately before the first map, with all
 # preparation charged there. Early publication is a separate optimization.
 s=once(s,' begin=seal=requirements264=0;', ' reset_plan390();sent_plan390=0;begin=seal=requirements264=0;')
 s+='\n'+(ROOT/'tools/nes_compact390.c').read_text()+'''
static uint8_t wire390[209];
static unsigned emit_plan390(unsigned finish){
 if(sent_plan390)return 1;
 if(!finish&&(uint16_t)(state259.sent-state259.retired)>=2)return 1;
 unsigned n;
 do{n=step_plan390(wire390+17);}while(finish&&!n);
 if(!n)return 1;
 for(unsigned i=1;i<=16;i++)wire390[i]=0;
 wire390[1]=2;wire390[2]=6;w16(wire390+13,n);
 uint8_t *b=wire390+17;b[4]=state259.bank;w16(b+6,state259.generation);w32(b+8,state259.serial);
 if(!send317(n+16,wire390,1))return 0;
 sent_plan390=1;return 1;
}
'''
 p.write_text(s,newline='\n')

def rtl(d):
 p=d/'nes_mux260.sv';s=p.read_text()
 s=once(s," wire [15:0] destination325=(header[1]==3?16'h6000:header[1]==4?16'h6200:16'h6500)"," wire [15:0] destination325=(header[1]==6?16'h7500:header[1]==3?16'h6000:header[1]==4?16'h6200:16'h6500)")
 s=once(s,'       if(sealed||!outlen||decode_end305>', '''       if(header[1]==6)begin
        if(sealed||header[0]!=2||startpos!=0||plen<16||plen>144)bad_data278=1;
       end else if(sealed||!outlen||decode_end305>''')
 s=once(s,'     PUT:if(prelude_mode?mready:put_ready)begin','''     PUT:if(prelude_mode?mready:put_ready)begin
      if(header[1]==6&&!prelude_mode)begin
       case(at)
        0:if(held!=8'h4d)failed<=1;1:if(held!=8'h50)failed<=1;
        2:if(held!=1)failed<=1;3:if(held>2)failed<=1;
        4:if(held!={7'd0,identity[48]})failed<=1;5:if(held!=0)failed<=1;
        6,7:if(held!=identity[32+8*(at-6)+:8])failed<=1;
        8,9,10,11:if(held!=identity[8*(at-8)+:8])failed<=1;
        default:;
       endcase
      end''')
 # Cold retained325 consumer still uses6066/67;do not claim this removal.
 p.write_text(s,newline='\n')
