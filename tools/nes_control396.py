# SPDX-License-Identifier: MIT
"""Replace source footer walkers and plan fetch phases by shared executors.
Wire bytes,ring capacity,physical RAM ownership and independent checks stay."""
from nes_delta231 import ROOT,once

def apply(d):
 (d/'nes_walk396.sv').write_text((ROOT/'src/fpga/nes_joint396/nes_walk396.sv').read_text(),newline='\n')
 # The host record executor handles source footer requests between its normal
 # steps. Physical read/CRC capture remains outside the preemptible case.
 p=d/'nes_mux260.sv';s=p.read_text();s=once(s,'module nes_output260 #(', 'module nes_output260 #(')
 # Parameterized declaration has a newline between parameter and ports.
 marker=s.index('input wire',s.index('module '))
 s=s[:marker]+'''input wire footer_request396,input wire[7:0] footer_data396,
 output wire footer_capture396,output wire[2:0] footer_index396,output wire[7:0] footer_address396,
 '''+s[marker:]
 a=s.index('\n',s.index(' wire rst='))+1;s=s[:a]+''' reg footer_phase396;reg[2:0] footer_at396;
 wire footer_active396=footer_request396;
 assign footer_index396=footer_at396;assign footer_address396=8'd250+footer_at396;
 assign footer_capture396=footer_active396&&footer_phase396&&!rst;
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin footer_phase396<=0;footer_at396<=0;end
  else if(!footer_active396)begin footer_phase396<=0;footer_at396<=0;end
  else if(!footer_phase396)footer_phase396<=1;
  else begin footer_phase396<=0;footer_at396<=footer_at396==5?0:footer_at396+1'b1;end
 end
'''+s[a:]
 s=s.replace('if(!fault)case(state)','if(!fault&&!footer_active396)case(state)')
 s=s.replace('.start(state==RCHECK)', '.start(state==RCHECK&&!footer_active396)')
 s=s.replace('state==OPEN&&!reference','state==OPEN&&!reference&&!footer_active396')
 s=once(s,'wire consume=state==TAKE&&!reference;','wire consume=state==TAKE&&!reference&&!footer_active396;')
 s=s.replace("wire aperture_put=(state==PUT&&op!=8'had)||state==EXPAND;", "wire aperture_put=!footer_active396&&((state==PUT&&op!=8'had)||state==EXPAND);")
 s=s.replace('.seal(state==SEAL)', '.seal(state==SEAL&&!footer_active396)')
 s=s.replace('assign allocate=','assign allocate=!footer_active396&&(').replace('||(state==ENDWAIT&&sealed);','||(state==ENDWAIT&&sealed));')
 for name in ('ordinary_finish','context_valid','begin_valid','display_request','display_response_ready'):
  s=s.replace('assign '+name+'=', 'assign '+name+'=!footer_active396&&')
 p.write_text(s,newline='\n')
 # Shared host loader replaces the source's loading/load_step FSM.
 p=d/'nes_transport257.sv';s=p.read_text();s=s.replace('module nes_transport257(','''module nes_transport257(
 input wire footer_capture396,input wire[2:0] footer_index396,input wire[7:0] footer_address396,
 output wire footer_request396,output wire[7:0] footer_data396,
 input wire source_capture396,input wire[2:0] source_index396,output wire source_request396,
''')
 s=s.replace('reg [2:0] footer_at;','wire[2:0] footer_at=source_index396;')
 s=s.replace('footer_busy&&footer_at==5?', 'footer_busy&&source_capture396&&footer_at==5?')
 s=s.replace('if(footer_busy)memory','if(footer_busy&&source_capture396)memory')
 s=s.replace('footer_busy<=1;footer_at<=0;','footer_busy<=1;').replace('footer_busy<=0;footer_at<=0;','footer_busy<=0;')
 s=s.replace('if(footer_at==5)begin footer_busy<=0;', 'if(source_capture396&&footer_at==5)begin footer_busy<=0;')
 s=s.replace("     else footer_at<=footer_at+1'b1;",'')
 s=s.replace('meta_valid,loading,check_generation;reg [3:0] load_step;', 'meta_valid,check_generation;')
 s=s.replace("loading?8'd250+{5'd0,load_step[3:1]}", 'footer_request396?footer_address396')
 s=s.replace('meta_valid<=0;loading<=0;load_step<=0;check_generation<=0;','meta_valid<=0;check_generation<=0;')
 a=s.index('   if(!empty&&!meta_valid&&!loading)');z=s.index('   if(!ss[1]&&!sck[1]',a)
 block=s[a:z];start=block.index('     0:length<=');end=block.index('    endcase',start)
 cases=block[start:end].replace('loading<=0;','')
 s=s[:a]+'''   if(footer_capture396&&footer_request396)case(footer_index396)
'''+cases+'''   endcase
'''+s[z:]
 s=s.replace('loading<=0;check_generation<=','check_generation<=')
 s=s.replace(' assign crc_take270=', ''' assign footer_request396=hr[1]&&!host_fault&&!empty&&!meta_valid;
 assign footer_data396=read_byte;assign source_request396=footer_busy&&source_live;
 assign crc_take270=''')
 assert 'loading'not in s and 'load_step'not in s and 'footer_at<='not in s
 p.write_text(s,newline='\n')
 # Forward both clock-specific services through the existing joint boundary.
 hports='''input wire footer_capture396,input wire[2:0] footer_index396,input wire[7:0] footer_address396,
 output wire footer_request396,output wire[7:0] footer_data396,
 input wire source_capture396,input wire[2:0] source_index396,output wire source_request396,
 '''
 connections='.footer_capture396(footer_capture396),.footer_index396(footer_index396),.footer_address396(footer_address396),.footer_request396(footer_request396),.footer_data396(footer_data396),.source_capture396(source_capture396),.source_index396(source_index396),.source_request396(source_request396),'
 p=d/'nes_joint257.sv';s=p.read_text().replace('module nes_joint257(', 'module nes_joint257('+hports).replace('nes_transport257 transport(', 'nes_transport257 transport('+connections);p.write_text(s,newline='\n')
 p=d/'nes_joint266.sv';s=p.read_text();marker=s.index('output wire capture_materialized366');s=s[:marker]+'''input wire source_capture396,input wire[2:0] source_index396,output wire source_request396,
 '''+s[marker:]
 marker=s.index(' nes_output260 #');s=s[:marker]+''' wire footer_capture396,footer_request396;wire[2:0] footer_index396;wire[7:0] footer_address396,footer_data396;
'''+s[marker:]
 s=s.replace(' flow(.ctx_address375',' flow(.footer_capture396(footer_capture396),.footer_request396(footer_request396),.footer_index396(footer_index396),.footer_address396(footer_address396),.footer_data396(footer_data396),.ctx_address375')
 s=s.replace('nes_joint257 core(', 'nes_joint257 core('+connections);p.write_text(s,newline='\n')
 # One NES cursor executes source footer writes and plan field captures.
 p=d/'nes_plan_batch206.sv';s=p.read_text();marker=s.index(' output wire [9:0] plan_cursor319');s=s[:marker]+''' input wire source_request396,output wire source_capture396,output wire[2:0] source_index396,
'''+s[marker:]
 marker=s.index(' wire shape_ok=');s=s[:marker]+''' wire plan_capture396;
 wire plan_request396=!nr&&!nc&&state==READ&&read_cursor314<batch_length&&remaining!=0&&remaining<=16&&
  !(at>=16&&(alt_index>=8||!plan_alt_mask[alt_index]));
 nes_walk396 execution(.clk(nes_clk),.reset(nr||nc),.source_request(source_request396),.plan_request(plan_request396),
  .source_capture(source_capture396),.source_index(source_index396),.plan_capture(plan_capture396));
'''+s[marker:]
 s=s.replace('(state==CAPTURE&&at!=length-1)', '(state==READ&&plan_capture396&&at!=length-1)')
 a=s.index('    READ:begin');z=s.index('     if(at==0&&data[7])',a)
 s=s[:a]+'''    READ:begin
     if(read_cursor314>=batch_length||remaining==0||remaining>16||(at>=16&&alt_index>=8))nf<=1;
     else if(at>=16&&!plan_alt_mask[alt_index])alt_index<=alt_index+1'b1;
     else if(plan_capture396)begin
'''+s[z:]
 marker='    CHECK:if(!shape_ok';at=s.index(marker);s=s[:at].rstrip()+'\n    end\n'+s[at:];p.write_text(s,newline='\n')
 p=d/'nes_plan_path267.sv';s=p.read_text().replace('module nes_plan_path267(','''module nes_plan_path267(
 input wire source_request396,output wire source_capture396,output wire[2:0] source_index396,
''');s=s.replace('transport(.plan_cursor319', 'transport(.source_request396(source_request396),.source_capture396(source_capture396),.source_index396(source_index396),.plan_cursor319');p.write_text(s,newline='\n')
 # Physical board and functional bench use exactly the same cross-path wires.
 wire='wire source_request396,source_capture396;wire[2:0] source_index396;\n'
 con='.source_request396(source_request396),.source_capture396(source_capture396),.source_index396(source_index396),'
 p=d/'nes_live_joint.sv';s=p.read_text().replace('nes_joint267_board native_joint267(',wire+'nes_joint267_board native_joint267('+con).replace('nes_plan_path267 retained_plan267(','nes_plan_path267 retained_plan267('+con);p.write_text(s,newline='\n')

def bench(s):
 wire='wire source_request396,source_capture396;wire[2:0] source_index396;\n'
 con='.source_request396(source_request396),.source_capture396(source_capture396),.source_index396(source_index396),'
 return s.replace('nes_joint267_board dut(',wire+'nes_joint267_board dut('+con).replace('nes_plan_path267 planrom(','nes_plan_path267 planrom('+con)
