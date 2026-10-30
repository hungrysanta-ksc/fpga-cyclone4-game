# SPDX-License-Identifier: MIT
"""Differential owned pins/response/cancel and4096 unchanged admission-fault cases.

Loaded memory is seeded and PSRAM data constant; not full ROM loading/CRC,
physical electrical/IO/reset signoff or NES/SNES program boot evidence.
"""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_status495 import ROOT,sha,once
TB=r'''
`timescale 1ns/1ps
module boot495_tb;
 parameter real PHASE=0;
 reg clk=0,mem_clk=0,reset=1,read_reset=1,seed=1;
 always #23.280423 clk=~clk;
 initial begin #(PHASE);forever #5.952381 mem_clk=~mem_clk;end
 reg check_enable=0,check_request=0,start=0;reg[18:0]check_address=0;
 wire ready,response,fault,rr,rs,rf;wire[18:0]address,ra;wire[7:0]data,rd;
 wire[21:0]pa,rpa;wire ce1,ce2,oe,we,bhe,ble,rce1,rce2,roe,rwe,rbhe,rble;
 wire[15:0]pd=16'ha55a,rpd=16'ha55a;
 nes_rom_boot dut(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset),
  .check_enable(check_enable),.check_request(check_request),.check_address(check_address),
  .check_ready(ready),.check_response(response),.check_fault(fault),.check_response_address(address),.check_data(data),
  .load_begin(1'b0),.load_chr32(1'b0),.load_valid(1'b0),.load_end(1'b0),.start(start),.stop(1'b0),.load_data(8'd0),
  .rom_request(1'b0),.rom_address(22'd0),.psram_address(pa),.psram_1ce(ce1),.psram_2ce(ce2),.psram_oe(oe),.psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data(pd));
 baseline_boot495 refdut(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(read_reset),
  .check_enable(check_enable),.check_request(check_request),.check_address(check_address),
  .check_ready(rr),.check_response(rs),.check_fault(rf),.check_response_address(ra),.check_data(rd),
  .load_begin(1'b0),.load_chr32(1'b0),.load_valid(1'b0),.load_end(1'b0),.start(start),.stop(1'b0),.load_data(8'd0),
  .rom_request(1'b0),.rom_address(22'd0),.psram_address(rpa),.psram_1ce(rce1),.psram_2ce(rce2),.psram_oe(roe),.psram_we(rwe),.psram_bhe(rbhe),.psram_ble(rble),.psram_data(rpd));
 integer cycles=0,reads=0,guards=0;
 always @(negedge mem_clk)begin
  #0.001;
  if(!reset)begin
   if({ready,response,fault,ce1,ce2,oe,we,bhe,ble}!=={rr,rs,rf,rce1,rce2,roe,rwe,rbhe,rble})$fatal(1,"BOOT495 flags/pins");
   if((!ce1||!ce2||!oe||!rce1||!rce2||!roe)&&pa!==rpa)$fatal(1,"BOOT495 owned address");
   if(response&&{address,data}!=={ra,rd})$fatal(1,"BOOT495 response");cycles++;
  end
 end
 task init;
  begin reset=1;check_request=0;check_enable=0;start=0;seed=1;
   repeat(4)@(negedge mem_clk);reset=0;check_enable=1;
   repeat(8)@(negedge mem_clk);if(!ready)$fatal(1,"BOOT495 init");end
 endtask
 task kick(input[18:0]a);
  begin while(!ready)@(negedge mem_clk);check_address=a;check_request=1;@(negedge mem_clk);check_request=0;end
 endtask
 task read_one(input[18:0]a);
  integer n;begin kick(a);n=0;while(!response&&n<40)begin @(negedge mem_clk);n++;end
   if(!response||address!==a||data!==(a[0]?8'h5a:8'ha5)||fault)$fatal(1,"BOOT495 read");reads++;
   @(negedge mem_clk);if(response)$fatal(1,"BOOT495 duplicate");end
 endtask
 initial begin
  force dut.check_loaded=seed;force refdut.check_loaded=seed;
  init;
  for(integer h=0;h<3;h++)for(integer i=0;i<16;i++)read_one((h<<17)|((i*8191)&19'h1ffff));
  for(integer i=0;i<4;i++)begin init;kick(19'h60000+i);
   repeat(3)@(negedge mem_clk);if(!fault||!ce1||!ce2||!oe||response)$fatal(1,"BOOT495 invalid range");guards++;end
  init;kick(0);check_request=1;@(negedge mem_clk);check_request=0;
  repeat(3)@(negedge mem_clk);if(!fault||response||!oe)$fatal(1,"BOOT495 busy request");guards++;
  init;check_enable=0;check_request=1;@(negedge mem_clk);check_request=0;
  repeat(3)@(negedge mem_clk);if(!fault||response||!oe)$fatal(1,"BOOT495 owner request");guards++;
  init;seed=0;@(negedge mem_clk);if(!fault||response||!oe)$fatal(1,"BOOT495 unloaded");guards++;
  init;start=1;@(negedge mem_clk);start=0;repeat(3)@(negedge mem_clk);
  if(!fault||response||!oe)$fatal(1,"BOOT495 START conflict");guards++;
  for(integer phase=1;phase<=4;phase++)begin
   init;kick(0);wait(dut.reader.state==phase);#0.1;reset=1;#0.1;
   if(!ce1||!ce2||!oe||response)$fatal(1,"BOOT495 cancel pins");
   repeat(3)@(negedge mem_clk);check_enable=0;reset=0;
   repeat(8)@(negedge mem_clk);if(response)$fatal(1,"BOOT495 stale reply");guards++;
  end
  $display("PASS BOOT495 reads=%0d guards=%0d cycles=%0d",reads,guards,cycles);$finish;
 end
 initial begin #1000000;$fatal(1,"BOOT495 watchdog");end
endmodule
'''
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['old','new','out','bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
    for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:shutil.copyfile(a.new/n,a.out/n)
    (a.out/'baseline.sv').write_text(once((a.old/'nes_rom_boot.sv').read_text(),'module nes_rom_boot(','module baseline_boot495('))
    (a.out/'bench.sv').write_text(TB)
    q=(ROOT/'tests/nes-functional/boot135_diff_tb.sv').read_text().replace('[16:0]','[18:0]').replace('baseline_boot135','baseline_boot495').replace('dut.loaded=in_loaded','dut.check_loaded=in_loaded')
    (a.out/'sticky.sv').write_text(q)
    def run(label,cmd,negative=False):
        with (a.out/(label+'.log')).open('wb')as f:r=subprocess.run([str(a.bin/(cmd[0]+'.exe')),*cmd[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        text=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert '** Fatal: BOOT495'in text,text[-2500:]
        else:assert not r.returncode and not re.search(r'\*\* (Error|Fatal):',text),text[-3500:]
        return text
    run('vlib',['vlib','work']);run('compile',['vlog','-sv','nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv','baseline.sv','bench.sv','sticky.sv'])
    rows=[]
    for name,top,phase in [('normal','boot495_tb',0),('phase','boot495_tb',3.5),('sticky','boot135_diff_tb',None)]:
        s=run(name,['vsim','-c',top,*([f'-gPHASE={phase}']if phase is not None else []),'-do','onerror {quit -code 1};run -all;quit -f']);assert 'PASS'in s;rows.append({'name':name,'passed':True})
    bad=once((a.new/'nes_rom_boot.sv').read_text(),'!raw_check_ready || !address_valid','!raw_check_ready')
    (a.out/'wrong.sv').write_text(bad);run('negative-compile',['vlog','-sv','wrong.sv']);run('negative',['vsim','-c','boot495_tb','-do','onerror {quit -code 1};run -all;quit -f'],True)
    r={'passed':True,'scope':__doc__,'rows':rows,'valid_reads_each_phase':48,'cancel_fault_cases_each_phase':12,'sticky_cases':4096,'negative_controls':1,'old_SHA256':sha(a.old/'nes_rom_boot.sv'),'new_SHA256':sha(a.new/'nes_rom_boot.sv')}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
