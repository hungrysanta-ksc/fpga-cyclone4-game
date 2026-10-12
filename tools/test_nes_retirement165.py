# SPDX-License-Identifier: MIT
"""Every 19-bit increment and retirement fault/priority states vs prior decoder."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_retire165 import retire

REGS='check_busy check_done verified check_next next_carry8 checked_data ss_sync sck_sync mosi_sync ss_previous sck_previous miso_hold bit_count byte_count shift command arg arg_not received_crc tail crc offset offset_matches_next next_below_length next_matches_length pending pending_command pending_header_error pending_causes pending_arg snapshot load_begin load_chr32 load_valid load_end start stop load_data fault error_code check_enable check_request'.split()

def bench():
    inputs='mem_clk reset SPI_SS SPI_SCK SPI_MOSI load_ready loaded run_enable boot_fault boot_error loaded_bytes check_ready check_response check_fault check_response_address check_data'.split()
    ports=','.join('.'+n+'('+n+')' for n in inputs)
    seed='\n'.join('dut.'+n+"='0; refdut."+n+"='0;" for n in REGS)
    compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"CHECK165 mismatch {n} n=%h flags=%h op=%h",n,f,op);' for n in REGS)
    return '''`timescale 1ns/1ps
module check165_tb;
reg mem_clk=0,reset=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
reg load_ready=1,loaded=1,run_enable=0,boot_fault=0;
reg [3:0] boot_error=0;reg [18:0] loaded_bytes=19'h60000;
reg check_ready=1,check_response=0,check_fault=0;
reg [18:0] check_response_address=0;reg [7:0] check_data=8'ha6;
nes_rom_spi_check dut('''+ports+''');
baseline_check165 refdut('''+ports+''');
integer count=0;
task step(input [18:0] n,input [10:0] f,input [3:0] op,input carry);
begin
'''+seed+'''
 dut.check_next=n;refdut.check_next=n;
 dut.next_carry8=carry;refdut.next_carry8=carry;
 dut.pending=1;refdut.pending=1;dut.pending_command=op;refdut.pending_command=op;
 dut.pending_arg=8'h96;refdut.pending_arg=8'h96;
 dut.ss_sync=f[5]?0:3;refdut.ss_sync=dut.ss_sync;
 dut.ss_previous=1;refdut.ss_previous=1;
 reset=f[10];check_fault=f[0];boot_fault=f[1];check_response=f[2];
 dut.check_enable=!f[3];refdut.check_enable=dut.check_enable;
 dut.check_busy=!f[4];refdut.check_busy=dut.check_busy;
 dut.fault=f[6];refdut.fault=f[6];
 dut.pending_header_error=f[7]?4'd2:0;refdut.pending_header_error=dut.pending_header_error;
 dut.pending_causes=f[8]?5'b10000:0;refdut.pending_causes=dut.pending_causes;
 check_response_address=f[9]?(n^19'h40001):n;
 #1;mem_clk=1;#1;
'''+compare+'''
 mem_clk=0;reset=0;#1;count++;
end endtask
initial begin
 // Exhaustive counter values at normal ACK retirement, with actual carry.
 for(integer n=0;n<524288;n++)step(n,0,8,(&n[7:0]));
 // All fault/lifecycle/response/overlap/reset flags, all queued commands,
 // and eight counter/carry patterns, including inconsistent injected carries.
 for(integer f=0;f<2048;f++)for(integer op=0;op<16;op++)for(integer p=0;p<8;p++)
  step((19'h7ffff >> p),f,op,p[0]);
 $display("PASS CHECK165 states=%0d",count);$finish;
end
endmodule
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    before=(a.baseline/'nes_rom_spi.sv').read_text();after=(a.prepared/'nes_rom_spi.sv').read_text()
    assert after==retire(before);a.out.mkdir()
    (a.out/'baseline.sv').write_text(before.replace('module nes_rom_spi_check(','module baseline_check165(',1))
    (a.out/'candidate.sv').write_text(after);(a.out/'check165_tb.sv').write_text(bench())
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        s=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert 'CHECK165 mismatch check_next' in s and 'PASS CHECK165' not in s
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),(label,s[-2000:])
        return s
    run('vlib',['work'],'vlib')
    run('vlog',['-sv','baseline.sv','candidate.sv','check165_tb.sv'],'compile')
    args=['-c','check165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    assert 'PASS CHECK165 states=786432' in run('vsim',args,'equivalence')
    needle='&& !check_fault &&';assert after.count(needle)==1
    (a.out/'wrong-carry.sv').write_text(after.replace(needle,"&& 1'b1 &&"))
    run('vlog',['-sv','wrong-carry.sv'],'negative-compile');run('vsim',args,'negative',True)
    result=dict(passed=True,states=786432,all_counter_values=524288,priority_states=262144,wrong_fault_gate_rejected=True,
        source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_retire165.py','tools/test_nes_retirement165.py','tools/test_nes_check165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
