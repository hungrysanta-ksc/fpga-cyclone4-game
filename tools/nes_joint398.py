# SPDX-License-Identifier: MIT
"""398 actual-count EA and shared byte execution materialization."""
from nes_delta231 import ROOT,once
import nes_joint396 as old

def arm(d):
 old.arm(d);p=d/'nes_decode280.c';s=p.read_text()
 s=once(s,'source_hint_tags367=n;for(unsigned j=n;j<7;j++)tags[j]=tags[0];','source_hint_tags367=n;')
 s=once(s,'w[0]=0xea;w[1]=7;','w[0]=0xea;w[1]=(uint8_t)n;')
 s=once(s,'for(unsigned i=0;i<7;i++){w[12+i*2]', 'for(unsigned i=0;i<n;i++){w[12+i*2]')
 s=once(s,'uint16_t c=65535;for(unsigned i=0;i<26;i++)c=crc_source368(c,w[i]);w[26]=(uint8_t)c;w[27]=(uint8_t)(c>>8);return 28;',
  'unsigned last=12+n*2;uint16_t c=65535;for(unsigned i=0;i<last;i++)c=crc_source368(c,w[i]);w[last]=(uint8_t)c;w[last+1]=(uint8_t)(c>>8);return last+2;')
 p.write_text(s,newline='\n')
 p=d/'nes_output264.c';s=p.read_text()
 s=once(s,'  if((p[0]==10||p[0]==11)&&map_issued327)return 1;', '''  if((p[0]==10||p[0]==11)&&map_issued327)return 1;
  /* Legacy fragments and the incremental whole-map builder are exclusive. */
  if(p[0]==10||p[0]==11)map_disabled327=1;''')
 s=once(s,'wire259[1]=3;if(!send(16)||!drain())return 0;seal=1;return 1;', '''/* Reserve the terminal phase before publication or a credit wait. */
   seal=1;wire259[1]=3;if(!send(16)||!drain())return 0;return 1;''')
 p.write_text(s,newline='\n')

def ea(d):
 p=d/'nes_spi270.sv';s=p.read_text();s=s.replace('reg crc_good280,tail_good280;','reg crc_good280,tail_good280;reg[4:0] hint_length398;reg hint_count_ok398;')
 s=s.replace('(count==28&&request_value280==payload_crc280)','(hint_count_ok398&&count==hint_length398&&request_value280==payload_crc280)')
 s=s.replace("command==8'hea&&count<26", "command==8'hea&&count<hint_length398-2")
 s=s.replace('request_length280<=0;request_value280<=0;request_number280<=0;\n   crc_good280', 'request_length280<=0;request_value280<=0;request_number280<=0;hint_length398<=28;hint_count_ok398<=0;\n   crc_good280')
 s=s.replace("1:request_length280[7:0]<=incoming;2:request_length280[15:8]<=incoming;", "1:begin request_length280[7:0]<=incoming;hint_count_ok398<=incoming>=1&&incoming<=7;hint_length398<=14+{incoming[2:0],1'b0};end 2:request_length280[15:8]<=incoming;")
 s=s.replace("26:request_value280[7:0]<=incoming;27:request_value280[15:8]<=incoming;", "default:begin if(count==hint_length398-2)request_value280[7:0]<=incoming;if(count==hint_length398-1)request_value280[15:8]<=incoming;end")
 # Remove the original second default after the generated default.
 s=s.replace("if(count==hint_length398-1)request_value280[15:8]<=incoming;end\n     default:;", "if(count==hint_length398-1)request_value280[15:8]<=incoming;end")
 p.write_text(s,newline='\n')
 p=d/'nes_plan_spi200.sv';s=p.read_text().replace("command==8'hea&&count==28", "command==8'hea&&count>=16&&count<=28&&!count[0]");p.write_text(s,newline='\n')
 p=d/'nes_plan_path267.sv';s=p.read_text();s=s.replace('reg [111:0] tags;', 'reg [111:0] tags;reg[2:0] tag_count398;reg[6:0] last398;')
 s=s.replace("command==8'hea&&count==28", "command==8'hea&&count==14+{tag_count398,1'b0}")
 s=s.replace('tags<=0;invalid<=0;', 'tags<=0;tag_count398<=0;last398<=0;invalid<=0;')
 s=s.replace('1:if(incoming!=7)invalid<=1;', "1:begin tag_count398<=incoming[2:0];if(incoming<1||incoming>7)invalid<=1;end")
 s=s.replace('else begin launch<=!launch;used<=1;end', "else begin launch<=!launch;used<=1;last398<={tag_count398,4'b0}-1'b1;end")
 s=s.replace('count>=12&&count<26','count>=12&&count<12+{tag_count398,1\'b0}')
 s=s.replace('cursor==111','cursor==last398')
 p.write_text(s,newline='\n')

def rtl(d):
 old.rtl(d);ea(d);host(d);plan(d);spi(d);hint(d)

def ea_only(d):
 old.rtl(d);ea(d)

def host(d):
 from nes_host398 import host_program,IO
 p=host_program();code=p.finish();code += [15<<14|255]*(4096-len(code))
 (d/'program398.hex').write_text('\n'.join(f'{x:05x}'for x in code)+'\n',newline='\n')
 import json
 (d/'program398.json').write_text(json.dumps(dict(words=len(p.code),labels=p.labels),indent=2)+'\n')
 (d/'nes_byte398.sv').write_text((ROOT/'src/fpga/nes_exec398/nes_byte398.sv').read_text(),newline='\n')
 q=d/'nes_mux260.sv';s=q.read_text();at=s.index(' wire rst=')
 body=(ROOT/'src/fpga/nes_exec398/host_body.svh').read_text().replace('@ENTRY@','0').replace('@IRQ@',str(p.labels['interrupt']))
 body=body.replace('@IO_CONSTANTS@','localparam '+','.join('IO_'+k+'='+str(v)for k,v in IO.items())+';')
 q.write_text(s[:at]+body,newline='\n')
 q=d/'nes_stage396.sv';s=q.read_text().replace('input wire begin_valid,begin_tile','input wire meta_pause398,output wire meta_atomic398,\n input wire begin_valid,begin_tile')
 s=s.replace('wire live=active', 'assign meta_atomic398=ps==P_COPY||ps==P_STAMP||binding&&bs==B_CAP;\n wire live=active')
 s=s.replace('P_IDLE:begin','P_IDLE:if(!meta_pause398)begin').replace('P_READ:ps<=P_COPY;','P_READ:if(!meta_pause398)ps<=P_COPY;')
 s=s.replace('B_READ:bs<=B_CAP;','B_READ:if(!meta_pause398)bs<=B_CAP;')
 q.write_text(s,newline='\n')
 # The same interpreter owns queue identity and completion, not a second FSM.
 q=d/'nes_queue260.sv';s=q.read_text();s=s.replace('module nes_queue260(', 'module nes_queue260(\n output wire irq398,input wire control_write398,input wire[7:0]control_address398,output reg[7:0]control_q398,')
 at=s.index(' (* ramstyle=');q.write_text(s[:at]+(ROOT/'src/fpga/nes_exec398/queue_body.svh').read_text(),newline='\n')

HINT_PORTS='.hint_metaactive398(hint_metaactive398),.hint_meta_at398(hint_meta_at398),.hint_meta_q398(hint_meta_q398),'
def hint_top(s):
 s=s.replace('wire source_request396,source_capture396;wire[2:0] source_index396;',
  'wire hint_metaactive398;wire[3:0]hint_meta_at398;wire[7:0]hint_meta_q398;\n wire source_request396,source_capture396;wire[2:0] source_index396;')
 return s.replace('(.source_request396(', '('+HINT_PORTS+'.source_request396(')

def hint(d):
 q=d/'nes_mux260.sv';s=q.read_text().replace('input wire footer_request396,','input wire hint_metaactive398,input wire[3:0]hint_meta_at398,output wire[7:0]hint_meta_q398,\n input wire footer_request396,',1)
 s=s.replace('tile_link(.nes_clk(', 'tile_link('+HINT_PORTS+'.nes_clk(')
 q.write_text(s,newline='\n')
 q=d/'nes_tile_link394.sv';s=q.read_text().replace('module nes_tile_link394(input wire nes_clk', 'module nes_tile_link394(input wire hint_metaactive398,input wire[3:0]hint_meta_at398,output reg[7:0]hint_meta_q398,input wire nes_clk')
 s=s.replace('assign tile_ready=!sr', 'assign tile_ready=!hint_metaactive398&&!sr')
 s=s.replace('always @(posedge nes_clk)if(tile_valid&&tile_ready&&valid_input&&tile_index==next_index)memory[tile_index]<=tile_data;', '''wire[9:0]nes_at398=hint_metaactive398 ? 10'd928+hint_meta_at398 : {5'd0,tile_index};
 always @(posedge nes_clk)begin
  hint_meta_q398<=memory[nes_at398];
  if(tile_valid&&tile_ready&&valid_input&&tile_index==next_index)memory[nes_at398]<=tile_data;
 end''')
 q.write_text(s,newline='\n')
 q=d/'nes_joint266.sv';s=q.read_text().replace('input wire source_capture396,','input wire hint_metaactive398,input wire[3:0]hint_meta_at398,output wire[7:0]hint_meta_q398,\n input wire source_capture396,',1)
 s=s.replace(' flow(.footer_capture396(', ' flow('+HINT_PORTS+'.footer_capture396(');q.write_text(s,newline='\n')
 q=d/'nes_plan_path267.sv';s=q.read_text();s=s[:s.index('module nes_hint361(')]+(ROOT/'src/fpga/nes_exec398/hint.sv').read_text()
 s=s.replace('module nes_plan_path267(', 'module nes_plan_path267(output wire hint_metaactive398,output wire[3:0]hint_meta_at398,input wire[7:0]hint_meta_q398,',1)
 s=s.replace(' wire ha361,', ' wire[199:0]endpoint_status398;wire[7:0]hint_control_q398;\n assign status270={endpoint_status398[199:8],endpoint_status398[7:0]|hint_control_q398};\n wire ha361,',1)
 s=s.replace('hint(.host_clk(', 'hint(.control_q398(hint_control_q398),.meta_active398(hint_metaactive398),.meta_at398(hint_meta_at398),.meta_q398(hint_meta_q398),.host_clk(')
 s=s.replace('.status270(status270)', '.status270(endpoint_status398)')
 q.write_text(s,newline='\n')
 q=d/'nes_live_joint.sv'
 if q.exists():q.write_text(hint_top(q.read_text()),newline='\n')

def plan(d):
 # Forty explicit host-clock bus bits. No new asynchronous side channel.
 for q in d.glob('*.sv'):
  s=q.read_text();s=s.replace('[113:0]','[153:0]');q.write_text(s,newline='\n')
 q=d/'nes_spi270.sv';s=q.read_text().replace(' assign link[113]=transaction_admit319;',' assign link[145:114]=output_status[95:64];assign link[153:146]=plan_status[7:0];\n assign link[113]=transaction_admit319;');q.write_text(s,newline='\n')
 q=d/'nes_plan_spi200.sv';s=q.read_text();at=s.index(' wire raw=');q.write_text(s[:at]+(ROOT/'src/fpga/nes_exec398/plan_body.svh').read_text(),newline='\n')

def spi(d):
 q=d/'nes_spi270.sv';s=q.read_text();a=s.index("   if(command==8'he1)begin");z=s.index('\n  end\n end\n\n always @(posedge clk',a)
 s=s[:a]+s[z:]
 s=s.replace('  end else if(ss[1])begin\n   // The sealed', '  end else begin if(ss[1])begin\n   // The sealed',1)
 s=s.replace("assign link[112]=command==8'he9", "assign link[112]=command==8'hea ? hint_count_ok398 : command==8'he9")
 a=s.index('\n end\n\n always @(posedge clk',a)
 s=s[:a]+'''\n  // The last signature byte has only the SS hold interval to commit. These
  // fixed checksum events are physical hot-lane work, not deferred bytecode.
  if(!reset&&byte_event)begin
   if(((command==8'hd4||command==8'hd5)&&count==6)||(command==8'hea&&count==5)||(command==8'he9&&count==request_length280+6))crc_good280<=incoming==request_crc;
   if(((command==8'hd4||command==8'hd5)&&count==7)||(command==8'hea&&count==6)||(command==8'he9&&count==request_length280+7))tail_good280<=incoming==8'ha5;
   if(command==8'hea&&hint_count_ok398&&count==hint_length398-2)request_value280[7:0]<=incoming;
   if(command==8'hea&&hint_count_ok398&&count==hint_length398-1)request_value280[15:8]<=incoming;
  end
  if(!reset&&output_status[88])case(output_status[87:80])
   144:request_length280[7:0]<=output_status[79:72];145:request_length280[15:8]<=output_status[79:72];
   146:request_value280[7:0]<=output_status[79:72];147:request_value280[15:8]<=output_status[79:72];
   148:request_number280<=output_status[79:72];
   151:hint_count_ok398<=output_status[72];152:hint_length398<=output_status[76:72];
   default:;
  endcase
  end
'''+s[a:]
 q.write_text(s,newline='\n')
