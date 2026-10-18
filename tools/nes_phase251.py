# SPDX-License-Identifier: MIT
"""Phase-owned shared scratch/receipt RAM; actual packet/CDC binding excluded."""
import re
from nes_block249_rtl import RTL as SOURCE
from nes_receipt250 import RTL as RECEIPT
from nes_delta231 import once

def sources():
 s=SOURCE.replace('nes_source_block249','nes_source_phase251')
 s=once(s,' input wire clk,reset,abort_source,',' input wire [7:0] ram_a_q,ram_b_q,output wire [8:0] ram_a_addr,ram_b_addr,output wire ram_a_we,ram_b_we,output wire [7:0] ram_a_w,ram_b_w,\n input wire clk,reset,abort_source,')
 s=once(s,'base_lo[0:4095],base_hi[0:511],scratch[0:511]','base_lo[0:4095],base_hi[0:511]')
 s=once(s,'reg [7:0] lo_q,hi_q,a_q,b_q;','reg [7:0] lo_q,hi_q;wire [7:0] a_q=ram_a_q,b_q=ram_b_q;')
 for name in ('a','b'):s=once(s,f' always @(posedge clk)begin {name}_q<=scratch[{name}_addr];if({name}_we)scratch[{name}_addr]<={name}_w;end',f' assign ram_{name}_addr={name}_addr;assign ram_{name}_we={name}_we;assign ram_{name}_w={name}_w;')
 v=RECEIPT.replace('nes_receipt250','nes_receipt_phase251')
 v=once(v,' input wire clk,reset,abort_source,',' input wire [7:0] ram_q,output wire [9:0] ram_addr,output wire ram_we,output wire [7:0] ram_wdata,\n input wire clk,reset,abort_source,')
 v=once(v,'reg [7:0] q,wdata,mask,value;','reg [7:0] wdata,mask,value;wire [7:0] q=ram_q;')
 v=once(v,' (* ramstyle="M9K" *) reg [7:0] memory[0:1023];\n always @(posedge clk)begin q<=memory[addr];if(we)memory[addr]<=wdata;end',' assign ram_addr=addr;assign ram_we=we;assign ram_wdata=wdata;')
 sh=re.search(r'module nes_source_block249\((.*?)\);',SOURCE,re.S).group(1)
 vh=re.search(r'module nes_receipt250\((.*?)\);',RECEIPT,re.S).group(1)
 names=lambda h:[re.search(r'(\w+)\s*$',x).group(1) for x in h.split(',')]
 sn=names(sh);vn=names(vh);shared={'clk','reset','abort_source'}
 vh=once(vh,'input wire clk,reset,abort_source,','')
 for name in sorted(set(vn)-shared,key=len,reverse=True):vh=re.sub(r'\b'+name+r'\b','v_'+name,vh)
 vh=vh.replace('output reg','output wire')
 sh=sh.replace('output reg','output wire')
 smap={'start':'start&&start_ready','start_ready':'sr','fault':'efault','ack_valid':'ack_valid&&!out_phase','ack_ready':'er'}
 vmap={n:n if n in shared else 'v_'+n for n in vn};vmap.update(begin_valid='v_begin_valid&&out_phase',range_valid='v_range_valid&&out_phase',check_valid='v_check_valid&&out_phase',finish_valid='v_finish_valid&&out_phase',display_ack='v_display_ack&&out_phase',ready='vr',sealed='vs',fault='vf')
 top='module nes_phase251('+sh+','+vh+');\n'+r'''
 reg out_phase;wire sr,er,vr,vs;wire [3:0] efault,vf;
 wire [8:0] sa,sb;wire saw,sbw;wire [7:0] sad,sbd;
 wire [9:0] va;wire vw;wire [7:0] vd;
 reg [7:0] aq,bq;
 (* ramstyle="M9K" *) reg [7:0] memory[0:1023];
 // Receipt initializes persistent validity once after reset. Thereafter it
 // stays IDLE during source; only explicit input commit transfers ownership.
 reg initialized;
 wire use_validator=out_phase||!initialized;
 wire [9:0] aa=use_validator?va:{1'b1,sa};
 wire [9:0] ba={1'b1,sb};
 wire aw=!reset&&!abort_source&&!fault&&(use_validator?vw:saw);
 wire bw=!reset&&!abort_source&&!fault&&!use_validator&&sbw;
 wire [7:0] ad=use_validator?vd:sad;
 always @(posedge clk)begin aq<=memory[aa];if(aw)memory[aa]<=ad;end
 always @(posedge clk)begin bq<=memory[ba];if(bw)memory[ba]<=sbd;end
 assign fault=efault?efault:vf;
 assign start_ready=sr&&initialized&&!out_phase&&!fault;
 assign ack_ready=er&&!out_phase&&!fault;
 assign v_ready=vr&&out_phase&&!fault;
 assign v_sealed=vs&&out_phase&&!fault;
 assign v_fault=vf;
 always @(posedge clk)begin
  if(reset)begin initialized<=0;out_phase<=0;end
  else if(!fault&&!abort_source)begin
   if(!initialized&&vr)initialized<=1;
   if(ack_valid&&ack_ready&&ack_accept)out_phase<=1;
   if(v_display_ack&&v_sealed)out_phase<=0;
  end
 end
'''
 top+='nes_source_phase251 encoder('+','.join('.'+n+'('+smap.get(n,n)+')' for n in sn)+',.ram_a_q(aq),.ram_b_q(bq),.ram_a_addr(sa),.ram_b_addr(sb),.ram_a_we(saw),.ram_b_we(sbw),.ram_a_w(sad),.ram_b_w(sbd));\n'
 top+='nes_receipt_phase251 validator('+','.join('.'+n+'('+vmap[n]+')' for n in vn)+',.ram_q(aq),.ram_addr(va),.ram_we(vw),.ram_wdata(vd));\nendmodule\n'
 return {'nes_source_phase251.sv':s,'nes_receipt_phase251.sv':v,'nes_phase251.sv':top}
