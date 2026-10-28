# SPDX-License-Identifier: MIT
"""Actual source core read-lifetime checks for raw0/1/2 and no queries after seal.

Collector responses are directed valid query fixtures. Full byte/CRC/receipt
correctness is checked by the separate actual-collector integration run.
"""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha

TB=r'''`timescale 1ns/1ps
module core366 #(parameter RAW=0)(output reg finished=0);
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,start=0;wire ready,query,materialized,done,ack_ready,byte_valid;
 wire [3:0] fault;wire [2:0] kind;wire [12:0] index;
 reg response=0;reg [63:0] data=0;reg released=0;
 wire [9:0] aa,ba;wire aw,bw;wire [7:0] ad,bd,byte_data;reg [7:0] aq=0,bq=0;
 reg [7:0] memory[0:1023];integer queries=0,seals=0,bytes_seen=0;
 nes_core257 dut(PORTS);
 always @(posedge clk)begin
  aq<=memory[aa];bq<=memory[ba];if(aw)memory[aa]<=ad;if(bw)memory[ba]<=bd;
  response<=query;
  if(query)begin
   queries++;
   if(released)$fatal(1,"query after materialized raw%0d",RAW);
   if(kind==4)begin
    if(index<RAW)data<=(64'd1<<49)|({51'd0,index}<<50);
    else data<=64'h0000018000000000;
   end else data<=0;
  end
  if(materialized)begin
   if(released||dut.q_pending)$fatal(1,"invalid seal raw%0d",RAW);
   seals++;released<=1;
   if(queries!=513+RAW*256)$fatal(1,"seal before last query raw%0d count%0d",RAW,queries);
  end
  if(byte_valid)begin bytes_seen++;if($isunknown(byte_data))$fatal(1,"unknown source byte raw%0d",RAW);end
  if(!reset&&fault)$fatal(1,"source fault raw%0d code%0d",RAW,fault);
  if(done)begin
   if(seals!=1||!released)$fatal(1,"ACK without seal raw%0d",RAW);
   $display("HANDOFF366 raw=%0d queries=%0d seals=%0d bytes=%0d",RAW,queries,seals,bytes_seen);finished<=1;
  end
 end
 initial begin
  for(integer j=0;j<1024;j++)memory[j]=0;
  repeat(4)@(negedge clk);reset=0;wait(ready);@(negedge clk);start=1;@(negedge clk);start=0;
 end
endmodule
module guard366;
 wire a,b,c;core366 #(.RAW(0)) raw0(a);core366 #(.RAW(1)) raw1(b);core366 #(.RAW(2)) raw2(c);
 initial begin wait(a&&b&&c);$display("PASS HANDOFF366 raw0 raw1 raw2");$finish;end
 initial begin #100000000;$fatal(1,"handoff366 timeout");end
endmodule
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);shutil.copyfile(a.reference/'nes_core257.sv',d/'nes_core257.sv')
    values=dict(clk='clk',reset='reset',start='start',start_ready='ready',capture_materialized366='materialized',
                frame_owned="1'b1",geometry_valid="1'b1",frame_generation="16'd1",content_epoch="32'd1",frame_serial="32'd1",patch_count='RAW[2:0]',
                row_count="8'd224",group_count="6'd1",palette_count="6'd1",transport_empty="1'b1",record_ready="1'b1",byte_ready="1'b1",
                raw_response='response',raw_hit='response',raw_data='data',query='query',query_kind='kind',query_index='index',
                ram_a_addr='aa',ram_b_addr='ba',ram_a_we='aw',ram_b_we='bw',ram_a_w='ad',ram_b_w='bd',ram_a_q='aq',ram_b_q='bq',
                ack_valid='ack_ready',ack_ready='ack_ready',ack_accept="1'b1",ack_generation="16'd1",done='done',fault='fault',
                display_lease="1'b1",display_generation="16'd1",display_epoch="32'd1",byte_valid='byte_valid',byte_data='byte_data')
    header=(d/'nes_core257.sv').read_text().split('module nes_core257(',1)[1].split(');',1)[0]
    ports=[];direction=None
    for part in header.split(','):
        part=part.strip();m=re.match(r'(input|output)\s+(?:wire|reg)\s+',part)
        if m:direction=m[1];part=part[m.end():]
        part=re.sub(r'^\[[^]]+\]\s*','',part);assert re.fullmatch(r'\w+',part),part
        ports.append(f'.{part}({values.get(part,"\'0" if direction=="input" else "")})')
    (d/'guard366.sv').write_text(TB.replace('PORTS',','.join(ports)),newline='\n')
    def run(exe,args,name):
        r=subprocess.run([str(a.questa_bin/exe),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        (d/(name+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace');return r.stdout.decode(errors='replace')
    run('vlib.exe',['work'],'vlib');run('vlog.exe',['-sv','nes_core257.sv','guard366.sv'],'vlog')
    log=run('vsim.exe',['-c','work.guard366','-do','onerror {quit -code 1};run -all;quit -f'],'vsim')
    assert 'PASS HANDOFF366 raw0 raw1 raw2' in log and 'Errors: 0, Warnings: 0' in log
    result=dict(passed=True,scope=__doc__,cases=3,pins={n:sha(d/n) for n in ['nes_core257.sv','guard366.sv']})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print('PASS HANDOFF366 raw0 raw1 raw2')

if __name__=='__main__':main()
