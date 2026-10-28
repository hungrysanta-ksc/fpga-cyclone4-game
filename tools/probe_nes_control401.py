# SPDX-License-Identifier: MIT
"""400 RTL/M4 with exact native view and observed prior-HDMA service envelope.
No replacement RTL or new area saving is claimed. The CPU service envelope is
observed at three phases, not a proven all-phase resident CPU timing bound.
"""
import json,shutil
import probe_nes_joint400 as previous
from nes_delta231 import ROOT,sha,once

driver=previous.driver
driver.__file__=__file__
def profile(d,f):
 q=driver.NATIVE/str(f);r=json.loads((q/'model401.json').read_text())
 for name,h in r['files'].items():assert sha(q/name)==h;shutil.copyfile(q/name,d/name)
 shutil.copyfile(q/'model401.json',d/f'model401-{f}.json')
 return r
driver.profile=profile

adapt=driver.adapt_tb
def bench(s):
 s=adapt(s)
 s=once(s,' task reset394;begin', '''reg[63:0]view_head401[0:127],poll401[0:0];
 task reset394;begin
  $readmemh($sformatf("view401-%0d.hex",f),view_head401);$readmemh($sformatf("poll401-%0d.hex",f),poll401);''')
 task=''' task view401;
 integer count;reg[63:0]e;reg[23:0]a;reg[7:0]b;realtime origin;
 begin
  origin=$realtime;count=0;
  $fwrite(events261,"view_start401,%0d,%0t\\n",f,$time);
  for(integer i=1;i<=view_head401[0];i++)begin
   e=view_head401[i];until378(origin+e[63:40]*MASTER_NS378);a=e[31:8];
   if(e[32])$fatal(1,"unexpected native head write401");
   if(a>=24'h006000)begin
    rd400(a,b);
    if(a>=24'h006070&&a<24'h00607c)begin
     if(a!=24'h006070+count||b!==view394[count])$fatal(1,"native ordered view401");count++;
    end else if(a==24'h006001&&b[7:6])$fatal(1,"native head fault401");
    else if(a==24'h006054&&b!=1)$fatal(1,"native head ready401");
   end
  end
  if(count!=12)$fatal(1,"native view count401");
  $fwrite(events261,"view_end401,%0d,%0t\\n",f,$time);
 end endtask
'''
 s=once(s,' task display_job394;',task+' task display_job394;')
 a=s.index('  // Exact12 view reads;');b=s.index('  if(f>=907)while',a)
 s=s[:a]+'''  view401();check_final265();
  $fwrite(events261,"display_gate401,%0d,%0d,%0d,%0d,%0t\\n",f,phase378(),config394[4],config394[2],$time);
'''+s[b:]
 poll='#(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;'
 assert s.count(poll)==2
 s=s.replace(poll,'#(poll401[0]*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;')
 return s
driver.adapt_tb=bench
prepare=driver.prepare
def fresh(d,last,cold_quantum=0):
 src=prepare(d,last,cold_quantum)
 p=d/'joint266_tb.sv';s=p.read_text();monitor=(ROOT/'tests/nes-control399/ports.svh').read_text()
 monitor=monitor.replace('capture&&!dut.flow.read359[33]','capture&&dut.flow.read_pending')
 monitor=monitor.replace('ports399.csv','ports401.csv')
 # Additional simultaneous demand counts are hypothetical if merged; they
 # never drive a real port or count payload writes as control RAM accesses.
 monitor+=r'''
 integer overlap401[0:3];initial for(integer i=0;i<4;i++)overlap401[i]=0;
 always @(posedge clk)if(!reset)begin
  if(source_write399&&planrom.transport.plan_request396)overlap401[0]++;
  if(source_write399&&hint_metaactive398)overlap401[1]++;
  if(source_write399&&tv263&&tr263)overlap401[2]++;
  if(planrom.transport.plan_request396&&tv263&&tr263)overlap401[3]++;
 end
 final for(integer i=0;i<4;i++)$display("PORT401 demand%0d=%0d",i,overlap401[i]);
'''
 at=s.rindex('endmodule');p.write_text(s[:at]+monitor+'\n'+s[at:],newline='\n')
 (d/'manifest401.json').write_text(json.dumps(dict(RTL={n:sha(d/n)for n in src},ELF=sha(d/'output.elf'),program=sha(d/'program398.hex'),test=sha(p),model='native view and phase-sampled HDMA envelope; not WCET',new_RTL=False),indent=2)+'\n')
 return src
driver.prepare=fresh
if __name__=='__main__':driver.main()
