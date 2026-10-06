# SPDX-License-Identifier: MIT
"""Same pins, legacy and corrected frontend; raw logs preserve both outcomes."""
from pathlib import Path
import re,subprocess
from nes_h1_release import ROOT
TB=r"""
`timescale 1ns/1ps
module release_tb;
 reg host_clk=0;always #5.952381 host_clk=~host_clk;
 reg reset=1,read_n=1,write_n=1,romsel_n=1;
 reg [23:0] snes_addr=0;
 reg data_valid=1;
 wire [3:0] fixed_error,legacy_error;
 wire [7:0] fixed_data,legacy_data;
 wire fixed_oe,fixed_dir,legacy_oe,legacy_dir,dr,old_dr;
 integer reads=0,old_reads=0,good=0,bad=0,legacy_reproduced=0;
 nes_snes_frontend dut(.host_clk(host_clk),.reset(reset),.snes_addr(snes_addr),
  .read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.snes_data_in(8'h00),
  .bus_data(fixed_data),.databus_oe_n(fixed_oe),.databus_dir(fixed_dir),
  .reg_write(),.reg_read(),.data_read(dr),.reg_address(),.reg_wdata(),
  .reg_rdata(8'h55),.data(8'ha6),.reg_rvalid(1'b1),.data_valid(data_valid),
  .ready(1'b1),.busy(1'b0),.fault(1'b0),.frontend_error(fixed_error));
 nes_snes_frontend_legacy old(.host_clk(host_clk),.reset(reset),.snes_addr(snes_addr),
  .read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.snes_data_in(8'h00),
  .bus_data(legacy_data),.databus_oe_n(legacy_oe),.databus_dir(legacy_dir),
  .reg_write(),.reg_read(),.data_read(old_dr),.reg_address(),.reg_wdata(),
  .reg_rdata(8'h55),.data(8'ha6),.reg_rvalid(1'b1),.data_valid(data_valid),
  .ready(1'b1),.busy(1'b0),.fault(1'b0),.frontend_error(legacy_error));
 always @(posedge host_clk) if(reset)begin reads<=0;old_reads<=0;end
  else begin if(dr)reads<=reads+1;if(old_dr)old_reads<=old_reads+1;end
 task automatic init(input integer phase);
  reset=1;read_n=1;write_n=1;romsel_n=1;snes_addr=0;data_valid=1;
  #100;reset=0;#100;@(negedge host_clk);#(phase);
 endtask
 task automatic start_read(input integer address,input integer sel);
  snes_addr=address;romsel_n=sel;#20;read_n=0;
 endtask
 task automatic check_abort(input integer mask);
  #100;
  if((fixed_error&mask)!=mask || (legacy_error&mask)!=mask)
   $fatal(1,"lost real abort fixed=%h old=%h mask=%h",fixed_error,legacy_error,mask);
  read_n=1;write_n=1;romsel_n=1;#100;
  if(!fixed_oe || fixed_dir)$fatal(1,"abort release OE");
  bad++;
 endtask
 integer skew;
 initial begin
  for(integer phase=0;phase<12;phase++)begin
   for(integer width=120;width<=180;width+=60)begin
    for(integer s=0;s<6;s++)begin
     case(s)0:skew=0;1:skew=1;2:skew=6;3:skew=12;4:skew=24;5:skew=36;endcase
     init(phase);start_read(24'h408000,0);#(width);
     if(fixed_oe || !fixed_dir || fixed_data!==8'ha6 || legacy_data!==8'ha6)
      $fatal(1,"payload response phase=%0d width=%0d",phase,width);
     read_n=1;
     #(skew);romsel_n=1;snes_addr=24'h011800;
     #0.001;if(!fixed_oe || fixed_dir)$fatal(1,"raw release not immediate");
     #100;
     if(fixed_error!==0 || reads!=1 || old_reads!=1)
      $fatal(1,"normal release fault/duplicate phase=%0d width=%0d skew=%0d fixed=%h reads=%0d/%0d",phase,width,skew,fixed_error,reads,old_reads);
     if(legacy_error==1)legacy_reproduced++;
     if(skew==0 && legacy_error!==1)$fatal(1,"legacy reproduction missing");
     good++;
    end
   end
   init(phase);start_read(24'h6001,1);#120;
   if(fixed_oe || fixed_data!==8'h55)$fatal(1,"register response");
   read_n=1;snes_addr=24'h011800;#100;
   if(fixed_error!==0 || legacy_error!==0)$fatal(1,"register release");good++;
   // Deselection while RD remains low is still a real abort.
   init(phase);start_read(24'h408000,0);#120;romsel_n=1;
   #0.001;if(!fixed_oe || fixed_dir)$fatal(1,"deselect OE");check_abort(1);
   // RD release before the response is ready must still be rejected.
   init(phase);start_read(24'h408000,0);wait(dut.pending==1);#1;read_n=1;romsel_n=1;check_abort(1);
   init(phase);start_read(24'h408000,0);#120;snes_addr=24'h408001;check_abort(1);
   init(phase);start_read(24'h408000,0);#120;write_n=0;check_abort(4);
   init(phase);start_read(24'h408001,0);#120;check_abort(2);
   init(phase);data_valid=0;start_read(24'h408000,0);#120;check_abort(8);
  end
  if(good!=156 || bad!=72 || legacy_reproduced<24)$fatal(1,"coverage counts");
  $display("PASS RELEASE good=%0d abort=%0d legacy_false_abort=%0d",good,bad,legacy_reproduced);$finish;
 end
 initial begin #1000000;$fatal(1,"release watchdog");end
endmodule
"""
def run(out,questa):
 (out/'nes_snes_frontend_legacy.sv').write_text((ROOT/'src/nes/nes_snes_frontend.sv').read_text().replace('module nes_snes_frontend(','module nes_snes_frontend_legacy('))
 (out/'release_tb.sv').write_text(TB)
 for label,tool,args in [('release-vlib','vlib',['release_work']),('release-compile','vlog',['-work','release_work','-sv','nes_snes_frontend.sv','nes_snes_frontend_legacy.sv','release_tb.sv']),('release','vsim',['-c','-lib','release_work','release_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(questa/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert cp.returncode==0,label
 log=(out/'release.log').read_text();assert not re.search(r'\*\* (?:Fatal|Error):',log),log
 m=re.search(r'PASS RELEASE good=(\d+) abort=(\d+) legacy_false_abort=(\d+)',log);assert m,log
 result=dict(zip(('normal_cases','real_abort_cases','legacy_false_abort_cases'),map(int,m.groups())))
 assert result['normal_cases']==156 and result['real_abort_cases']==72 and result['legacy_false_abort_cases']>=24
 result['board_signature']=snapshot_pair(out,questa)
 return result

def snapshot_pair(out,questa):
 # Whole boundary + queue/stage/producer, not the unit-test response stub.
 prefix=(out/'h1_board_tb.sv').read_text().split(' initial begin\n  log=',1)[0]
 prefix=prefix.replace('module h1_board_tb;','module release_snapshot_tb;\n parameter LEGACY=0;')
 body=r"""
 initial begin
  $readmemh("h1-pattern.hex",pattern);
  #100;locked=1;#1000;query(8'hf0,8'ha5);query(8'hf1,8'h39);
  control(8'he8,8'ha5,8'h5a);while(dut.published<2)#100;acquire(1);
  SNES_ADDR_IN=24'h408000;SNES_ROMSEL_IN=0;#20;SNES_READ_IN=0;#180;
  if(SNES_DATABUS_OE || !SNES_DATABUS_DIR || snes_data_out!==pattern[0])$fatal(1,"snapshot payload response");
  SNES_READ_IN=1;SNES_ROMSEL_IN=1;SNES_ADDR_IN=24'h011800;
  #0.001;if(!SNES_DATABUS_OE || SNES_DATABUS_DIR)$fatal(1,"snapshot release");#100;
  if(LEGACY)begin
   query(8'hf2,7);snapshot_check(8'h87,8'h10,8'h10,24'h011800);
   $display("PASS LEGACY NORMAL RELEASE REPRO F2=07 flags=87 frontend=1 bus=0 producer=0 ROMSEL=1 RD=1 WR=1 addr=011800");
  end else begin
   query(8'hf2,3);query(8'hf5,0);rd(24'h600a,0,1);
   $display("PASS FIXED NORMAL RELEASE F2=03 snapshot=00 frontend=0");
  end
  control(8'he9,8'ha5,8'h5a);query(8'hf2,2);$finish;
 end
 initial begin #5000000;$fatal(1,"snapshot watchdog");end
endmodule
"""
 (out/'release_snapshot_tb.sv').write_text(prefix+body)
 (out/'nes_snes_frontend_original.sv').write_text((ROOT/'src/nes/nes_snes_frontend.sv').read_text())
 names=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus']
 for legacy in (True,False):
  label='snapshot_legacy' if legacy else 'snapshot_fixed'
  src='nes_snes_frontend_original.sv' if legacy else 'nes_snes_frontend.sv'
  jobs=[('vlib','vlib',[label]),('compile','vlog',['-sv','-work',label,*[n+'.sv' for n in names],src,'release_snapshot_tb.sv']),('run','vsim',['-c','-lib',label,'release_snapshot_tb','-gLEGACY='+str(int(legacy)),'-do','onerror {quit -code 1}; run -all; quit -f'])]
  for suffix,tool,args in jobs:
   with (out/(label+'-'+suffix+'.log')).open('wb') as f:
    cp=subprocess.run([str(questa/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
   assert cp.returncode==0,label+suffix
  log=(out/(label+'-run.log')).read_text()
  expected='PASS LEGACY NORMAL RELEASE REPRO F2=07' if legacy else 'PASS FIXED NORMAL RELEASE F2=03'
  assert expected in log and not re.search(r'\*\* (?:Fatal|Error):',log),log
 return {'legacy_F2':7,'legacy_flags':135,'legacy_frontend':1,'legacy_stage':0,'legacy_producer':0,'legacy_address_hex':'011800','fixed_F2':3,'fixed_snapshot':0,'scope':'Legal synthetic bus release; matching recorded status signature, not a measured hardware bus trace'}
