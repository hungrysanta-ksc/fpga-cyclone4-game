# SPDX-License-Identifier: MIT
"""Private exact-ROM bonus entry on selected NES/mapper/reader RTL.

One-shot map coordinate intervention, then normal pad input. No production
patches, deadline relaxation, source/tile contention or SNES display claim.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha

def prepare(board,rom,out):
 assert not out.exists() and str(out).isascii() and sha(rom)==ROM_SHA
 out.mkdir(parents=True)
 files=VHDL+SV+EXTRA+['nes_native_ciram165.sv','nes_game_pad150.sv']
 for n in files:
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(board/n,dst)
 data=rom.read_bytes()
 for n,d in [('prg',data[16:0x40010]),('chr',data[0x40010:])]:
  (out/(n+'.hex')).write_text(''.join(f'{v:02x}\n' for v in d))
 s=(ROOT/'tests/nes-functional/game147_tb.sv').read_text()
 extra='''wire game160_restart_hint,game147_prefetch_hint;wire [21:0] game148_hint_physical;
 wire [63:0] ppu_fault_state154;wire [13:0] native_chr_logical;
 wire pad_serial,pad_ready,pad_trace_valid;wire [7:0] pad_trace_buttons;
 reg pad_commit=0;reg [15:0] pad_buttons=0;
 nes_game_pad150 pad(.host_clk(clk),.nes_clk(clk),.reset(reset),.commit(pad_commit),
 .snes_buttons(pad_buttons),.host_ready(pad_ready),.strobe(joypad_out[0]),.read_clock(joypad_clock[0]),
 .serial(pad_serial),.trace_valid(pad_trace_valid),.trace_buttons(pad_trace_buttons));
 always @(negedge clk)begin
  pad_commit=0;
  if(!reset&&pad_ready)begin
   pad_buttons=(frame>=30&&frame<34)||(frame>=90&&frame<96)?16'h1000:
    (frame>=360&&frame<366)||(frame>=550&&frame<556)?16'h0080:16'd0;
   pad_commit=1;
  end
 end
 integer trace_file,scene_file;reg cheated=0;
 initial begin trace_file=$fopen("rom-tail.tsv","w");scene_file=$fopen("scene.tsv","w");end
 always @(negedge clk)if(!reset)begin
  if(frame==350&&!cheated)begin
   $display("CHEAT698 before y=%h x=%h",local_memory.cpu_ram.mem['h75],local_memory.cpu_ram.mem['h79]);
   local_memory.cpu_ram.mem['h75]='h60;local_memory.cpu_ram.mem['h79]='h80;
   cheated=1;$display("CHEAT698 released frame=%0d",frame);
  end
  if(frame>=350 && scanline==192 && cycle>=254 && cycle<=266)
   $fwrite(trace_file,"%0d %0d %0d %0d %04h %06h %b %b %b %b %b %06h %b %06h %0d %016h\\n",
    ticks,frame,scanline,cycle,native_chr_logical,ppumem_addr,rom_ppu_address_valid,
    tap_ce&&ppumem_read,rom_ppu_valid,rom_ready,rom_request,rom_address,
    rom_response,rom_response_address,rom_service.age,ppu_fault_state154);
  if(cycle==1 && scanline==240 && tap_ce)begin
   $fwrite(scene_file,"%0d %02h %02h %02h %02h %02h %02h\\n",frame,
    local_memory.cpu_ram.mem['h75],local_memory.cpu_ram.mem['h79],local_memory.cpu_ram.mem['he5],
    local_memory.cpu_ram.mem['h70a],local_memory.cpu_ram.mem['h408],local_memory.cpu_ram.mem['h409]);
   $fflush(scene_file);$fflush(trace_file);
  end
 end
'''
 declarations,body=extra.split(' nes_game_pad150 pad(',1)
 s=s.replace('wire [4:0] joypad1_data=0,joypad2_data=0;',declarations+"\n wire [4:0] joypad1_data={4'd0,pad_serial},joypad2_data=0;")
 s=s.replace('reg [255:0] history[0:15];integer hi=0;', 'reg [255:0] history[0:15];integer hi=0;\n nes_game_pad150 pad('+body)
 # Bind every selected probe port explicitly; extra observations are unused.
 h=(board/'nes_probe.sv').read_text().split(');',1)[0]
 known=set(re.findall(r'\b\w+\b',s))
 conn=[]
 for direction,width,names in re.findall(r'\b(input|output)\s+wire\s*(\[[^\]]+\])?\s*(.*?)(?=\binput\b|\boutput\b|$)',h,re.S):
  for n in names.strip().strip(',').split(','):
   n=n.strip()
   if n:conn.append('.'+n+'('+ (n if n in known else ("'0" if direction=='input' else '')) +')')
 s=s.replace('nes_probe dut(.*);','nes_probe dut('+','.join(conn)+');')
 s=s.replace('nes_rom_early rom_service(','''nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),''')
 s=s.replace('nes_local_memory local_memory(',"nes_local_memory local_memory(.native_nt_address(11'd0),")
 # Fault history must be captured before the model deliberately stops.
 s=s.replace('if(rom_fault)$fatal', '''if(fault_trigger)begin
   for(integer h=0;h<16;h++)$display("HISTORY698 %064h",history[(hi+h)%16]);
   $display("FAULT698 tick=%0d frame=%0d line=%0d dot=%0d context=%h ppu=%h",ticks,frame,scanline,cycle,fault_context,ppu_fault_state154);
   $fflush(trace_file);$fflush(scene_file);
  end
  if(rom_fault)$fatal''')
 s=s.replace('if(frame<=2 || frame%10==0 || frame==target)fp=', 'if(frame==349 || frame==355 || frame==540 || frame==650 || frame==target)fp=')
 (out/'game147_tb.sv').write_text(s,encoding='utf8',newline='\n')
 meta=dict(stage=698,scope=__doc__,board=str(board),rom_sha256=ROM_SHA,
  sources={n:sha(out/n) for n in files+['game147_tb.sv']},frames=680,
  intervention={'frame':350,'cpu_ram':{'0075':'60','0079':'80'},'one_shot':True},
  pad='START30..33/90..95; A360..365/550..555; release between')
 (out/'inputs.json').write_text(json.dumps(meta,indent=2)+'\n')
 return meta

def run(out,questa):
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 m=json.loads((out/'inputs.json').read_bytes())
 for n,h in m['sources'].items():assert sha(out/n)==h,n
 def call(exe,args,label):
  with (out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(questa/(exe+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=18000)
  t=(out/(label+'.log')).read_text(errors='replace')
  if label!='simulation':assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-4000:]
  return r.returncode,t
 call('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):call('vcom',['-2008',n],f'vcom-{i}')
 call('vlog',['-sv','-mfcu',*[n for n in m['sources'] if n not in VHDL]],'vlog')
 rc,t=call('vsim',['-L','altera_mf_ver','-c','work.game147_tb',f"+FRAMES={m['frames']}",'-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
 result=dict(returncode=rc,rom_faults=re.findall(r'FAULT698[^\r\n]+',t),
  completed='PASS GAME147' in t or 'DONE698' in t,simulation_sha256=sha(out/'simulation.log'))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 assert result['completed'] or result['rom_faults'],t[-4000:]

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
 for n in ['board','rom','out','questa-bin']:p.add_argument('--'+n,type=Path)
 a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.board,a.rom,a.out)))
 else:run(a.out,a.questa_bin)
