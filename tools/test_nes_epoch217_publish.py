# SPDX-License-Identifier: MIT
"""Serial equivalence, one-edge Gray publish, and fail-closed stopped publisher."""
import inspect
import test_nes_epoch217 as prior
from nes_epoch217_publish import transform
from nes_board204 import replace

s=inspect.getsource(prior.main).replace('nes-loader217/source02','nes-loader217/source04')
inject='''
 s=replace(s,'always #2.976 mem_clk=!mem_clk;','reg run_mem=1;always #2.976 if(run_mem)mem_clk=!mem_clk;')
 end='  $display("PASS EPOCH207 baseline=%0d cold=%0d",checks,cold_cases);$finish;'
 extra='''+repr('''  observe_cold=0;
  for(integer ph=0;ph<16;ph++)begin
   @(negedge nes_clk);#(0.1+ph*2.5);
   @(negedge mem_clk);begin_load=1;
   @(negedge mem_clk);begin_load=0;run_mem=0;
   repeat(12)@(negedge nes_clk);
   if(ready||!dut.gray_pending||!writing)$fatal(1,"PUBLISH217 stale admission");
   run_mem=1;repeat(12)@(negedge nes_clk);
   if(!ready||epoch!==(dut.serial^(dut.serial>>1)))$fatal(1,"PUBLISH217 recovery");
  end
  $display("PASS EPOCH207 baseline=%0d cold=%0d pending=16",checks,cold_cases);$finish;''')+'''
 s=replace(s,end,extra)
'''
s=replace(s," (a.out/'admission.sv').write_text(s,encoding='utf8')",inject+" (a.out/'admission.sv').write_text(s,encoding='utf8')")
s=replace(s,'integer cases=0;reg [31:0] seed=', 'reg [31:0] expected_gray;integer cases=0;reg [31:0] seed=')
s=replace(s,'@(posedge clk);#0.01;', '@(posedge clk);expected_gray=reset?0:(refdut.serial^(refdut.serial>>1));#0.01;')
s=replace(s,'{dut.serial,dut.gray,dut.exhausted}!=={refdut.serial,refdut.gray,refdut.exhausted}', '{dut.serial,dut.exhausted}!=={refdut.serial,refdut.exhausted} || dut.gray!==expected_gray || dut.gray_pending!==(reset?1\'b0:begin_load)')
s=replace(s,"wrong=new.read_text().replace('carry_in&!serial[epoch_bit]','carry_in&serial[epoch_bit]')", "wrong=new.read_text().replace('gray<=serial^(serial>>1);',\"gray<=(serial^(serial>>1))^32'd1;\")")
s=replace(s," r=dict(passed=True,",''' wrong=new.read_text().replace('cold_reset||gray_pending||exhausted','cold_reset||exhausted')
 (a.out/'wrong-pending.sv').write_text(wrong,encoding='utf8');run('vlog',['-sv','wrong-pending.sv'],'pending-negative-compile');sim('source_epoch207_tb','pending-negative','** Fatal: PUBLISH217 stale admission')
 r=dict(passed=True,pending_cases=16,wrong_pending_rejected=True,gray_latency_mem_cycles=1,''')
ns=dict(prior.__dict__);ns.update(transform=transform,replace=replace,__file__=__file__)
exec(compile(s,'epoch217_publish','exec'),ns)
if __name__=='__main__':ns['main']()
