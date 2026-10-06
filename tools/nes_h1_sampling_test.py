# SPDX-License-Identifier: MIT
"""043 normal termination, real aborts, single-event capture and skew regression."""
import re,subprocess
from nes_h1_release_test import TB
from nes_h1_sampling import ROOT

def run(out,questa):
 tb=TB.replace('module release_tb;','module release_tb;\n parameter RD_DELAY=0,ADDR_DELAY=0,SEL_DELAY=0,WR_DELAY=0;')
 wires="""
 reg inject_wr_x=0;wire delayed_rd,delayed_wr,delayed_sel;wire [23:0] delayed_addr;
 assign #(RD_DELAY) delayed_rd=read_n;
 assign #(WR_DELAY) delayed_wr=inject_wr_x ? 1'bx : write_n;
 assign #(SEL_DELAY) delayed_sel=romsel_n;
 assign #(ADDR_DELAY) delayed_addr=snes_addr;
"""
 tb=tb.replace(' nes_snes_frontend dut(',wires+' nes_snes_frontend dut(')
 start=tb.index(' nes_snes_frontend dut(');end=tb.index(' nes_snes_frontend_legacy',start)
 instance=tb[start:end].replace('.snes_addr(snes_addr)','.snes_addr(delayed_addr)').replace('.read_n(read_n)','.read_n(delayed_rd)').replace('.write_n(write_n)','.write_n(delayed_wr)').replace('.romsel_n(romsel_n)','.romsel_n(delayed_sel)')
 instance=instance.replace('.reg_write(),.reg_read(),','.reg_write(test_reg_write),.reg_read(),').replace('.reg_address(),.reg_wdata(),','.reg_address(test_reg_address),.reg_wdata(test_reg_data),')
 tb=tb[:start]+instance+tb[end:]
 tb=tb.replace(' wire [3:0] fixed_error,legacy_error;',""" wire test_reg_write;wire [3:0] test_reg_address;wire [7:0] test_reg_data;integer write_count=0;
 always @(posedge host_clk)if(reset)write_count<=0;else if(test_reg_write)begin
  write_count<=write_count+1;
  if(test_reg_address!==4'h2 || test_reg_data!==0)$fatal(1,"wrong qualified write");
 end
 wire [3:0] fixed_error,legacy_error;""")
 # Immediate release is checked from the actual delayed pad edge.
 tb=tb.replace('#0.001;if(!fixed_oe', '#12.001;if(!fixed_oe')
 tb=tb.replace('input integer mask);','input integer mask,input integer cause);\n  reg [127:0] saved_snapshot;')
 tb=tb.replace('  bad++;',"""  if(dut.frontend_snapshot[7:0]!==cause[7:0] || dut.frontend_snapshot[127:120]!==8'h44)
   $fatal(1,"wrong first cause got=%h expected=%h",dut.frontend_snapshot,cause);
  if(dut.frontend_snapshot[91:88]!==dut.error_mask(cause[7:0]))$fatal(1,"captured cause/mask disagree");
  if(cause==1 || cause==32)begin
   if(dut.frontend_snapshot[47:24]!==24'h408001)$fatal(1,"decision address missing");
  end
  saved_snapshot=dut.frontend_snapshot;
  snes_addr=24'hbadbad;read_n=0;write_n=0;#100;
  if(dut.frontend_snapshot!==saved_snapshot)$fatal(1,"first event overwritten");
  read_n=1;write_n=1;bad++;""")
 for mask,cause in [(1,8),(1,2),(1,1),(4,20),(2,32),(8,64)]:
  tb=tb.replace('check_abort(%d);'%mask,'check_abort(%d,%d);'%(mask,cause),1)
 tb=tb.replace('  end\n  if(good!=156',"   init(phase);start_read(24'h408000,0);wait(dut.pending==1);#1;write_n=0;check_abort(4,20);\n  end\n  if(good!=156")
 tb=tb.replace('bad!=72','bad!=84')
 tb=tb.replace('if(fixed_error!==0 || reads!=1','if(dut.frontend_snapshot!==0 || fixed_error!==0 || reads!=1')
 tb=tb.replace('#100;reset=0;#100;@(negedge host_clk);#(phase);','#100;reset=0;#100;if(dut.frontend_snapshot!==0)$fatal(1,"reset snapshot");@(negedge host_clk);#(phase);')
 # Check the registered event really is the sole source of BOTH outputs at every edge.
 monitor="""
 reg [7:0] checked_cause;reg [3:0] checked_error;reg [127:0] checked_event,checked_snapshot;
 always @(posedge host_clk)begin
  checked_cause=dut.event_cause;checked_error=fixed_error;
  checked_event=dut.event_snapshot;checked_snapshot=dut.frontend_snapshot;
  if(!reset)begin
   #0.001;
   if(fixed_error!==(checked_error|dut.error_mask(checked_cause)))$fatal(1,"sticky error bypassed registered event");
   if(checked_snapshot[7:0]==0 && checked_cause!=0)begin
    if(dut.frontend_snapshot!==checked_event)$fatal(1,"capture bypassed registered event");
   end else if(dut.frontend_snapshot!==checked_snapshot)$fatal(1,"first capture changed");
  end
 end
"""
 # Consecutive address changes at release must not become phantom next reads.
 sequential="""
  for(integer phase=0;phase<12;phase++)begin
   init(phase);
   for(integer k=0;k<64;k++)begin
    start_read(24'h408000+k,0);#120;
    if(fixed_oe || fixed_data!==8'ha6)$fatal(1,"stream response k=%0d",k);
    read_n=1;romsel_n=1;snes_addr=24'h011800;#155;
    if(fixed_error!==0 || reads!=k+1)$fatal(1,"stream error/duplicate k=%0d err=%h count=%0d",k,fixed_error,reads);
   end
  end
  // Unselected ROM cycles are outside this frontend; no phantom early-release fault.
  init(0);
  repeat(32)begin start_read(24'h008000,0);#120;read_n=1;romsel_n=1;snes_addr=0;#155;end
  if(fixed_error!==0 || reads!=0)$fatal(1,"unselected cycle falsely tracked");
  // Once a real fault is sticky, the diagnostic register remains readable.
  init(0);start_read(24'h408001,0);#120;read_n=1;#155;
  start_read(24'h600a,1);#120;
  if(fixed_oe || fixed_data!==8'h02)$fatal(1,"error register inaccessible");
  read_n=1;#155;
  // X models vendor notifier uncertainty, not a physical voltage.
  init(0);snes_addr=24'h6002;#40;write_n=0;#220;
  @(negedge host_clk);inject_wr_x=1;write_n=1;
  repeat(3)@(negedge host_clk);inject_wr_x=0;#150;
  if(write_count!=1 || fixed_error!==0)$fatal(1,"write lost/duplicated after uncertainty count=%0d",write_count);
  #150;if(write_count!=1)$fatal(1,"write repeated while idle");
  $display("PASS STREAM bytes=768 unselected=32 error_register=1 shared_event_every_edge=1 write_uncertainty=1");
"""
 tb=tb.replace(' integer skew;',monitor+' integer skew;').replace('  if(good!=156',sequential+'  if(good!=156')
 (out/'release_tb.sv').write_text(tb)
 (out/'nes_snes_frontend_legacy.sv').write_text((ROOT/'src/nes/nes_snes_frontend.sv').read_text().replace('module nes_snes_frontend(','module nes_snes_frontend_legacy('))
 def command(label,tool,args):
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(questa/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(out/(label+'.log')).read_text();assert cp.returncode==0 and not re.search(r'\*\* (?:Fatal|Error):',log),label+'\n'+log[-3500:]
  return log
 command('qualified-vlib','vlib',['qualified_work'])
 command('qualified-compile','vlog',['-work','qualified_work','-sv','nes_snes_frontend.sv','nes_snes_frontend_legacy.sv','release_tb.sv'])
 cases=[]
 for label,rd,addr,sel,wr in [('aligned',0,0,0,0),('rd_late',11,0,0,0),('addr_late',0,11,0,0),('sel_late',0,0,11,0),('wr_late',0,0,0,11),('crossed',11,6,1,9)]:
  log=command('qualified-'+label,'vsim',['-c','-lib','qualified_work','release_tb',f'-gRD_DELAY={rd}',f'-gADDR_DELAY={addr}',f'-gSEL_DELAY={sel}',f'-gWR_DELAY={wr}','-do','onerror {quit -code 1}; run -all; quit -f'])
  assert 'PASS RELEASE good=156 abort=84' in log and 'PASS STREAM bytes=768' in log,log
  cases.append(dict(name=label,rd_delay_ns=rd,addr_delay_ns=addr,sel_delay_ns=sel,wr_delay_ns=wr))
 # Negative control: restoring the one-edge completion must lose the write.
 from nes_h1_sampling import frontend
 old=frontend().replace('if(wr_sync[1] && wr_previous)begin','if(wr_sync[1]&&!wr_previous)begin')
 assert old!=frontend()
 (out/'edge_completion_control.sv').write_text(old)
 command('edge-control-vlib','vlib',['edge_control_work'])
 command('edge-control-compile','vlog',['-work','edge_control_work','-sv','edge_completion_control.sv','nes_snes_frontend_legacy.sv','release_tb.sv'])
 with (out/'edge-control.log').open('wb') as f:
  cp=subprocess.run([str(questa/'vsim.exe'),'-c','-lib','edge_control_work','release_tb','-do','onerror {quit -code 1}; run -all; quit -f'],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 log=(out/'edge-control.log').read_text()
 assert 'Fatal: write lost/duplicated after uncertainty count=0' in log,log[-3000:]
 return dict(normal_cases=936,real_abort_cases=504,stream_bytes=4608,unselected_cycles=192,skew_cases=cases,shared_event_every_edge=True,uncertain_write_release_cases=6,edge_completion_negative_control="lost write reproduced",scope='RTL bounded pad skew <=11ns; not an analog metastability or external-board timing proof')
