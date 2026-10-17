# SPDX-License-Identifier: MIT
"""Observation equivalence for four private samples, plus explicit C0/C1 tests."""
import inspect
import test_nes_counter224 as prior
from nes_counter224_sample import transform,replace

PRIVATE=['raw_loaded','raw_run','raw_ready','raw_load_ready']
def qualified(s):
 for n in PRIVATE:
  needle=f'if(dut.{n}!==refdut.{n})'
  assert needle in s
  s=s.replace(needle,f'if((dut.sampled||refdut.sampled)&&dut.{n}!==refdut.{n})')
 return s

def bench():
 s=qualified(prior.bench())
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in prior.STATE)
 task='''integer sample_cases=0;
 task sample_case(input [3:0] at_c0,input [3:0] at_c1,input [7:0] cmd);
 reg [4:0] expected;
 begin
 '''+seed+'''
 reset=0;check_fault=0;boot_fault=0;check_response=0;
 SPI_SS=1;SPI_SCK=0;dut.byte_last=0;refdut.byte_last=0;
 dut.ss_sync=3;refdut.ss_sync=3;dut.ss_previous=0;refdut.ss_previous=0;
 dut.command=cmd;refdut.command=cmd;
 // Valid lifecycle prerequisites keep unrelated causes from masking the
 // external eligibility bits under test (notably START's verified guard).
 dut.check_enable=cmd!=8'h66;refdut.check_enable=dut.check_enable;
 dut.verified=1;refdut.verified=1;
 dut.offset_matches_next=1;refdut.offset_matches_next=1;
 dut.next_below_length=1;refdut.next_below_length=1;
 {loaded,run_enable,check_ready,load_ready}=at_c0;
 #1;mem_clk=1;#1;
 if(!dut.sampled||!refdut.sampled)$fatal(1,"SAMPLE224 C0 not admitted");
 if({dut.raw_loaded,dut.raw_run,dut.raw_ready,dut.raw_load_ready}!==at_c0)$fatal(1,"SAMPLE224 wrong capture edge");
 expected=refdut.sampled_causes;
 mem_clk=0;#1;{loaded,run_enable,check_ready,load_ready}=at_c1;
 #1;mem_clk=1;#1;
 if(dut.pending_causes!==expected||dut.pending_causes!==refdut.pending_causes)$fatal(1,"SAMPLE224 live C1 leaked into C0 causes");
 mem_clk=0;#1;sample_cases++;
 end endtask
 '''
 s=replace(s,'initial begin\n',task+'''initial begin
 for(integer a=0;a<16;a++)for(integer b=0;b<16;b++)begin
  sample_case(a,b,8'h61);sample_case(a,b,8'h63);sample_case(a,b,8'h66);sample_case(a,b,8'h67);
 end
 $display("PASS SAMPLE224 cases=%0d",sample_cases);
 loaded=1;run_enable=0;check_ready=1;load_ready=1;
 ''')
 return s

def connected():return qualified(prior.connected())

s=inspect.getsource(prior.main)
s=replace(s,"assert 'PASS COUNTER224 cases=491520 edges=983040' in log", "assert 'PASS SAMPLE224 cases=1024' in log and 'PASS COUNTER224 cases=491520 edges=983040' in log")
s=replace(s," names=['tools/nes_counter224.py'", " names=['tools/nes_counter224_sample.py','tools/test_nes_counter224_sample.py','tools/nes_counter224.py'")
s=replace(s," result=dict(passed=True", " result=dict(sample_cases=1024,private_sample_comparison='Only at original C0 publication; all consumed state/output and counter effects always compared',passed=True")
s=replace(s,"('pending','!fault && pending && ss_sync[1]','!fault && ss_sync[1]')]", "('pending','!fault && pending && ss_sync[1]','!fault && ss_sync[1]'),('live-run','raw_causes[4] || (raw_select[3] && (!raw_loaded || raw_run)),','raw_causes[4] || (raw_select[3] && (!raw_loaded || run_enable)),')]")
s=replace(s,"assert 'COUNTER224 mismatch' in log and 'PASS COUNTER224' not in log", "assert ('COUNTER224 mismatch' in log or 'SAMPLE224 live C1 leaked' in log) and 'PASS COUNTER224' not in log")
s=replace(s,"'missing pending gate']", "'missing pending gate','live C1 substituted for sampled C0 RUN']")
ns=dict(prior.__dict__);ns.update(transform=transform,bench=bench,connected=connected);ns['__file__']=__file__
exec(compile(s,'counter224-sample','exec'),ns)
if __name__=='__main__':ns['main']()
