# SPDX-License-Identifier: MIT
"""Actual M4/RTL STOP after12view reads,while the378display kernel waits VBlank."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from nes_context375 import COMMON
from nes_delta231 import ROOT,sha,once
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for f in a.reference.iterdir():
  if not f.is_file() or f.name.startswith(('arm-','arm9','actual-plans','causal','result','joint-events','calls337','metadata317')):continue
  if f.suffix.lower() in ('.sv','.hex','.palette','.cfg','.bin','.expected','.lens','.desc','.elf','.dll','.json','.c','.h','.inc','.a','.s','.ld','.csv'):shutil.copyfile(f,d/f.name)
 path=d/'joint266_tb.sv';s=path.read_text();s=once(s,'parameter real CPI=1.0;','parameter real CPI=1.0;localparam CANCEL378=1;reg waiting_stop378=0,stop_return378=0;')
 s=s.replace('PRESENT_FIRST378=907','PRESENT_FIRST378=905').replace('!NEG&&!PRENEG','!NEG&&!PRENEG&&!CANCEL378')
 s=once(s,'   bank=(~display_serial373[0])&1;tok=', '   waiting_stop378=1;bank=(~display_serial373[0])&1;tok=')
 s=once(s,'if(PRESENT378&&f>=PRESENT_FIRST378)display_tail378();', 'if(PRESENT378&&f>=PRESENT_FIRST378)begin display_tail378();stop_return378=1;end ')
 extra=r'''
 initial begin:cancel_test378
  reg [7:0] memory378[0:1023],queue378[0:1023],shadow378[0:511];
  wait(waiting_stop378);@(negedge host_clk);test_abort=1;
  wait(source_fault||flow_fault);repeat(16)@(negedge clk);wait(stop_return378);
  if(display_reads265!=12||presents378||ppu_writes378||rack||flow_retired||lease_valid||staged)$fatal(1,"cancelled display published378");
  for(integer i=0;i<1024;i++)begin memory378[i]=dut.core.memory[i];queue378[i]=dut.flow.queue.buffer[i];end
  for(integer i=0;i<512;i++)shadow378[i]=dut.core.source_shadow373[i];
  repeat(256)@(negedge host_clk);
  for(integer i=0;i<1024;i++)if(memory378[i]!==dut.core.memory[i]||queue378[i]!==dut.flow.queue.buffer[i])$fatal(1,"RAM after cancel378");
  for(integer i=0;i<512;i++)if(shadow378[i]!==dut.core.source_shadow373[i])$fatal(1,"shadow after cancel378");
  $display("PASS CANCEL378 source=%0d flow=%0d",source_fault,flow_fault);$finish;
 end
'''
 s=once(s,'endmodule',extra+'\nendmodule');path.write_text(s,newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');names=list(dict.fromkeys(json.loads((d/'manifest367.json').read_text())['sources']+list(COMMON)))
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'joint266_tb.sv'],d,'vlog')
 with (d/'arm-worker.log').open('wb') as log:
  child=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'tools/probe_nes_present378.py'),'--worker','--out',str(d),'--last','905','--irq','--plans',str(d)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   raw=run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb','-gROM_WINDOW=1','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',900);assert 'PASS CANCEL378' in raw and 'Errors: 0, Warnings: 0' in raw
  finally:
   if child.poll() is None:child.kill()
   child.wait()
 result=dict(passed=True,view_reads=12,PPU_writes=0,final_ACK=False,wait_returned_on_STOP=True,RAM_frozen_host_clocks=256,RTL={n:sha(d/n) for n in COMMON},ARM=sha(d/'output.elf'),TB=sha(path),scope='Expected STOP worker cancellation,not a normal completed-frame run.')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,PPU_writes=0,final_ACK=False)))
if __name__=='__main__':main()
