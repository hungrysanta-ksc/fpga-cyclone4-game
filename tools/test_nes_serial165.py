# SPDX-License-Identifier: MIT
"""Compare old indexed snapshot and serial snapshot at every memory edge."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from nes_retire165 import spi

def bench():
    inputs='mem_clk reset SPI_SS SPI_SCK SPI_MOSI load_ready loaded run_enable boot_fault boot_error loaded_bytes check_ready check_response check_fault check_response_address check_data'.split()
    ports=','.join(f'.{n}({n})' for n in inputs)
    outputs='spi_miso spi_selected load_begin load_chr32 load_valid load_end start stop load_data fault error_code check_enable check_request check_address'.split()
    comparisons='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"SERIAL165 {n} frame=%0d bits=%0d",frames,bits);' for n in outputs)
    deposit='\n'.join(f'dut.{n}=random_value;refdut.{n}=dut.{n};random_value={{random_value[30:0],random_value[31]^random_value[21]^random_value[1]^random_value[0]}};' for n in ['check_busy','check_done','verified','check_next','checked_data','fault','error_code','check_enable'])
    return '''`timescale 1ns/1ps
module serial165_tb;
reg mem_clk=0,reset=1,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
always #2.976 mem_clk=~mem_clk;
reg load_ready=0,loaded=0,run_enable=0,boot_fault=0;
reg [3:0] boot_error=0;reg [18:0] loaded_bytes=0;
reg check_ready=0,check_response=0,check_fault=0;
reg [18:0] check_response_address=0;reg [7:0] check_data=0;
integer frames=0,bits=0,edges=0;reg [31:0] random_value=32'hbeef1271;
nes_rom_spi_check dut('''+ports+''');
baseline_serial165 refdut('''+ports+''');
always @(posedge mem_clk)begin #0.001;
 if(!reset)begin
'''+comparisons+'''
 edges++;
 end
end
task send_bit(input bit b);
 SPI_MOSI=b;#190.476;SPI_SCK=1;#190.476;SPI_SCK=0;bits++;
endtask
reg [7:0] command;
initial begin
 repeat(5)@(negedge mem_clk);reset=0;
 for(integer trial=0;trial<256;trial++)begin
  @(negedge mem_clk);reset=1;SPI_SS=1;SPI_SCK=0;
  repeat(5)@(negedge mem_clk);reset=0;
  {load_ready,loaded,run_enable,boot_fault,boot_error,loaded_bytes}=random_value;
'''+deposit+'''
  // Coherent snapshots with varied status/data/address/error bits; overlong
  // and truncated frames also exercise the default-zero reply interval.
  command=trial[0]?8'h65:8'h6a;
  #2000;SPI_SS=0;#2000;
  for(integer b=7;b>=0;b--)send_bit(command[b]);
  for(integer b=0;b<(trial%4==0?80:trial%4==1?21:56);b++)begin
   send_bit(random_value[b%32]);
   // Change live inputs mid-frame: both replies must keep the captured image.
   loaded_bytes=loaded_bytes^19'h55555;load_ready=!load_ready;boot_error=boot_error+1;
  end
  #2000;SPI_SS=1;#2000;frames++;
 end
 $display("PASS SERIAL165 frames=%0d bits=%0d edges=%0d",frames,bits,edges);$finish;
end
initial begin #20000000;$fatal(1,"SERIAL165 timeout");end
endmodule
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new==spi(old)
    a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_serial165(',1))
    (a.out/'candidate.sv').write_text(new);(a.out/'serial165_tb.sv').write_text(bench())
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert '** Fatal: SERIAL165 spi_miso' in log and 'PASS SERIAL165' not in log
        else:assert r.returncode==0 and '** Fatal:' not in log and '** Error:' not in log,(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','serial165_tb.sv'],'compile')
    args=['-c','serial165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    log=run('vsim',args,'equivalence');assert 'PASS SERIAL165 frames=256' in log
    (a.out/'wrong-bit.sv').write_text(new.replace('?snapshot[55]:', '?snapshot[54]:'))
    run('vlog',['-sv','wrong-bit.sv'],'negative-compile');run('vsim',args,'negative',True)
    import re
    summary=re.search('PASS SERIAL165[^\r\n]+',log)[0]
    result=dict(passed=True,summary=summary,frames=256,wrong_bit_rejected=True,source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_retire165.py','tools/test_nes_serial165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(summary)
if __name__=='__main__':main()
