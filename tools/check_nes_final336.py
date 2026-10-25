# SPDX-License-Identifier: MIT
"""Public unit ABI, independent raw0/final checks, private STOP and cold reset."""
import inspect
import check_nes_final332 as old


if __name__=='__main__':
    s=inspect.getsource(old.main)
    a=s.index('  begin wait(ready);@(negedge clk);first=f;count=n;')
    b=s.index('\n endtask',a)
    s=s[:a]+'''  begin
   for(integer j=f;j<(end_mode?n:f+n);j++)begin
    wait(ready);@(negedge clk);first=j;count=1;map_range=m;descriptor=end_mode;range_valid=1;
    @(negedge clk);range_valid=0;wait(ready);@(negedge clk);if(fault)$fatal(1,"unit fault336");
   end
  end'''+s[b:]
    s=s.replace('if(done!=7)$fatal(1,"case count");$finish;', '''if(done!=7)$fatal(1,"case count");
  reset=1;repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  for(integer j=0;j<1024;j++)if(memory[j]!==0)$fatal(1,"cold reset memory336");
  grant=1;@(negedge clk);grant=0;wait(context_ready);@(negedge clk);
  for(integer j=0;j<32;j++)begin context_valid=1;context_data=context_bytes[j];@(negedge clk);end
  context_valid=0;beg=1;@(negedge clk);beg=0;wait(ready);@(negedge clk);
  first=1152;count=1;map_range=0;range_valid=1;@(negedge clk);range_valid=0;
  wait(dut.state==dut.V_PREAD);@(negedge clk);abort_source=1;
  repeat(8)@(negedge clk);
  if(!fault||sealed||initialized||memory[656]!==1||memory[144]!==0)$fatal(1,"private cancel336");
  repeat(256)@(negedge clk);if(memory[656]!==1||memory[144]!==0||we)$fatal(1,"STOP freeze336");
  reset=1;abort_source=0;repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  for(integer j=0;j<1024;j++)if(memory[j]!==0)$fatal(1,"private leak after reset336");
  if(dut.v_initialized!==0||sealed)$fatal(1,"bank publication after reset336");
  $display("PASS PRIVATE336 STOP freeze both-bank cold reset");$finish;''')
    s=s.replace('assert raw.count(\'PASS FINAL332 raw0 case=\')==7', "assert raw.count('PASS FINAL332 raw0 case=')==7 and 'PASS PRIVATE336' in raw")
    s=s.replace('cases=7,RTL_sha256', 'cases=8,RTL_sha256')
    s=s.replace("print('PASS raw0 final RAM job 7 cases')", "print('PASS raw0 final RAM job 7 cases + private STOP/reset')")
    ns=dict(old.__dict__);ns.update(__file__=__file__,__doc__=__doc__);exec(compile(s,'final336','exec'),ns);ns['main']()
