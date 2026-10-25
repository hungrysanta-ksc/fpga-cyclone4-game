# SPDX-License-Identifier: MIT
"""Compare retained plane checks with the old implementation; query6/rearm/STOP."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_refill267 import run
PORTS='''.clk(clk),.reset(reset),.release_scene(release_scene),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
.scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
.obj_valid(obj_valid),.extra_sprites(extra_sprites),.bg_attribute(2'd0),.obj_attribute(8'd0),.obj_x(8'd0),
.ppu_read(1'b1),.ppu_valid(ppu_valid),.logical_address(logical_address),.physical_address(physical_address),
.query(query),.query_tile(query_tile),.initialized(initialized[g]),.active(active[g]),.owned(owned[g]),.valid(valid[g]),
.errors(errors[g]),.generation(generation[g]),.event_valid(ev[g]),.event_data(ed[g]),.response(response[g]),.required_kind(kind[g])'''
TB=r'''`timescale 1ns/1ps
module bitmap368_tb;
 reg clk=0;always #22.727272727 clk=~clk;
 reg reset=1,release_scene=0,ppu_ce=0,rom_fault=0,ppu_valid=1,extra_sprites=0;
 reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=1,query=0;
 reg [8:0] scanline=0,dot=0;reg [13:0] logical_address=0;reg [21:0] physical_address=0;reg [12:0] query_tile=0;
 wire [2:0] initialized,active,owned,valid,response,ev;wire [7:0] errors[0:2];wire [15:0] generation[0:2];
 wire [63:0] ed[0:2];wire [1:0] kind[0:2];reg compare368=1;integer cases=0,events=0;
 generate for(genvar g=0;g<3;g++)begin: unit368
  if(g==2)legacy_planes368 dut(PORTS);
  else nes_native_planes165 #(.REQUIRED_BITMAP(g)) dut(PORTS);
 end endgenerate
 always @(negedge clk)if(!reset&&compare368)begin
  if(active[0]!==active[1]||active[1]!==active[2]||owned[0]!==owned[1]||owned[1]!==owned[2]||
     valid[0]!==valid[1]||valid[1]!==valid[2]||errors[0]!==errors[1]||errors[1]!==errors[2]||ev[0]!==ev[1]||ev[1]!==ev[2])$fatal(1,"plane validation mismatch");
  if(ev[0])begin if(ed[0]!==ed[1]||ed[1]!==ed[2])$fatal(1,"plane event mismatch");events++;end
 end
 task tick;@(negedge clk);#1;endtask
 task clear;begin reset=1;release_scene=0;ppu_ce=0;query=0;rom_fault=0;ppu_valid=1;extra_sprites=0;
  bg_low=0;bg_high=0;obj_low=0;obj_high=0;compare368=1;repeat(4)tick();reset=0;wait(&initialized);tick();end endtask
 task drive(input integer line,input integer column,input integer low,input integer high,input integer object,
   input [21:0] physical,input [13:0] logical);begin
  tick();scanline=line;dot=column;physical_address=physical;logical_address=logical;
  bg_low=low&&!object;bg_high=high&&!object;obj_low=low&&object;obj_high=high&&object;ppu_ce=1;
  tick();ppu_ce=0;bg_low=0;bg_high=0;obj_low=0;obj_high=0;repeat(2)tick();
 end endtask
 task read_required(input [12:0] tag);begin
  tick();query=1;query_tile=tag;@(posedge clk);#1;
  if(response[0]||kind[0]!=0||!response[1]||!response[2]||kind[1]!=1||kind[2]!=1)$fatal(1,"required query retained/rejected");
  tick();query=0;tick();
 end endtask
 initial begin
  for(integer bad=0;bad<8;bad++)begin
   clear();drive(7,257,0,0,0,0,0);
   if(bad==3)extra_sprites=1;
   drive(8,1,1,0,0,bad==1?22'h200101:22'h200100,14'h0100);
   if(bad==4)begin rom_fault=1;wait(&owned);end
   else begin
    if(bad==6)drive(8,1,1,0,0,22'h200100,14'h0100);
    if(bad!=5)drive(8,3,0,1,bad==2,bad==7?22'h200118:22'h200108,14'h0108);
    drive(232,1,0,0,0,0,0);wait(&owned);
   end
   tick();if(valid!==(bad==0||bad==7?3'b111:3'b000))$fatal(1,"expected plane validity case%0d errors%h",bad,errors[0]);
   if(bad==0||bad==7)read_required(13'h10);
   if(bad==7)read_required(13'h11);
   cases++;
  end
  clear();drive(7,257,0,0,0,0,0);drive(8,1,1,0,0,22'h200100,14'h100);
  tick();release_scene=1;tick();release_scene=0;repeat(20)tick();
  if(ev||owned||active)$fatal(1,"late event/ownership after STOP");cases++;
  clear();drive(7,257,0,0,0,0,0);drive(232,1,0,0,0,0,0);wait(&owned);tick();
  compare368=0;release_scene=1;tick();release_scene=0;repeat(16)tick();
  if(initialized!==3'b001)$fatal(1,"expected bitmap-only scrub latency");
  drive(7,257,0,0,0,0,0);if(active!==3'b001||generation[0]!=2||generation[1]!=1||generation[2]!=1)$fatal(1,"immediate next capture");cases++;
  $display("PASS BITMAP368 cases=%0d events=%0d",cases,events);$finish;
 end
 initial begin #100000000;$fatal(1,"bitmap368 timeout");end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'src/fpga/nes_source368/nes_native_planes165.sv',d/'nes_native_planes165.sv')
 old=(BASE/'probes/nes-hint367/map02/nes_native_planes165.sv').read_text().replace('module nes_native_planes165(', 'module legacy_planes368(')
 (d/'legacy_planes368.sv').write_text(old,newline='\n');(d/'bitmap368_tb.sv').write_text(TB.replace('PORTS',PORTS),newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_native_planes165.sv','legacy_planes368.sv','bitmap368_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.bitmap368_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',180);assert 'PASS BITMAP368 cases=10' in log
 result=dict(passed=True,cases=10,pins={p.name:sha(p) for p in d.glob('*.sv')});(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(log[-500:])
if __name__=='__main__':main()
