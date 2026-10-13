# SPDX-License-Identifier: MIT
"""Compare every old reader register/pin for both owners and short/board counts."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_eligibility165 import physical

def bench():
    regs='source_reset memory_reset owner_valid owner_check request_toggle ack_toggle ack_seen source_busy address_hold data_hold request_sync ack_sync remaining state chip lane reading_active check_response psram_address'.split()
    outputs='check_ready check_response_address check_data rom_ready rom_response rom_error rom_response_address rom_data psram_1ce psram_2ce psram_oe psram_we psram_bhe psram_ble'.split()
    compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"READLAST165 mismatch {n} N=%0d",N);' for n in regs+outputs)
    ports='.clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(mode),.check_request(check_request),.check_address(address),.rom_request(rom_request),.rom_address(address),.psram_data(16\'h1234)'
    return '''`timescale 1ns/1ps
module reader_last_case #(parameter N=16,parameter PHASE=0)(output reg done=0);
reg clk=0,mem_clk=0,reset=1,mode=1,check_request=0,rom_request=0,mem_run=1;
reg [21:0] address=0;
always #23.280423 clk=~clk;
initial begin #(PHASE);forever begin #2.9761905;if(mem_run)mem_clk=~mem_clk;end end
nes_rom_physical #(.READ_CYCLES(N)) dut('''+ports+''');
baseline_physical #(.READ_CYCLES(N)) refdut('''+ports+''');
integer checks=0,reads=0,cancels=0;
always @(posedge clk or posedge mem_clk or posedge reset)begin
 #0.01;
 if(!reset)begin
'''+compare+'''
 if(!dut.mr && dut.state==2 && dut.read_last!==(dut.remaining==1))$fatal(1,"READLAST165 terminal invariant N=%0d",N);
 checks++;
 end
end
task mtick;@(negedge mem_clk);#0.1;endtask
task ctick;@(negedge clk);#0.1;endtask
task fresh(input bit owner);
 mtick();reset=1;mode=owner;check_request=0;rom_request=0;
 repeat(3)ctick();reset=0;repeat(3)ctick();
endtask
task request(input integer n);
 if(mode)begin
  wait(dut.check_ready);mtick();address=n;check_request=1;mtick();check_request=0;
 end else begin
  wait(dut.rom_ready);ctick();address=n;rom_request=1;ctick();rom_request=0;
 end
endtask
initial begin
 for(integer owner=0;owner<2;owner++)begin
  fresh(owner);
  for(integer n=0;n<12;n++)begin
   request((22'h1ffff0+n*19)&22'h3fffff);
   if(mode)wait(dut.check_response);else wait(dut.rom_response);
   if((mode?dut.check_data:dut.rom_data)!==(address[0]?8'h34:8'h12))$fatal(1,"READLAST165 data");
   reads++;
  end
  for(integer phase=0;phase<N+5;phase++)begin
   fresh(owner);request(22'h200003);repeat(phase)mtick();reset=1;
   #0.1;if(!dut.psram_oe||!dut.psram_1ce||!dut.psram_2ce)$fatal(1,"READLAST165 reset pins");cancels++;
  end
 end
 fresh(1);request(22'h12345);mtick();mem_run=0;reset=1;#100;
 if(!dut.psram_oe||!dut.psram_1ce||!dut.psram_2ce||dut.read_last!==0)$fatal(1,"READLAST165 stopped reset");
 mem_run=1;repeat(5)mtick();done=1;
 $display("READLAST165 N=%0d phase=%0d checks=%0d reads=%0d cancels=%0d",N,PHASE,checks,reads,cancels);
end
endmodule
module reader_last165_tb;
wire [4:0] done;
reader_last_case #(.N(1)) a(done[0]);
reader_last_case #(.N(2)) b(done[1]);
reader_last_case #(.N(3)) c(done[2]);
reader_last_case #(.N(16)) d(done[3]);
reader_last_case #(.N(16),.PHASE(3)) e(done[4]);
initial begin wait(&done);$display("PASS READLAST165 cases=5 reads=120 cancels=126 stopped_resets=5");$finish;end
initial begin #1000000;$fatal(1,"READLAST165 watchdog");end
endmodule
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_physical.sv').read_text();new=(a.prepared/'nes_rom_physical.sv').read_text();assert new==physical(old)
    a.out.mkdir();(a.out/'candidate.sv').write_text(new)
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_physical #','module baseline_physical #',1))
    (a.out/'reader_last165_tb.sv').write_text(bench())
    def run(tool,args,label,expected=None):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if expected:assert expected in log and 'PASS READLAST165' not in log,(label,log[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','reader_last165_tb.sv'],'compile')
    args=['-c','reader_last165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    log=run('vsim',args,'equivalence');assert 'PASS READLAST165' in log
    records=re.findall(r'READLAST165 N=(\d+) phase=(\d+) checks=(\d+) reads=(\d+) cancels=(\d+)',log);assert len(records)==5
    assert sum(int(r[3]) for r in records)==120 and sum(int(r[4]) for r in records)==126
    wrong=new.replace('read_last<=remaining==2;','read_last<=remaining==1;');assert wrong!=new
    (a.out/'wrong.sv').write_text(wrong);run('vlog',['-sv','wrong.sv'],'wrong-compile');run('vsim',args,'wrong-negative','READLAST165 terminal invariant')
    result=dict(passed=True,cases=5,reads=120,cancels=126,stopped_resets=5,records=records,wrong_terminal_rejected=True,
        source_sha256=sha(a.prepared/'nes_rom_physical.sv'),reference_sha256=sha(a.baseline/'nes_rom_physical.sv'),
        scope='Register/pin equivalence for CHECK and RUN owners, READ_CYCLES1/2/3/16, two board-count phases. Constant data model for short counts; board READ16 70ns model is covered by connected eligibility test.',
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_eligibility165.py','tools/test_nes_reader_last165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
