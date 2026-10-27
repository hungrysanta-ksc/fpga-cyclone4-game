# SPDX-License-Identifier: MIT
"""Unit-test the exact materialized390 RTL admission and PUT identity decisions.

This is not a new integrated STOP/fault/RAM-freeze proof.
"""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import sha
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--rtl',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);s=a.rtl.read_text()
 admission=s[s.index(' always @*begin\n  bad_data278=0;'):s.index(' assign data_command278=')]
 check=s[s.index('       case(at)',s.index('PUT:if')):s.index('       endcase',s.index('PUT:if'))+len('       endcase')]
 check=check.replace('failed<=1','bad390=1')
 text='''module plan390_tb;
 reg [7:0] header[0:15];reg sealed;reg [15:0] startpos,outlen,plen;reg [10:0] scroll_length;
 wire [16:0] decode_end305={1'b0,startpos}+{1'b0,outlen};reg bad_data278;
 reg [48:0] identity;integer at;reg [7:0] held;reg bad390;integer count390=0;
'''+admission+'''\n task decision390;begin bad390=0;
'''+check+'''\n end endtask
 task good390;begin decision390();if(bad390)$fatal(1,"valid metadata rejected at%0d",at);count390++;end endtask
 task wrong390;begin decision390();if(!bad390)$fatal(1,"metadata identity accepted at%0d",at);count390++;end endtask
 initial begin
 for(integer i=0;i<16;i++)header[i]=0;
 header[0]=2;header[1]=6;sealed=0;startpos=0;scroll_length=21;
 for(integer n=16;n<=144;n++)begin plen=n;outlen=n;#1;if(bad_data278)$fatal(1,"valid length");count390++;end
 plen=15;#1;if(!bad_data278)$fatal;plen=145;#1;if(!bad_data278)$fatal;plen=16;outlen=16;
 sealed=1;#1;if(!bad_data278)$fatal;sealed=0;startpos=1;#1;if(!bad_data278)$fatal;startpos=0;header[0]=5;#1;if(!bad_data278)$fatal;header[0]=2;count390+=5;
 for(integer trial=0;trial<16;trial++)begin
 identity={trial[0],16'(16'h10a0+trial),32'(32'h9abcdef0+trial)};
 for(at=0;at<12;at++)begin
 case(at)
 0:held=8'h4d;1:held=8'h50;2:held=1;3:held=trial%3;
 4:held=identity[48];5:held=0;
 6,7:held=identity[32+8*(at-6)+:8];
 8,9,10,11:held=identity[8*(at-8)+:8];
 endcase
 good390();if(at==3)held=3;else held=held^8'h80;wrong390();
 end
 end
 $display("PASS PLAN390 decision_checks=%0d",count390);$finish;
 end endmodule
'''
 (d/'test.sv').write_text(text,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','test.sv'],d,'vlog');out=run(q/'vsim.exe',['-c','plan390_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);m=re.search(r'PASS PLAN390 decision_checks=(\d+)',out);assert m
 (d/'result.json').write_text(json.dumps(dict(passed=True,decision_checks=int(m[1]),materialized_RTL=sha(a.rtl),test=sha(d/'test.sv'),scope=__doc__),indent=2)+'\n');print(m[0])
if __name__=='__main__':main()
