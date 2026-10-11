# SPDX-License-Identifier: MIT
"""Actual released152 core/game, Start-path investigation with bounded reader model."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,time
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--frames',type=int,default=240);p.add_argument('--start-frame',type=int,default=30)
 p.add_argument('--latency',type=int,default=5);p.add_argument('--physical',action='store_true')
 p.add_argument('--service',type=Path);p.add_argument('--dpi-gcc',type=Path)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 e=a.baseline/'nes-game152/evidence';old=a.baseline/'nes-game148/evidence'
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game152-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];a.out.mkdir(parents=True)
 names=VHDL+SV+EXTRA+['nes_game_pad150.sv']
 for n in names:
  src=e/'asm'/n;assert sha(src)==pins['asm/'+n];d=a.out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,d)
 if a.service:shutil.copy2(a.service,a.out/'nes_rom_service.sv')
 assert sha(a.rom)==ROM_SHA;image=a.rom.read_bytes()
 for n,b in [('prg',image[16:0x40010]),('chr',image[0x40010:])]:
  (a.out/(n+'.hex')).write_text(''.join('%02x\n'%x for x in b))
 tb=(old/'core03/game147_tb.sv').read_text()
 assert sha(old/'core03/game147_tb.sv')==json.loads((old/'manifest.json').read_bytes())['files']['core03/game147_tb.sv']
 tb=tb.replace('game147_tb','game154_tb')
 tb=tb.replace('wire [4:0] joypad1_data=0,joypad2_data=0;', '''integer frame=0,START_FRAME;
 wire pad_serial,pad_ready;
 wire [4:0] joypad1_data={4'b0,pad_serial},joypad2_data=0;
 wire start_pressed=(frame>=START_FRAME && frame<START_FRAME+15) || (frame>=START_FRAME+60 && frame<START_FRAME+75);
 nes_game_pad150 pad(.host_clk(clk),.nes_clk(clk),.reset(reset),.commit(pad_ready),
  .snes_buttons(start_pressed?16'h1000:16'd0),.host_ready(pad_ready),
  .strobe(joypad_out[0]),.read_clock(joypad_clock[0]),.serial(pad_serial));
 initial begin if(!$value$plusargs("START_FRAME=%d",START_FRAME))START_FRAME=300;end''')
 tb=tb.replace('integer target,unused,frame=0,','integer target,unused,')
 if not a.physical:
  tb=tb.replace('initial begin #3.5;forever #2.9761905 mem_clk=~mem_clk;end','// No168MHz pin events in abstract backend mode.')
  start=tb.index(' nes_rom_physical #(');end=tb.index(' reg [7:0] prg',start)
  tb=tb[:start]+''' reg backend_busy=0;integer remaining=0,LATENCY;reg [21:0] backend_address=0;
 initial begin if(!$value$plusargs("LATENCY=%d",LATENCY))LATENCY=5;end
 assign rom_ready=!backend_busy || rom_response;
 assign rom_response=backend_busy && remaining==1;
 assign rom_response_address=backend_address;
 assign rom_data=value({2'b0,backend_address});assign rom_error=0;
 always @(posedge clk)begin
  if(common_reset)begin backend_busy<=0;remaining<=0;end
  else begin
   if(backend_busy)begin remaining<=remaining-1;if(remaining==1)backend_busy<=0;end
   if(rom_request && rom_ready)begin backend_busy<=1;remaining<=LATENCY;backend_address<=rom_address;end
  end
 end
'''+tb[end:]
  start=tb.index(' wire selected=');end=tb.index(' integer target',start);tb=tb[:start]+tb[end:]
 # Avoid pixel dump and per-clock packed history work in a long investigation.
 start=tb.index(' reg [255:0] history');end=tb.index(' always @(posedge clk)if(!reset)begin\n  ticks++;',start)
 tb=tb[:start]+''' integer trace;
 reg [21:0] last_ppu=0;integer trace_count=0;
 reg [255:0] history154[0:31];integer history_index154=0;
 always @(posedge clk)if(!reset)begin
  history154[history_index154]<={ticks,scanline,cycle,ppumem_addr,rom_ppu_valid,rom_request,rom_address,rom_response,rom_response_address,
    rom_service.busy,rom_service.pending_ppu,rom_service.age,game147_prefetch_hint,game148_hint_physical,
    dut.core.ppu.ALE,dut.core.ppu.read_2007_delayed,dut.core.ppu.is_rendering_d,dut.core.ppu.sprite_load_en,
    dut.core.ppu.vram_a_byte,dut.core.ppu.vram_a,dut.core.ppu.vram_pins,rom_service.ppu_tag,rom_service.ppu_previous_tag,
    dut.core.ppu.write_2007_delayed,rom_cpu_sample,cpumem_read,rom_cpu_valid};
  history_index154<=(history_index154+1)%32;
  if(fault_trigger)begin
   for(integer h=0;h<32;h++)$fdisplay(trace,"HISTORY154 %064h",history154[(history_index154+h)%32]);
   $fflush(trace);
  end
  if((ppumem_addr>=22'h217a00 && ppumem_addr<22'h217a40) || fault_trigger)begin
   if(trace_count<20000 && (last_ppu!=ppumem_addr || rom_request || rom_response || tap_ce || fault_trigger))begin
    $fwrite(trace,"tick=%0d frame=%0d line=%0d dot=%0d ppu=%h valid=%b req=%b/%h rsp=%b/%h busy=%b age=%0d hint=%b/%h ALE=%b rd7=%b render=%b sprite=%b latch=%h vram_a=%h pins=%h cached=%h prev=%h context=%h\\n",
     ticks,frame,scanline,cycle,ppumem_addr,rom_ppu_valid,rom_request,rom_address,rom_response,rom_response_address,
     rom_service.busy,rom_service.age,game147_prefetch_hint,game148_hint_physical,
     dut.core.ppu.ALE,dut.core.ppu.read_2007_delayed,dut.core.ppu.is_rendering_d,dut.core.ppu.sprite_load_en,
     dut.core.ppu.vram_a_byte,dut.core.ppu.vram_a,dut.core.ppu.vram_pins,rom_service.ppu_tag,rom_service.ppu_previous_tag,fault_context);
    trace_count++;
   end
  end
  last_ppu<=ppumem_addr;
 end
'''+tb[end:]
 tb=tb.replace('for(integer h=0;h<16;h++)$display("HISTORY147 %064h",history[(hi+h)%16]);','')
 tb=tb.replace('if(frame<=2 || frame%10==0 || frame==target)fp=$fopen($sformatf("game-%0d.hex",frame),"w");','')
 tb=tb.replace('$readmemh("prg.hex",prg);','trace=$fopen("requests.txt","w");\n  $readmemh("prg.hex",prg);')
 if a.dpi_gcc:
  # Host lookup only. Same exact private ROM, read-only byte API and timing.
  shutil.copy2(a.rom,a.out/'game.nes')
  c='''#include <stdio.h>
 #include <stdlib.h>
 static unsigned char rom[393232];static int loaded;
 __declspec(dllexport) int game154_byte(int address){
  if(!loaded){FILE*f=fopen("game.nes","rb");if(!f||fread(rom,1,sizeof rom,f)!=sizeof rom)abort();fclose(f);loaded=1;}
  if(address>=0&&address<0x40000)return rom[16+address];
  if(address>=0x200000&&address<0x220000)return rom[16+0x40000+address-0x200000];
  abort();return 0;
 }
 '''
  (a.out/'lookup.c').write_text(c)
  r=subprocess.run([str(a.dpi_gcc),'-O2','-shared','-o',str(a.out/'lookup.dll'),str(a.out/'lookup.c')],capture_output=True)
  (a.out/'dpi-build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0
  begin=tb.index(' reg [7:0] prg[');end=tb.index(' endfunction',begin)+len(' endfunction')
  tb=tb[:begin]+''' import "DPI-C" function int game154_byte(input int address);
 function automatic [7:0] value(input [23:0] address);
  if((address<24'h40000)||(address>=24'h200000&&address<24'h220000))value=8'(game154_byte(int'(address)));else value=8'hxx;
 endfunction'''+tb[end:]
  tb=tb.replace('prg[cpumem_addr]','value(cpumem_addr)').replace('chr[ppumem_addr[16:0]]','value({2\'b0,ppumem_addr})')
  tb=tb.replace('$readmemh("prg.hex",prg);$readmemh("chr.hex",chr);','')
 (a.out/'game154_tb.sv').write_text(tb,encoding='utf8',newline='\n')
 def run(exe,args,log):
  with (a.out/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
  return r.returncode,(a.out/log).read_text(errors='replace')
 for exe,args,log in [('vlib',['work'],'vlib.log')]+[('vcom',['-2008',n],f'vcom-{i}.log') for i,n in enumerate(VHDL)]+[('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_game_pad150.sv','game154_tb.sv'],'vlog.log')]:
  code,logtext=run(exe,args,log);assert code==0 and not re.search(r'\*\* (?:Error|Fatal):',logtext),(log,logtext[-4000:])
 began=time.time();code,logtext=run('vsim',['-c',*(['-sv_lib','lookup'] if a.dpi_gcc else []),'work.game154_tb',f'+FRAMES={a.frames}',f'+START_FRAME={a.start_frame}',f'+LATENCY={a.latency}','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation.log')
 result=dict(passed='PASS GAME147' in logtext,exit_code=code,physical_model=a.physical,abstract_latency=a.latency,frames=a.frames,start_frame=a.start_frame,
  elapsed_seconds=time.time()-began,sources={n:sha(a.out/n) for n in names+['game154_tb.sv']},tail=logtext[-3500:],scope='Actual core/mapper/game with two15frame Start presses60frames apart. Abstract backend unless physical flag. No SNES display or MCU. Not proof of physical root cause.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(logtext[-3500:],flush=True)

if __name__=='__main__':main()
