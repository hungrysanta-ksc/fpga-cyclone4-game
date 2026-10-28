# SPDX-License-Identifier: MIT
"""Bounded session guards: actual lease/controller, forced collector boundary.

These isolate ownership/protocol edges, not collector content correctness. The
separate full functional run uses the actual collector and actual query data.
"""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha

TB=r'''`timescale 1ns/1ps
module guard365;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,stop=0,ready=1,done=0,identity_ready=0,ack=0,flow_error=0,drained=1,retire=0;
 reg sr=1,isrom=1,writing=0,cap=0,have=0,valid=0,materialize=0;reg [31:0] epoch=1;reg [15:0] gen=0;
 wire launch,identity,prelease,release_frame,lease,permitted,waiting,fault;
 wire [31:0] source_epoch,serial;wire [15:0] source_gen,captured_gen;
 integer starts=0,checks=0;
 nes_native_capture365 #(.EARLY_RELEASE(EARLY)) dut(PORTS);
 always @(posedge clk)if(reset)starts<=0;else if(launch)starts<=starts+1;
 task tick;@(negedge clk);endtask
 task clear;
 begin
  reset=1;stop=0;ready=1;done=0;identity_ready=0;ack=0;flow_error=0;drained=1;retire=0;
  sr=1;isrom=1;writing=0;cap=0;have=0;valid=0;materialize=0;epoch=1;gen=0;
  repeat(3)tick();reset=0;tick();
 end endtask
 task capture;
 begin cap=1;tick();cap=0;gen=gen+1;have=1;valid=1;repeat(4)tick();end
 endtask
 task commit;
 begin
  if(EARLY)begin materialize=1;tick();materialize=0;tick();if(lease||identity)$fatal(1,"local read seal published display before ACK366");end
  done=1;tick();done=0;tick();if(!lease||!identity||captured_gen!=source_gen)$fatal(1,"commit guard365");
 end
 endtask
 task cancelled;
 begin
  repeat(4)tick();
  if(launch||identity||lease||permitted||!release_frame)$fatal(1,"completion escaped cancellation365");
 end endtask
 task passed(input string label);
 begin checks++;$display("GUARD365 %0d %s",checks,label);end endtask
 initial begin
  force dut.capture_begin=cap;force dut.owned=have;force dut.geometry_valid=valid;force dut.generation=gen;
  clear();repeat(10)tick();if(starts||launch)$fatal(1,"pre-capture start");passed("no start before capture");
  have=1;valid=1;repeat(5)tick();if(starts)$fatal(1,"untracked capture start");passed("owned alone is insufficient");
  clear();cap=1;tick();cap=0;gen=1;have=1;valid=0;repeat(5)tick();if(starts)$fatal(1,"invalid geometry start");passed("invalid geometry held");
  clear();epoch=0;capture();if(starts)$fatal(1,"epoch zero start");passed("zero epoch held");
  clear();capture();if(starts!=1||source_epoch!=1||source_gen!=1||serial!=1)$fatal(1,"first source context");repeat(8)tick();if(starts!=1)$fatal(1,"repeated launch");passed("first live context and exactly one start");
  commit();have=0;valid=0;cap=1;tick();cap=0;gen=2;have=1;valid=1;repeat(6)tick();
  if(source_gen!=1||source_epoch!=1||serial!=1||starts!=1||!lease)$fatal(1,"next capture replaced display context");passed("next capture cannot replace active source/display");
  ack=1;tick();ack=0;retire=1;tick();retire=0;repeat(5)tick();
  if(serial!=2||source_gen!=2||starts!=2||fault)$fatal(1,"ordered retirement/rearm");passed("rearm only after final ACK and plan retirement");
  clear();ready=0;cap=1;tick();cap=0;gen=1;have=1;valid=1;repeat(3)tick();ready=1;tick();stop=1;tick();stop=0;cancelled();if(starts)$fatal(1,"STOP launch race");passed("STOP between arm and launch");
  clear();capture();stop=1;done=1;tick();stop=0;done=0;cancelled();passed("simultaneous STOP and DONE blocked");
  done=1;tick();done=0;cancelled();passed("late DONE after STOP blocked");
  clear();capture();commit();stop=1;tick();stop=0;cancelled();passed("STOP before identity consumption");
  clear();capture();commit();retire=1;tick();retire=0;cancelled();if(!fault)$fatal(1,"early retire not faulted");passed("plan retire before final ACK rejected");
  clear();capture();commit();ack=1;tick();ack=0;drained=0;retire=1;tick();retire=0;cancelled();if(!fault)$fatal(1,"undrained retire not faulted");passed("undrained retirement rejected");
  clear();capture();gen=2;cancelled();passed("input generation mutation cancelled");
  clear();capture();commit();epoch=2;cancelled();passed("ROM epoch mutation cancelled");
  clear();writing=1;capture();cancelled();passed("writable ROM rejects capture");
  clear();gen=16'hffff;capture();if(starts!=1||source_gen!=0||fault)$fatal(1,"generation wrap");passed("generation16 wrap is contextual");
  clear();done=1;tick();done=0;cancelled();if(!fault)$fatal(1,"unsolicited DONE");passed("unsolicited DONE rejected");
  if(EARLY)begin
   clear();capture();materialize=1;tick();materialize=0;have=0;valid=0;tick();
   cap=1;tick();cap=0;gen=2;done=1;tick();done=0;tick();
   if(release_frame||!lease||source_gen!=1||captured_gen!=1||serial!=1)$fatal(1,"input ACK released following capture366");
   passed("input ACK cannot release following capture");
   clear();capture();materialize=1;tick();materialize=0;tick();stop=1;done=1;tick();stop=0;done=0;cancelled();
   passed("STOP after local seal blocks input ACK");
   clear();capture();done=1;tick();done=0;cancelled();if(!fault)$fatal(1,"unmaterialized COMMIT accepted366");
   passed("input ACK before materialization rejected");
   clear();capture();materialize=1;tick();materialize=0;tick();materialize=1;tick();materialize=0;cancelled();if(!fault)$fatal(1,"duplicate materialization accepted366");
   passed("duplicate local seal rejected");
  end
  $display("PASS SESSION365 guards=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"guard365 timeout");end
endmodule
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--controller',type=Path);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    ref=a.reference.resolve();r=json.loads((ref/'result.json').read_text());assert r['passed']
    sources=list(r['rtl_hashes']);early=False
    if (ref/'manifest365.json').exists():early=json.loads((ref/'manifest365.json').read_text()).get('early_release',False)
    for n in sources:shutil.copyfile(ref/n,d/n)
    if a.controller:shutil.copyfile(a.controller,d/'nes_native_capture365.sv')
    values=dict(clk='clk',reset='reset',stop='stop',source_start_ready='ready',source_done='done',identity_ready='identity_ready',display_ack='ack',
                source_ready='sr',source_is_rom='isrom',source_writing='writing',live_epoch='epoch',flow_error='flow_error',reader_drained='drained',retire_commit='retire',retire_generation='captured_gen',
                source_start='launch',identity_valid='identity',prelease='prelease',effective_release='release_frame',lease_valid='lease',retire_permitted='permitted',waiting_display='waiting',lease_fault='fault',
                source_epoch='source_epoch',source_serial='serial',source_generation='source_gen',captured_generation='captured_gen',capture_materialized366='materialize')
    text=(d/'nes_native_capture365.sv').read_text()
    header=re.search(r'module nes_native_capture365(?:\s*#\([^)]*\))?\s*\((.*?)\);',text,re.S).group(1)
    ports=[];direction=None
    for part in header.split(','):
        part=part.strip();m=re.match(r'(input|output)\s+(?:wire|reg)\s+',part)
        if m:direction=m[1];part=part[m.end():]
        part=re.sub(r'^\[[^]]+\]\s*','',part);assert re.fullmatch(r'\w+',part),part
        value=values.get(part,"'0" if direction=='input' else '')
        ports.append(f'.{part}({value})')
    (d/'guard365.sv').write_text(re.sub(r'\bEARLY\b',str(int(early)),TB.replace('PORTS',','.join(ports))),newline='\n')
    def run(exe,args,name):
        r=subprocess.run([str(a.questa_bin/exe),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        (d/(name+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace');return r.stdout.decode(errors='replace')
    run('vlib.exe',['work'],'vlib');run('vlog.exe',['-sv',*sources,'guard365.sv'],'vlog')
    log=run('vsim.exe',['-c','work.guard365','-do','onerror {quit -code 1};run -all;quit -f'],'vsim')
    count=22 if early else 18
    assert f'PASS SESSION365 guards={count}' in log
    assert 'Errors: 0, Warnings: 0' in log
    out=dict(passed=True,guards=count,scope=__doc__,controller_override=str(a.controller) if a.controller else None,pins={n:sha(d/n) for n in sources+['guard365.sv']})
    (d/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print(f'PASS SESSION365 guards={count}')

if __name__=='__main__':main()
