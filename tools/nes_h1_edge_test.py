# SPDX-License-Identifier: MIT
from pathlib import Path
import re,subprocess
from nes_h1_release_test import TB
from nes_h1_release import frontend as golden_frontend
from nes_h1_edge import ROOT

def run(out,questa):
 tb=TB
 tb=tb.replace('input integer mask);','input integer mask,input integer cause);\n  reg [127:0] saved_snapshot;')
 tb=tb.replace('  bad++;',"""  if(dut.frontend_snapshot[7:0]!==cause[7:0] || dut.frontend_snapshot[127:120]!==8'h41)
   $fatal(1,"wrong causal snapshot got=%h wanted=%h",dut.frontend_snapshot,cause);
  saved_snapshot=dut.frontend_snapshot;
  snes_addr=24'hbadbad;read_n=0;write_n=0;#100;
  if(dut.frontend_snapshot!==saved_snapshot)$fatal(1,"first snapshot overwritten");
  read_n=1;write_n=1;
  bad++;""")
 tb=tb.replace('check_abort(1);','check_abort(1,8);',1)
 tb=tb.replace('check_abort(1);','check_abort(1,2);',1)
 tb=tb.replace('check_abort(1);','check_abort(1,1);',1)
 tb=tb.replace('check_abort(4);','check_abort(4,16);').replace('check_abort(2);','check_abort(2,32);').replace('check_abort(8);','check_abort(8,64);')
 tb=tb.replace('  end\n  if(good!=156',"   init(phase);start_read(24'h408000,0);wait(dut.pending==1);#1;write_n=0;check_abort(4,20);\n  end\n  if(good!=156")
 tb=tb.replace('bad!=72','bad!=84')
 tb=tb.replace('if(fixed_error!==0 || reads!=1','if(dut.frontend_snapshot!==0 || fixed_error!==0 || reads!=1')
 tb=tb.replace('#100;reset=0;#100;@(negedge host_clk);#(phase);','#100;reset=0;#100;if(dut.frontend_snapshot!==0)$fatal(1,"reset snapshot");@(negedge host_clk);#(phase);')
 instance=tb.split(' nes_snes_frontend_legacy old(',1)[1].split(');',1)[0]
 instance=instance.replace('legacy_data','gold_data').replace('legacy_error','gold_error').replace('legacy_oe','gold_oe').replace('legacy_dir','gold_dir').replace('old_dr','gold_dr')
 golden='wire [7:0] gold_data;wire [3:0] gold_error;wire gold_oe,gold_dir,gold_dr;\n nes_snes_frontend_040 golden('+instance+');\n'
 golden+=''' always @(posedge host_clk) begin
  #0.001;
  if({fixed_data,fixed_error,fixed_oe,fixed_dir,dr}!=={gold_data,gold_error,gold_oe,gold_dir,gold_dr})
   $fatal(1,"041 monitor changed040 behavior");
 end
'''
 tb=tb.replace(' integer skew;',golden+' integer skew;')

 tb=tb.replace('  saved_snapshot=dut.frontend_snapshot;',"""  if(cause!=32 && dut.frontend_snapshot[71:48]!==24'h408000)$fatal(1,"latched address");
  if((cause==1 || cause==32) && dut.frontend_snapshot[47:24]!==24'h408001)$fatal(1,"raw address");
  if((cause==1 || cause==8 || cause==16) && dut.frontend_snapshot[87:72]!==16'd1)$fatal(1,"position after response");
  if((cause==2 || cause==20) && dut.frontend_snapshot[9:8]!==2'd1)$fatal(1,"pending causal state");
  if(cause==64 && dut.frontend_snapshot[9:8]!==2'd2)$fatal(1,"missing response causal state");
  saved_snapshot=dut.frontend_snapshot;""")
 calibration="""
  // Aligned strobe lengths independently specify counter values at the event.
  init(0);snes_addr=24'h408000;romsel_n=0;
  repeat(2)@(negedge host_clk);read_n=0;
  repeat(12)@(negedge host_clk);read_n=1;
  repeat(8)@(negedge host_clk);snes_addr=24'h408001;read_n=0;
  repeat(10)@(negedge host_clk);snes_addr=24'h408002;
  #100;
  if(dut.frontend_snapshot[7:0]!==1 || dut.frontend_snapshot[95:88]!==10 ||
     dut.frontend_snapshot[103:96]!==12 || dut.frontend_snapshot[111:104]!==0 ||
     dut.frontend_snapshot[119:112]!==8 || dut.frontend_snapshot[87:72]!==2)
   $fatal(1,"counter calibration got=%h",dut.frontend_snapshot);
  init(0);repeat(300)@(negedge host_clk);snes_addr=24'h408000;romsel_n=0;read_n=0;
  repeat(300)@(negedge host_clk);romsel_n=1;#100;
  if(dut.frontend_snapshot[7:0]!==8 || dut.frontend_snapshot[95:88]!==255 || dut.frontend_snapshot[119:112]!==255)
   $fatal(1,"counter saturation");
  $display("PASS CAUSAL COUNTERS low=10 previous_low=12 previous_high=8 saturation=255");
"""
 tb=tb.replace('  if(good!=156',calibration+'  if(good!=156')

 (out/'release_tb.sv').write_text(tb)
 (out/'nes_snes_frontend_legacy.sv').write_text((ROOT/'src/nes/nes_snes_frontend.sv').read_text().replace('module nes_snes_frontend(','module nes_snes_frontend_legacy('))
 (out/'nes_snes_frontend_040.sv').write_text(golden_frontend().replace('module nes_snes_frontend(','module nes_snes_frontend_040('))
 for label,tool,args in [('edge-vlib','vlib',['edge_work']),('edge-compile','vlog',['-work','edge_work','-sv','nes_snes_frontend.sv','nes_snes_frontend_legacy.sv','nes_snes_frontend_040.sv','release_tb.sv']),('edge','vsim',['-c','-lib','edge_work','release_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(questa/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert cp.returncode==0,label
 log=(out/'edge.log').read_text();assert not re.search(r'\*\* (?:Fatal|Error):',log),log
 assert 'PASS CAUSAL COUNTERS low=10 previous_low=12 previous_high=8 saturation=255' in log,log
 assert 'PASS RELEASE good=156 abort=84 legacy_false_abort=120' in log,log
 return {'normal_cases':156,'real_abort_cases':84,'legacy_false_abort_cases':120,'040_behavior_equal_each_edge':True,'first_cause_retention_reset':True,'cause_classes':7,'counter_calibration_and_saturation':True}
