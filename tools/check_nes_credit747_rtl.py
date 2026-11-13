# SPDX-License-Identifier: MIT
"""Measure the board E0 latch against MMIO ACK publication and checked retirement."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from nes_raw506 import once,sha


def run(a):
    a.out.mkdir(exist_ok=False,parents=True)
    files=['nes_sink_spi165.sv','nes_sink_bridge165.sv','nes_sink_bus165.sv','nes_domain_reset124.sv','sink-program.hex']
    for f in files:shutil.copyfile(a.board/f,a.out/f)
    bench=Path('tests/nes-functional/progress680_tb.sv').read_text()
    bench=once(bench,'module progress680_tb;', 'module credit747_tb;')
    bench=once(bench,' initial begin\n','''
 bit trace747=0;
 realtime snap747,return747,publish747,wire747;
 always @(posedge clk) if(trace747)begin
  if(dut.endpoint.ack_publish) publish747=$realtime;
  if(!dut.endpoint.ss[1] && dut.endpoint.sck[1] && !dut.endpoint.prev_sck &&
      dut.endpoint.bit_count==7 && dut.endpoint.byte_count==0) snap747=$realtime;
 end
 always @(dut.endpoint.retired) if(trace747 && dut.endpoint.retired==1) return747=$realtime;
 initial begin\n''')
    bench=once(bench,'  #(PHASE);restart();','''
  #(PHASE);
  for(int delay747=0;delay747<=800;delay747+=20)begin
   restart();prepare(0);transfer(19);
   for(int k=0;k<12;k++)write_byte('h6010+k,ack[k]);
   trace747=1;snap747=0;return747=0;publish747=0;
   fork status();begin
    wait(!ss);@(posedge sck);wire747=$realtime;
    repeat(5)@(posedge sck);#(delay747);write_byte('h601c,'ha5);
   end join
   trace747=0;
   if(!snap747||!return747||!publish747||return747<=publish747)$fatal(1,"missing edges");
   if({rx[3],rx[4]}!=1 || {rx[5],rx[6]}!=(return747<snap747))$fatal(1,"stale or torn counter");
   if(return747<snap747)begin
    for(int k=0;k<12;k++)if(rx[7+k]!==ack[k])$fatal(1,"identity");
   end
   $display("R747 %0d %.3f %.3f %.3f %.3f %0d",delay747,wire747,publish747,return747,snap747,rx[6]);
   expect_flags(2);
   if({rx[5],rx[6]}!=1)$fatal(1,"next status");
  end
  restart();''')
    (a.out/'credit747_tb.sv').write_text(bench,newline='\n')
    def cmd(tool,args,log):
        with (a.out/log).open('wb') as f:
            subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=150)
    cmd('vlib',['work'],'vlib.log')
    cmd('vlog',['-sv',*files[:4],'credit747_tb.sv'],'vlog.log')
    runs={}
    for phase in (0,8):
        name=f'vsim{phase}.log'
        cmd('vsim',['-c','credit747_tb',f'-gPHASE={phase}','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'],name)
        log=(a.out/name).read_text()
        rows=[list(map(float,m.split())) for m in re.findall(r'R747 ([0-9. ]+)',log)]
        assert len(rows)==41 and {r[-1] for r in rows}=={0,1} and 'PASS680' in log
        runs[phase]=rows
    (a.out/'result.json').write_text(json.dumps(dict(runs=runs,columns=['offset_ns','first_SCK_rise_ns','ACK_publish_ns',
        'checked_retired_ns','snapshot_ns','returned_credit'],pins={f:sha(a.out/f) for f in files},testbench=sha(a.out/'credit747_tb.sv')),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('bin','board','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
