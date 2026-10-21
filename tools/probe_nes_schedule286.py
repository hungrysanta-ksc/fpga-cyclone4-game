# SPDX-License-Identifier: MIT
"""Conservative serial incremental-planner cost plus live ARM/IRQ/ROM286.

New canonical expansion and early-H2 work are charged after source commit;
no unimplemented overlap or early FPGA plan lease is credited. Original source
SPI packing stays unchanged. Output ARM still produces/checks its own H2.
"""
import inspect,json,shutil
import probe_nes_refill284 as prior
from nes_joint286 import apply
from nes_delta231 import ROOT,sha,once


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];apply(d)
    evidence=ROOT.parent/'probes/nes-joint286/arm03'
    result=json.loads((evidence/'result.json').read_text());assert result['passed'] and len(result['frames'])==71 and not result['geometry_boundary']
    words=[0]*976;commits=[0]*976
    for r in result['frames']:words[r['frame']]=r['postdecode_instructions'];commits[r['frame']]=r['commit_instructions']
    for name,values in [('planner286.hex',words),('commit286.hex',commits)]:
        (d/name).write_text(' '.join(f'{v:08x}' for v in values)+'\n')
    for n in ('result.json','planner.elf','nes_planner211.c','nes_planner285.c','nes_input286.inc'):
        shutil.copyfile(evidence/n,d/('planner-'+n));pins['planner-'+n]=sha(evidence/n)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' realtime source_end261,output_end261;', ''' reg [31:0] planner286[0:975],commit286[0:975];
 initial begin $readmemh("planner286.hex",planner286);$readmemh("commit286.hex",commit286);end
 realtime source_end261,output_end261;''')
    s=once(s,'   source_end261=$realtime;', '''   source_end261=$realtime;
   $fwrite(events261,"planner286,%0d,%0d,%0t\\n",f,planner286[f],$time);
   #(planner286[f]*CPI*1000.0/84.0);''')
    s=once(s,'   output_end261=$realtime;', '''   $fwrite(events261,"commit286,%0d,%0d,%0t\\n",f,commit286[f],$time);
   #(commit286[f]*CPI*1000.0/84.0);
   output_end261=$realtime;''')
    # Observe immutable admission independently of both consumers.
    s=once(s,' initial begin : consumer', ''' reg [83:0] admitted286_expected;reg admitted286_seen;
 always @(posedge host_clk)begin
  if(reset||test_abort)admitted286_seen<=0;
  else begin
   if(dut.flow.grant278)begin admitted286_expected<=dut.flow.full_idata278;admitted286_seen<=1;end
   else if(admitted286_seen&&!dut.flow.fault&&dut.flow.have_identity&&dut.flow.admitted286!==admitted286_expected)$fatal(1,"identity owner changed");
  end
 end
 initial begin : consumer''')
    p.write_text(s,encoding='utf-8',newline='\n')
    for n in ('nes_joint286.py','probe_nes_schedule286.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
    return src,pins


def main():
    ns=dict(prior.__dict__);ns.update(prepare=prepare,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(prior.main),'schedule286-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
