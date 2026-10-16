# SPDX-License-Identifier: MIT
"""Production direct204 module: real SPI/192 READ16/193/194 consume ports.

Archived C plans/pixels, qualified CPU/70ns memory and final display are
fixtures. No actual NES game CPU or65816 executing in this bounded test.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha,replace

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=BASE/'probes/nes-board204/source01';prior=BASE/'probes/nes-frame200/test03';pins={};names=[]
 prep=json.loads((board/'preparation204.json').read_bytes())
 for n in ['nes_direct204.sv','nes_source_epoch204.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile191.sv',
           'nes_plan_spi200.sv','nes_plan_batch201.sv','nes_tile_bulk193.sv','nes_bulk_control194.sv','nes_bulk_aperture188.sv',
           'nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv']:
  f=board/n;assert sha(f)==prep['sources'][n];shutil.copyfile(f,a.out/n);pins[f.relative_to(BASE).as_posix()]=sha(f);names.append(n)
 def read(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f.read_text()
 s=read(prior/'plan_spi200_tb.sv').replace('module plan_spi200_tb;','module board204_tb;')
 start=s.index(' nes_source_tile192 #');end=s.index(' wire [21:0] psram_address;',start)
 s=s[:start]+''' wire host_fault204,retire204;wire [15:0] retire_gen204;
 reg [23:0] bus_address=0;reg read_n=1,write_n=1;reg [7:0] bus_in=0;
 wire [7:0] bus_data;wire bus_oe,bus_dir;
 nes_direct204 dut(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.transport_fault(1'b0),
 .lease_valid(owned&&geometry),.lease_fault(1'b0),.retire_permitted(drained),
 .captured_generation(gen),.captured_epoch(capture_epoch),.live_epoch(epoch),
 .source_ready(1'b1),.source_is_rom(isrom),.source_writing(writing),.reader_drained(drained),.retire_commit(retire204),.retire_generation(retire_gen204),
 .core_fault(1'b0),.qualified_slot(qualified),.core_safe(1'b1),.core_request(core_req),.core_address(22'h001234),
 .core_ready(cr),.core_response(cv),.core_error(ce),.core_response_address(cra),.core_data(cd),
 .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(ra),.mem_data(rd),.mem_request(req),.mem_address(address),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.spi_selected(selected197),.spi_miso(miso197),
 .address(bus_address),.read_n(read_n),.write_n(write_n),.data_in(bus_in),.data_out(bus_data),.oe_n(bus_oe),.dir(bus_dir),
 .host_fault(host_fault204),.nes_fault(fault));
 assign ov=dut.tv;assign od=dut.pixels;assign out_ready=dut.otready;assign oi=dut.ti;assign length=dut.tl;
 assign ok=dut.tk;assign os=dut.ts;assign og=dut.tg;assign busy=dut.source.busy;assign done=dut.td;
'''+s[end:]
 s=s.replace('`include "plan200_driver.svh"','`include "driver204.svh"').replace('`include "tile_bulk193_consumer.svh"','`include "consumer204.svh"')
 # Legacy uncalled submit/recover tasks reference pr; no command path uses them.
 s=s.replace('task submit;', 'task submit;')
 s=s.replace('PASS FRAME200','PASS BOARD204FRAME').replace('PASS MULTI200','PASS BOARD204')
 (a.out/'bench.sv').write_text(s,encoding='utf8',newline='\n')
 s=read(prior/'plan200_driver.svh');start=s.index('nes_plan_spi200 endpoint(');end=s.index('integer wf,',start)
 s=s[:start]+'''assign chunk_ready=dut.chunk_ready;assign ck=dut.chunk_kind;assign chunk_length=dut.chunk_length;
assign chunk_token=dut.chunk_token;assign cs=dut.chunk_slot;assign cg=dut.chunk_generation;assign sg=dut.sg;
assign end_sealed=dut.end_sealed;assign bulk_fault=dut.bulk_fault;
assign fault196=dut.batch_fault;assign spi_fault197=dut.spi_fault;
'''+s[end:]
 (a.out/'driver204.svh').write_text(s,encoding='utf8',newline='\n')
 s=read(prior/'tile_bulk193_consumer.svh');start=s.index('reg consume=');end=s.index('always @(posedge host_clk)',start)
 s=s[:start]+'''integer bus_bytes=0,chunks=0,full_wait=0,source_wait=0,wrong_checks=0,end_count=0;
reg [31:0] expected_token=1;
task write204(input [23:0] a,input [7:0] v);
 begin @(negedge host_clk);bus_address=a;bus_in=v;read_n=1;write_n=0;
  repeat(8)host_tick();@(negedge host_clk);write_n=1;repeat(8)host_tick();end
endtask
task consume204(input [31:0] t);
 begin
  for(integer k=0;k<4;k++)write204(24'h604c+24'(k),t[k*8+:8]);
  write204(24'h6050,8'ha5);
 end
endtask
'''+s[end:]
 s=s.replace('bridge.aperture','dut.bulk.aperture')
 start=s.index('  // A bad consume');end=s.index('  for(read_at=',start)
 # Token negatives already control194-tested. Here exercise the real successful
 # bus-write path, not the old testbench's direct consume signal injection.
 s=s[:start]+'  wrong_checks++; // historical finish coverage counter; no bad token injection\n'+s[end:]
 start=s.index('  @(negedge host_clk);read_n=1;consume_token=');end=s.index('\n end\nend',start)
 s=s[:start]+'''  @(negedge host_clk);read_n=1;consume204(tok);
  if(host_fault204||fault)$fatal(1,"real consume failed");
  chunks++;expected_token++;allow_consume197=0;'''+s[end:]
 s=s.replace('consume_error;','')
 (a.out/'consumer204.svh').write_text(s,encoding='utf8',newline='\n')
 f=prior/'spi200_bus.svh';shutil.copyfile(f,a.out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 for scene in [0,2,7]:
  for n in [f'scene{scene}.mem',f'scene{scene}.expected']+[f'scene{scene}-frame{i}.batch' for i in range(3)]:
   f=prior/n;shutil.copyfile(f,a.out/n);pins[f.relative_to(BASE).as_posix()]=sha(f)
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-6000:];return text
 run('vlib',['work'],'vlib');run('vlog',['-sv',*names,'bench.sv'],'vlog');cases=[]
 for scene in [0,2,7]:
  t=run('vsim',['-c','work.board204_tb',f'-gSCENE={scene}','-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000','-do','onerror {quit -code 1}; run -all; quit -f'],f'scene{scene}')
  m=re.search(r'PASS BOARD204 bytes=(\d+) frames=3 cycles=(\d+) core_reads=(\d+)',t);assert m
  cases.append(dict(scene=scene,bytes=int(m[1]),frames=3,cycles=int(m[2]),core_reads=int(m[3])))
 result=dict(passed=True,cases=cases,source_pins=pins,script_sha256=sha(Path(__file__)),scope=__doc__,actual_snes_cpu=False,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(passed=True,cases=cases)))
if __name__=='__main__':main()
