# SPDX-License-Identifier: MIT
"""Same-edge cause equivalence and existing actual SPI/reader regression."""
import argparse,json,os,re,subprocess
from pathlib import Path
from nes_game147 import ROOT,sha
from test_nes_checkstate181 import STATE,connected
from prepare_nes_nrom454_compare import transform
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
(d/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(d/'candidate.sv').write_text(new)
for n in ('nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv'):(d/n).write_bytes((a.candidate/n).read_bytes())
seq=connected();assert seq.count("wire_rx[55:48]!==8'h74")==1;seq=seq.replace("wire_rx[55:48]!==8'h74","wire_rx[55:48]!==8'h78");line='if(dut.raw_causes!==refdut.raw_causes)$fatal(1,"STATE181 sequential raw_causes");';assert seq.count(line)==1;seq=seq.replace(line,'if(dut.sampled && dut.sampled_causes!==refdut.sampled_causes)$fatal(1,"NROM454 sampled causes");');(d/'connected_tb.sv').write_text(seq)
seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in STATE)
inputs='mem_clk reset SPI_SS SPI_SCK SPI_MOSI load_ready loaded run_enable boot_fault boot_error loaded_bytes check_ready check_response check_fault check_response_address check_data'.split();ports=','.join('.'+n+'('+n+')' for n in inputs)
tb='''`timescale 1ns/1ps
module cause454_tb;
reg mem_clk=0,reset=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
reg load_ready=1,loaded=1,run_enable=0,boot_fault=0;reg [3:0] boot_error=0;reg [18:0] loaded_bytes=0;
reg check_ready=1,check_response=0,check_fault=0;reg [18:0] check_response_address=0;reg [7:0] check_data=0;
nes_rom_spi_check dut('''+ports+''');baseline_check165 refdut('''+ports+''');integer count=0;
task one(input [7:0] command,input [18:0] length,input [23:0] address,input [3:0] flags);
begin
'''+seed+'''
 dut.raw_len_command=0;dut.raw_end_command=0;dut.raw_len_lo_diff=0;dut.raw_len_hi_diff=0;
 reset=0;check_fault=0;boot_fault=0;check_response=0;SPI_SS=1;dut.byte_last=0;refdut.byte_last=0;
 dut.ss_sync=3;refdut.ss_sync=3;dut.ss_previous=0;refdut.ss_previous=0;
 dut.command=command;refdut.command=command;dut.offset=address;refdut.offset=address;loaded_bytes=length;
 dut.offset_zero_command=command==8'h60;refdut.offset_zero_command=dut.offset_zero_command;
 dut.offset_length_command=(command>=8'h61 && command<=8'h64);refdut.offset_length_command=dut.offset_length_command;
 dut.check_enable=flags[0];refdut.check_enable=flags[0];dut.check_busy=flags[1];refdut.check_busy=flags[1];dut.check_done=flags[2];refdut.check_done=flags[2];dut.verified=flags[3];refdut.verified=flags[3];
 dut.offset_matches_next=1;refdut.offset_matches_next=1;dut.next_below_length=1;refdut.next_below_length=1;dut.next_matches_length=1;refdut.next_matches_length=1;
 #1;mem_clk=1;#1;if(!dut.sampled||!refdut.sampled||dut.sampled_causes!==refdut.sampled_causes)$fatal(1,"C0 mismatch cmd=%h len=%h address=%h flags=%h",command,length,address,flags);
 mem_clk=0;loaded_bytes=~length;dut.offset=~address;refdut.offset=~address;dut.command=8'h60;refdut.command=8'h60;#1;mem_clk=1;#1;
 if(dut.pending_causes!==refdut.pending_causes)$fatal(1,"C1 mismatch");mem_clk=0;#1;count++;
end endtask
initial begin
 for(integer c=0;c<11;c++)for(integer f=0;f<16;f++)for(integer i=0;i<25;i++)for(integer l=0;l<3;l++)
  one(8'h60+c,l==0?19'd0:l==1?19'h3ffff:19'h60000,({5'd0,(l==0?19'd0:l==1?19'h3ffff:19'h60000)}) ^ (i==24?24'd0:(24'd1<<i)),f);
 $display("PASS NROM454 cause cases=%0d",count);$finish;
end
endmodule
''';(d/'cause_tb.sv').write_text(tb)
def run(tool,args,label):
 with(d/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
 s=(d/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','cause_tb.sv','connected_tb.sv'],'compile')
sim=lambda top:['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
s=run('vsim',sim('cause454_tb'),'causes');assert 'PASS NROM454 cause cases=13200' in s
s=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in s and 'acks=7 corruptions=19 cancels=72 overlaps=2' in s
needle="raw_len_hi_diff<=offset[23:12]!={5'd0,loaded_bytes[18:12]};";assert new.count(needle)==1;(d/'negative.sv').write_text(new.replace(needle,"raw_len_hi_diff<=1'b0;"))
run('vlog',['-sv','negative.sv'],'negative-compile')
with (d/'negative.log').open('wb') as f:q=subprocess.run([str(a.questa_bin/'vsim.exe'),*sim('cause454_tb')],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
assert 'C0 mismatch' in (d/'negative.log').read_text(errors='replace'),'upper-length negative was not detected'
r={'passed':True,'upper_mismatch_negative_detected':True,'cause_cases':13200,'actual_spi_regression':re.search(r'PASS TAG165[^\r\n]+',s)[0],'candidate_sha256':sha(d/'candidate.sv'),'reference_sha256':sha(d/'reference.sv'),'scope':'C0/C1 sampled causes plus existing modeled SPI/boot/reader test; no full board or physical hardware'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
