# SPDX-License-Identifier: MIT
"""Replace source/output/plan SPI sampling, status and CRC8 control together."""
import re
from nes_delta231 import ROOT,once

PORTS=' input wire [48:0] link270,output wire [183:0] status270,output wire crc_take270,\n'
BIND='.link270(link270),.status270(status270),.crc_take270(crc_take270),'
LINK=''' wire [7:0] common_crc270,status_reply270,command,incoming;
 wire [9:0] count270;wire [2:0] bits270;wire [1:0] ss,sck;wire prev_ss,prev_sck;
 assign {common_crc270,status_reply270,command,incoming,count270,bits270,ss[1],sck[1],prev_ss,prev_sck}=link270;
 assign ss[0]=1'b0;assign sck[0]=1'b0;
'''

def endpoint(s,kind):
 start=s.index(' (* ',s.index('module ')) if kind!='source' else s.index(' (* async_reg="true" *) reg [1:0] ss,sck,mosi;')
 if kind=='queue':start=s.index(' (* altera_attribute=')
 if kind=='plan':start=s.index(' (* altera_attribute=')
 end=s.index(' wire ours=',start)
 old=s[start:end]
 # Keep only owner-specific storage; shared link has a saturating count.
 if kind=='queue':
  new=LINK+''' wire [8:0] byte_count=count270>511?9'd511:count270[8:0];wire [2:0] bit_count=bits270;
 reg miso_hold,can_write;reg [15:0] payload_size,request_crc,received_crc;reg [7:0] reply;
 assign crc_take270=1'b0;
 assign status270={8'hf8,flags,accepted,retired,progress_status,8'd0};
'''
 elif kind=='source':
  new=LINK+''' wire [8:0] byte_count=count270>511?9'd511:count270[8:0];wire [2:0] bit_count=bits270;
 reg miso_hold;reg [7:0] read_byte,arg,arg_not,received_crc,tail;reg [23:0] offset;
 wire [7:0] request_crc=common_crc270;
 wire [7:0] read_address=byte_count[7:0]-1'b1;
 always @(posedge host_clk)read_byte<=memory[{read_bank,read_address}];
 assign crc_take270=byte_count<6&&(byte_count==0?(incoming>=8'hd0&&incoming<=8'hd3):ours);
 assign status270={8'hd8,flags,token,8'd0,length,8'd0,128'd0};
'''
 else:
  new=LINK+''' wire [9:0] count=count270;wire [2:0] bits=bits270;
 reg miso_hold,can_write,ended,retiring;reg [15:0] ended_generation;
 reg [15:0] length;reg [7:0] number,tail,received8;wire [7:0] request8=common_crc270;
 reg [15:0] received16,accepted;reg [7:0] reply;
 assign crc_take270=count==0?(incoming==8'he8||incoming==8'he9||incoming==8'hea):
  (command==8'hea ? count<=4 : command==8'he9&&(count<=length+5||count<=3));
'''
 s=s[:start]+new+s[end:]
 # Sampling and counters belong only to nes_spi270 now.
 for assignment in ['ss<=3;','sck<=0;','mosi<=0;','prev_ss<=1;','prev_sck<=0;',
  'ss<={ss[0],SPI_SS};','sck<={sck[0],SPI_SCK};','mosi<={mosi[0],SPI_MOSI};',
  'prev_ss<=ss[1];','prev_sck<=sck[1];','shift<=0;','shift<=incoming;',
  'command<=0;','command<=incoming;','bit_count<=0;','byte_count<=0;','bits<=0;','count<=0;',
  "bit_count<=bit_count+1'b1;","byte_count<=byte_count+1'b1;","bits<=bits+1'b1;","count<=count+1'b1;"]:
  s=re.sub(r'\b'+re.escape(assignment),'',s)
 s=s.replace('if(bit_count==7)begin\n     if(byte_count!=511)','if(bit_count==7)begin')
 s=s.replace('if(bits==7)begin\n     if(count!=1023)','if(bits==7)begin')
 # Remove empty remnants from the shared count updates.
 s=re.sub(r'if\((?:byte_count!=511|count!=1023)\)\s*(?=if|\n)', '',s)
 if kind=='queue':
  a=s.index('   if(crc_busy)begin');b=s.index('\n\n',a);s=s[:a]+s[b:]
  s=re.sub(r'\b(?:snapshot(?:\[[^\]]+\])?|status_crc|crc_busy|crc_position)\s*<=\s*[^;]+;', '',s)
  s=once(s,"wire ours=command==8'he0||command==8'he1;","wire ours=command==8'he0||command==8'he1||command==8'he2;")
  a=s.index('  reply=0;');b=s.index('\n end',a);s=s[:a]+'  reply=status_reply270;'+s[b:]
  s=once(s,"if(command==8'he0)begin if(byte_count!=24||bit_count!=0)fault<=1;end", "if(command==8'he0||command==8'he2)begin if(byte_count!=(command==8'he2 ? 9 : 24)||bit_count!=0)fault<=1;end")
 elif kind=='source':
  s=re.sub(r' wire \[7:0\] status_crc=[^;]+;', '',s)
  a=s.index('  end else case(byte_count)');b=s.index('\n end\n always',a);s=s[:a]+'  end else reply=status_reply270;'+s[b:]
  s=re.sub(r'\b(?:snapshot|request_crc)\s*<=\s*[^;]+;', '',s)
  s=s.replace('     if(byte_count<6)\n','')
 else:
  a=s.index('   if(crc_busy)begin');b=s.index('   if(!ss[1]',a);s=s[:a]+s[b:]
  a=s.index('      snapshot<=');b=s.index(';',a);expr=s[a+len('      snapshot<='):b]
  s=s[:a]+s[b+1:];s=s.replace(' wire ours=',f' assign status270={{{expr},32\'d0}};\n wire ours=',1)
  s=re.sub(r'\b(?:snapshot|status_crc|crc_busy|crc_at|request8)\s*<=\s*[^;]+;', '',s)
  s=s.replace('      if(count<=4)\n','').replace('      if(count<=length+5||count<=3)\n','')
  a=s.index('  reply=0;');b=s.index('\n end',a);s=s[:a]+'  reply=status_reply270;'+s[b:]
 # Old c8 functions become unused and are removed in synthesis; strip for audit.
 s=re.sub(r' function automatic \[7:0\] (?:crc8|c8)\([^\n]+\n.*? endfunction\n','',s,flags=re.S)
 assignments=re.findall(r' assign (?:status270|crc_take270)=[^;]+;',s)
 for a in assignments:s=s.replace(a,'')
 s=s.replace('endmodule','\n'+'\n'.join(assignments)+'\nendmodule')
 p=s.index('(',s.index('module '))+1;s=s[:p]+'\n'+PORTS+s[p:]
 return s

def pass_ports(s,child):
 p=s.index('(',s.index('module '))
 if s[p:p+2]=='(#':raise AssertionError('unexpected header')
 # Parameterized wrappers: insert into the port list after #(parameter...).
 if '#(' in s[s.index('module '):p+1]:p=s.index(')(',p)+1
 s=s[:p+1]+'\n'+PORTS+s[p+1:]
 return once(s,child,child+BIND)

def patch_files(d):
 for n,k in [('nes_queue260.sv','queue'),('nes_transport257.sv','source'),('nes_plan_spi200.sv','plan')]:
  p=d/n
  if p.exists():p.write_text(endpoint(p.read_text(),k),encoding='utf-8',newline='\n')
 for n,child in [('nes_joint257.sv','nes_transport257 transport('),('nes_mux260.sv','nes_queue260 queue(')]:
  p=d/n;p.write_text(pass_ports(p.read_text(),child),encoding='utf-8',newline='\n')
 (d/'nes_spi270.sv').write_bytes((ROOT/'tools/nes_spi270.sv').read_bytes())

def joint_ports(s):
 # Source and output channels cross this wrapper independently.
 p=s.index(')(')+1
 s=s[:p+1]+'''input wire [48:0] link270,output wire [183:0] source_status270,output_status270,
 output wire source_crc270,output_crc270,\n'''+s[p+1:]
 s=once(s,'nes_joint257 core(', 'nes_joint257 core(.link270(link270),.status270(source_status270),.crc_take270(source_crc270),')
 s=once(s,'flow(.', 'flow(.link270(link270),.status270(output_status270),.crc_take270(output_crc270),.')
 return s

def top_bus(clk,reset,ss,sck,mosi):
 return f'''wire [48:0] link270;wire [183:0] source_status270,output_status270,plan_status270;
 wire source_crc270,output_crc270,plan_crc270;
 nes_spi270 spi_front270(.clk({clk}),.reset({reset}),.SPI_SS({ss}),.SPI_SCK({sck}),.SPI_MOSI({mosi}),
 .source_status(source_status270),.output_status(output_status270),.plan_status(plan_status270),
 .request_crc_enable(source_crc270||plan_crc270),.link(link270));
'''

JOINT_BIND='.link270(link270),.source_status270(source_status270),.output_status270(output_status270),.source_crc270(source_crc270),.output_crc270(output_crc270),'
PLAN_BIND='.link270(link270),.status270(plan_status270),.crc_take270(plan_crc270),'
