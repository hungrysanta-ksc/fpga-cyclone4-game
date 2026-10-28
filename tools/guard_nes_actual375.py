# SPDX-License-Identifier: MIT
"""Actual ARM/SPI error injection for cold token,STOP and early final ACK375."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
from nes_context375 import COMMON,materialize
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--reference',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--cases',default='0,1,2,3');a=p.parse_args();base=a.out.resolve();base.mkdir(parents=True,exist_ok=False);q=Path('C:/altera_standard/25.1std/questa_fse/win64');cases=[]
 for case in map(int,a.cases.split(',')):
  d=base/f'case{case}';d.mkdir()
  for f in a.reference.iterdir():
   if not f.is_file() or f.name.startswith(('arm-','arm9','actual-plans','causal','result','joint-events','calls337','metadata317')):continue
   if f.suffix.lower() in ('.sv','.hex','.palette','.cfg','.bin','.expected','.lens','.desc','.elf','.dll','.json','.c','.h','.inc','.a','.s','.ld','.csv'):shutil.copyfile(f,d/f.name)
  materialize(d);tb=(d/'joint266_tb.sv').read_text();needle=' parameter real PHASE=3.5;';assert needle in tb
  tb=tb.replace(needle,f' parameter integer BAD375={case};reg injected375=0,saw_context_fault375=0;\n'+needle)
  tb=tb.replace('!NEG&&!PRENEG','!NEG&&!PRENEG&&!injected375')
  needle='integer i,b;begin\n   #2000;ss=0;';assert needle in tb
  tb=tb.replace(needle,'''integer i,b;reg [15:0] corrupt_crc375;begin
   if((BAD375==0||BAD375==1)&&!injected375&&tx[0]==8'he1&&tx[1]==(BAD375==0?7:14))begin
    tx[20]=tx[20]^8'h01;corrupt_crc375=16'hffff;
    for(integer j375=0;j375<size-2;j375++)corrupt_crc375=c16(corrupt_crc375,tx[j375]);
    tx[size-2]=corrupt_crc375[15:8];tx[size-1]=corrupt_crc375[7:0];injected375=1;
   end
   #2000;ss=0;''')
  extra=r'''
 always @(posedge host_clk)if(dut.flow.ctx_fault375)saw_context_fault375<=1;
 initial begin : actual_negative375
  reg [7:0] frozen375[0:1023],qfreeze375[0:1023];reg [7:0] shadow375[0:511];
  if(BAD375<2)wait(injected375);
  else if(BAD375==2)begin
   wait(dut.flow.ctx_check_busy375);@(negedge host_clk);test_abort=1;injected375=1;
   disable bus263;bus_read=1;bus_write=1;
  end else begin
   wait(dut.flow.state==dut.flow.DMA&&staged);injected375=1;disable bus263;bus_read=1;bus_write=1;
   token261(dut.flow.chunk_token);wr261(24'h006058,8'h5a);injected375=1;
  end
  wait(source_fault||flow_fault);disable bus263;bus_read=1;bus_write=1;
  repeat(16)@(negedge clk);
  if(BAD375<2&&!saw_context_fault375)$fatal(1,"wrong rejection cause375");
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"completion after actual negative375");
  for(integer j=0;j<1024;j++)begin frozen375[j]=dut.core.memory[j];qfreeze375[j]=dut.flow.queue.buffer[j];end
  for(integer j=0;j<512;j++)shadow375[j]=dut.core.source_shadow373[j];
  repeat(256)@(negedge host_clk);
  for(integer j=0;j<1024;j++)if(frozen375[j]!==dut.core.memory[j]||qfreeze375[j]!==dut.flow.queue.buffer[j])$fatal(1,"RAM changed after negative375");
  for(integer j=0;j<512;j++)if(shadow375[j]!==dut.core.source_shadow373[j])$fatal(1,"source shadow changed after negative375");
  $display("PASS ACTUAL_NEGATIVE375 case=%0d source=%0d flow=%0d context=%0d",BAD375,source_fault,flow_fault,saw_context_fault375);$finish;
 end
'''
  tb=tb.replace(' task clear_output;',extra+'\n task clear_output;');(d/'joint266_tb.sv').write_text(tb,newline='\n')
  names=list(dict.fromkeys(json.loads((d/'manifest367.json').read_text())['sources']+list(COMMON)))
  run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'joint266_tb.sv'],d,'vlog')
  with (d/'arm-worker.log').open('wb') as log:
   child=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'tools/probe_nes_context375.py'),'--worker','--out',str(d),'--last','905','--irq','--plans',str(d)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:
    out=run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb','-gROM_WINDOW=1','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',900)
    assert f'PASS ACTUAL_NEGATIVE375 case={case}' in out
   finally:
    if child.poll() is None:child.kill()
    child.wait()
  row=dict(case=case,passed=True,RTL={n:sha(d/n) for n in COMMON},tb=sha(d/'joint266_tb.sv'),ARM=sha(d/'output.elf'),worker_cancelled_after_expected_rejection=True)
  (d/'negative-result.json').write_text(json.dumps(row,indent=2)+'\n');cases.append(row)
 result=dict(passed=True,cases=cases,scope='Actual compiled ARM/SPI with CRC-valid token corruption,STOP during check,early final ACK;not a normal completed frame run.')
 (base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(cases))))
if __name__=='__main__':main()
