# SPDX-License-Identifier: MIT
"""Retimed serial planner-cost candidate on the unchanged284 RTL/output ARM.

Replay separately measured actual M4 planner instructions after input commit,
then execute live output ARM/IRQ against ROM arbitration and CPU279 bus traces.
This exposes the omitted planner term; it does NOT implement early planning,
live source/planner integration, IRQ preemption during planning or full RUN.
"""
import inspect,json,shutil
import probe_nes_refill284 as prior
from nes_delta231 import ROOT,sha,once


def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0]
    evidence=ROOT.parent/'probes/nes-joint285/arm04'
    result=json.loads((evidence/'result.json').read_text());assert result['passed'] and len(result['frames'])==71
    words=[0]*976;commits=[0]*976
    for r in result['frames']:
        words[r['frame']]=r['begin_instructions']+r['plan_instructions'];commits[r['frame']]=r['commit_instructions']
    for name,values in [('planner285.hex',words),('commit285.hex',commits)]:
        (d/name).write_text(' '.join(f'{v:08x}' for v in values)+'\n')
    for n in ('result.json','costs.csv','planner.elf','nes_planner285.c'):
        shutil.copyfile(evidence/n,d/('planner-'+n));pins['planner-'+n]=sha(evidence/n)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' realtime source_end261,output_end261;', ''' reg [31:0] planner285[0:975],commit285[0:975];
 initial begin $readmemh("planner285.hex",planner285);$readmemh("commit285.hex",commit285);end
 realtime source_end261,output_end261;''')
    s=once(s,'   source_end261=$realtime;', '''   source_end261=$realtime;
   $fwrite(events261,"planner285,%0d,%0d,%0t\\n",f,planner285[f],$time);
   #(planner285[f]*CPI*1000.0/84.0);''')
    s=once(s,'   output_end261=$realtime;', '''   $fwrite(events261,"commit285,%0d,%0d,%0t\\n",f,commit285[f],$time);
   #(commit285[f]*CPI*1000.0/84.0);
   output_end261=$realtime;''')
    p.write_text(s,encoding='utf-8',newline='\n');pins['probe_nes_schedule285.py']=sha(ROOT/'tools/probe_nes_schedule285.py')
    shutil.copyfile(ROOT/'tools/probe_nes_schedule285.py',d/'probe_nes_schedule285.py')
    return src,pins


def main():
    ns=dict(prior.__dict__);ns.update(prepare=prepare,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(prior.main),'schedule285-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
