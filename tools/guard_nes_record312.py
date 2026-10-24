# SPDX-License-Identifier: MIT
"""Retained independent checker/STOP/final ACK guards on the record ingress."""
import json,sys,shutil
from pathlib import Path
import guard_nes_ingress307 as old
from nes_slots312 import apply as slots
from nes_record312 import apply as record
from nes_delta231 import ROOT,sha
prior=old.old.record305
def patch(d):prior(d);slots(d);record(d)
old.old.record305=patch
before=old.engine.adapt
def fix(s):
    s=s.replace('[183:0]','[199:0]').replace('WINDOW=4','WINDOW=2')
    s=s.replace('(dut.flow.queue.accepted-dut.flow.queue.retired)<4','(dut.flow.queue.accepted-dut.flow.queue.retired)<2')
    s=s.replace('dut.flow.header[0]!=12&&!dut.flow.qr','dut.flow.header[0]!=12&&!(dut.flow.header[0]==14&&dut.flow.remaining==1)&&!dut.flow.qr')
    s=s.replace('dut.flow.state==dut.flow.HCAP&&dut.flow.at==3','dut.flow.queue.loading312&&dut.flow.queue.load_at312==3')
    s=s.replace("b=dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i];", '''if(i<16)begin
      if(i>=4&&i<=9)begin
       if(i<8)b=dut.flow.identity[(i-4)*8+:8];else b=dut.flow.identity[32+(i-8)*8+:8];
      end else b=dut.flow.queue.record312[dut.flow.queue.field312(i)*8+:8];
     end else b=dut.flow.queue.buffer[(dut.flow.queue.retired[0]?752:480)+24+i-16];''')
    return s
def adapt(s):return fix(before(s))
old.engine.adapt=adapt
previous_run=old.engine.prior.run
def run(tool,args,d,label,*extra,**kw):
    if label=='vlog':
        p=d/'joint266_tb.sv';s=fix(p.read_text())
        s=s.replace(' initial begin : result264', '''
 reg debug312=0;
 always @(posedge host_clk)if(source_fault&&!debug312)begin
  debug312=1;$display("FAULT312 flow=%0d failed=%0d qfault=%0d seq=%0d admission=%0d accepted=%0d retired=%0d loaded=%0d badhead=%0d encoded=%0d v=%0d vf=%0d",dut.flow.state,dut.flow.failed,dut.flow.qfault,dut.flow.packet_seq,dut.flow.queue.sequence312,dut.flow.queue.accepted,dut.flow.queue.retired,dut.flow.queue.loaded312,dut.flow.queue.bad_header312,dut.flow.queue.ingress_length312,dut.core.validator.state,dut.core.validator.fault);
 end
 initial begin : result264''')
        p.write_text(s,newline='\n')
    return previous_run(tool,args,d,label,*extra,**kw)
old.engine.prior.run=run
def finish(d):
    log=run(Path('C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'),
        ['-c','-sv_lib','producer263','work.joint266_tb','-gGNEG=0','+LAST=905',
         '-do','onerror {quit -code 1};run -all;quit -f'],d,'positive312',180)
    assert 'PASS JOINT266 frames=1' in log
    r=json.loads((d/'result.json').read_text());r['positive_control312']=True
    r['scope312']='Independent checker/STOP guards with actual two-slot fixture admission; separate GNEG=0 positive control.'
    for name in ('nes_slots312.py','nes_record312.py','guard_nes_record312.py'):
        shutil.copyfile(ROOT/'tools'/name,d/name);r.setdefault('entry_hashes',{})[name]=sha(d/name)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
if __name__=='__main__':
    old.old.main();finish(Path(sys.argv[sys.argv.index('--out')+1]))
