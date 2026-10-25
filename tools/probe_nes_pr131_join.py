# SPDX-License-Identifier: MIT
"""Retrospective reproducer for the MAP wrapper's source/lease admission join.

Actual unmodified lease and source core, exact wrapper expressions. This is a
bounded join test, not full board/collector/firmware simulation or a product fix.
"""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--questa-bin',required=True,type=Path);a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    source=BASE/'probes/nes-execute362/objmap01';pins={}
    for name in ('nes_core257.sv','nes_capture_lease201.sv','nes_live_joint.sv','nes_native_frame201.sv','nes_joint266.sv','board.qsf'):
        p=source/name;pins[str(p)]=sha(p);shutil.copyfile(p,d/name)
    board=(d/'nes_live_joint.sv').read_text()
    assert '.start(export_permitted204&&source_start_ready267&&!source_started267)' in board
    assert '.frame_generation(captured_gen204),.content_epoch(captured_epoch204)' in board
    assert 'if(!lease204)source_started267<=0;' in board
    header=(d/'nes_core257.sv').read_text().split(');',1)[0].split('module nes_core257(',1)[1]
    values=dict(clk='clk',reset='reset',abort_source="1'b0",start='launch',frame_owned='owned',geometry_valid='valid',frame_generation='(CASE==2?native_gen:captured_gen)',content_epoch="(CASE==2?32'd1:captured_epoch)",frame_serial="32'd1",row_count="8'd224",group_count="6'd1",palette_count="6'd1",transport_empty="1'b1",byte_ready="1'b1",record_ready="1'b1")
    ports=[];direction=None
    for part in header.split(','):
        part=part.strip();m=re.match(r'(input|output)\s+(?:wire|reg)\s+',part)
        if m:direction=m[1];part=part[m.end():]
        part=re.sub(r'^\[[^]]+\]\s*','',part);assert re.fullmatch(r'\w+',part),part
        if direction=='input':ports.append(f'.{part}({values.get(part,"\'0")})')
        elif part not in ('fault','start_ready','query_generation'):ports.append(f'.{part}()')
    ports+=['.fault(core_fault)','.start_ready(core_ready)','.query_generation(query_gen)']
    tb='''`timescale 1ns/1ps
module join131_tb;
 parameter integer CASE=0;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,begin_capture=0,owned=0,valid=0,export_done=0,retire=0;
 reg [15:0] native_gen=0;
 wire lease,export_allowed,retire_allowed,release_frame,waiting_display,lease_fault;
 wire [15:0] captured_gen;wire [31:0] captured_epoch;
 wire core_ready;wire [3:0] core_fault;wire [15:0] query_gen;
 reg started=0;
 // Wrapper equations, with a readiness gate only in CASE1/2 to isolate context.
 wire ready_gate=(CASE==0)||owned;
 wire launch=export_allowed&&core_ready&&ready_gate&&!started;
 always @(posedge clk)begin
  if(reset)started<=0;
  else if(!lease)started<=0;
  else if(export_allowed&&core_ready&&ready_gate&&!started)started<=1;
 end
 nes_capture_lease201 ownership(.clk(clk),.reset(reset),.stop(1'b0),.capture_begin(begin_capture),
 .frame_owned(owned),.geometry_valid(valid),.frame_generation(native_gen),
 .export_release(export_done),.export_error(4'd0),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd1),
 .reader_drained(1'b1),.retire_commit(retire),.retire_generation(captured_gen),.release_frame(release_frame),.lease_valid(lease),
 .retire_permitted(retire_allowed),.export_permitted(export_allowed),.captured_epoch(captured_epoch),.captured_generation(captured_gen),.waiting_display(waiting_display),.fault(lease_fault));
 nes_core257 core(CORE_PORTS);
 initial begin
  repeat(3)@(negedge clk);reset=0;
  if(CASE!=0)begin
   @(negedge clk);begin_capture=1;
   @(negedge clk);begin_capture=0;native_gen=1;owned=1;valid=1;
  end
  repeat(5)@(negedge clk);
  if(lease_fault||captured_epoch!==0||captured_gen!==0)$fatal(1,"lease fixture131");
  if(CASE<2)begin
   if(core_fault!==1)$fatal(1,"expected original admission rejection131");
   $display("REPRO131 case=%0d owned=%0d native_gen=%0d source_epoch=%0d source_gen=%0d fault=%0d",CASE,owned,native_gen,captured_epoch,captured_gen,core_fault);
  end else begin
   if(core_fault!==0||query_gen!==1)$fatal(1,"live context control rejected131");
   $display("CONTROL131 live capture context admitted; collector query data not exercised");
  end
  $finish;
 end
 initial begin #100000;$fatal(1,"timeout131");end
endmodule
'''.replace('CORE_PORTS',','.join(ports))
    (d/'join131_tb.sv').write_text(tb,encoding='utf-8',newline='\n')
    def run(name,args,label):
        r=subprocess.run([str(a.questa_bin/name),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
        (d/(label+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace');return r.stdout.decode(errors='replace')
    run('vlib.exe',['work'],'vlib');run('vlog.exe',['-sv','nes_capture_lease201.sv','nes_core257.sv','join131_tb.sv'],'vlog')
    for case in range(3):
        log=run('vsim.exe',['-c','work.join131_tb',f'-gCASE={case}','-do','onerror {quit -code 1};run -all;quit -f'],f'case{case}')
        assert ('REPRO131' if case<2 else 'CONTROL131') in log
        assert 'Errors: 0, Warnings: 0' in log
    result=dict(passed=True,original_failures_reproduced=['start allowed without a captured frame','first valid capture passes stale zero display epoch/generation to source'],control='Live capture epoch/generation plus captured-frame gate admits source; not a complete repair',scope=__doc__,pins=pins)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
