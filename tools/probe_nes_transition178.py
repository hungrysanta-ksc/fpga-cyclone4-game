# SPDX-License-Identifier: MIT
"""START transition on actual CPU/PPU/MMC3, ideal ROM, exact177 collectors.

Uses deployed serial pad, no CPU RAM patch/ROM modification. Captures rejection
causes and per-frame joins even if a member never seals. Not physical timing.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess,os
from nes_game147 import ROOT,sha,VHDL
from probe_nes_admission176 import FILES,COLLECTORS,bench as intro_bench

def bench():
 s=intro_bench()
 s=s.replace('wire [4:0] joypad1_data=0,joypad2_data=0;', '''wire pad_serial,pad_ready,pad_trace_valid;wire [7:0] pad_trace_buttons;
 reg pad_commit=0;reg [15:0] pad_buttons=0;integer pad_file,scene_file,frame=0,ticks=0;
 wire [4:0] joypad1_data={4'd0,pad_serial},joypad2_data=0;
 nes_game_pad150 pad(.host_clk(clk),.nes_clk(clk),.reset(reset),.commit(pad_commit),
 .snes_buttons(pad_buttons),.host_ready(pad_ready),.strobe(joypad_out[0]),.read_clock(joypad_clock[0]),
 .serial(pad_serial),.trace_valid(pad_trace_valid),.trace_buttons(pad_trace_buttons));
 initial begin pad_file=$fopen("pad.tsv","w");scene_file=$fopen("scene.tsv","w");end
 always @(negedge clk)begin
  pad_commit=0;
  if(!reset&&pad_ready)begin
   // START30..33, release, START55..58, release, A80..83.
   pad_buttons=(frame>=30&&frame<34)||(frame>=55&&frame<59)?16'h1000:
               (frame>=80&&frame<84)?16'h0080:16'd0;
   pad_commit=1;
  end
 end
 always @(posedge clk)if(!reset&&pad_trace_valid)begin
  $fwrite(pad_file,"%0d %0d %02h\\n",frame,ticks,pad_trace_buttons);$fflush(pad_file);
 end
''')
 s=s.replace('integer target,unused,frame=0,fp=0,pixels=0,ticks=0,','integer target,unused,fp=0,pixels=0,')
 # Preserve old24/25 snapshots, add pictures around each real input.
 s=s.replace('if(frame==24 || frame==25)fp=', 'if(frame==24 || frame==25 || frame==29 || frame==40 || frame==54 || frame==65 || frame==79 || frame==95)fp=')
 # Scene logs before release-independent end markers; errors are split by owner.
 anchor='if(frame%10==0)$display'
 extra='''$fwrite(scene_file,"%0d %02h %0d %0d %07h %02h %02h %02h %0d %0d %0d %0d %0d %0d %0d %0d %0d %07h\\n",
 frame,native_display_mask,native_generation,native_geometry_valid,native_errors,
 native_frame.fetch_errors,native_frame.compact_errors,native_frame.raster_errors,
 native_frame_owned,native_active,native_frame.joining,native_frame.fetch_owned,
 native_frame.compact_owned,native_frame.raster_owned,native_group_count,native_object_count,native_exception_count,slow_errors);
 $fflush(scene_file);
 '''
 assert anchor in s;s=s.replace(anchor,extra+anchor)
 return s

def prepare(baseline,out,frames):
 baseline=baseline.resolve()
 assert not out.exists() and str(out).isascii() and 60<=frames<=240
 pins=json.loads((ROOT/'analysis/cross174-verification.json').read_bytes())['replay_inputs']
 deployed=json.loads((ROOT/'analysis/boundary177-verification.json').read_bytes())['verification']['sources']
 out.mkdir(parents=True)
 for n in FILES+['prg.hex','chr.hex']:
  assert sha(baseline/n)==pins[n],n
  if n in COLLECTORS:assert sha(baseline/n)==deployed[n],n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,out/n)
 pad=ROOT.parent/'probes/nes-boundary177/evidence/fit/nes_game_pad150.sv';assert sha(pad)==deployed[pad.name]
 shutil.copy2(pad,out/pad.name)
 (out/'native_frame165_tb.sv').write_text(bench(),encoding='utf8',newline='\n')
 r=dict(frames=frames,baseline=str(baseline),sources={n:sha(out/n) for n in FILES+['prg.hex','chr.hex',pad.name,'native_frame165_tb.sv']},
 public_sources={n:sha(ROOT/n) for n in ['tools/probe_nes_transition178.py','tools/probe_nes_admission176.py','tests/nes-functional/cross174_replay_tb.sv']},
 scope='Actual CPU/PPU/MMC3 and deployed pad/collectors; START30/55 and A80, idealROM. Immediate and held10 leases. No physical PSRAM/fill/export/SPI/SNES timing proof.')
 (out/'inputs.json').write_text(json.dumps(r,indent=2)+'\n');print('Prepared scene178')

def run(out,questa):
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 m=json.loads((out/'inputs.json').read_bytes())
 for n,h in m['sources'].items():assert sha(out/n)==h,n
 def call(exe,args,label):
  assert not (out/(label+'.log')).exists()
  with (out/(label+'.log')).open('wb') as f:r=subprocess.run([str(questa/(exe+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=14400)
  text=(out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3500:]
  return text
 call('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):call('vcom',['-2008',n],f'vcom-{i}')
 call('vlog',['-sv','-mfcu',*[n for n in FILES if n not in VHDL],'nes_game_pad150.sv','native_frame165_tb.sv'],'vlog')
 text=call('vsim',['-c','work.native_frame165_tb',f"+FRAMES={m['frames']}",'-do','onerror {quit -code 1}; run -all; quit -f'],'core')
 verify(out)

def verify(out):
 assert not (out/'result.json').exists()
 m=json.loads((out/'inputs.json').read_bytes())
 for n,h in m['sources'].items():assert sha(out/n)==h,n
 text=(out/'core.log').read_text(errors='replace')
 assert not re.search(r'\*\* (Error|Fatal):',text)
 assert f"PASS GAME147 frames={m['frames']} " in text
 baseline=Path(m['baseline'])
 if not baseline.is_absolute():baseline=ROOT/baseline # legacy preparation used repo-relative path
 old=(baseline/'states.tsv').read_text().splitlines();rows=(out/'states.tsv').read_text().splitlines();assert rows[:len(old)]==old
 for frame in [24,25]:assert (out/f'game-{frame}.hex').read_bytes()==(baseline/f'game-{frame}.hex').read_bytes()
 pads=[line.split() for line in (out/'pad.tsv').read_text().splitlines()]
 assert any(x[2]=='08' and 30<=int(x[0])<35 for x in pads)
 assert any(x[2]=='00' and 35<=int(x[0])<55 for x in pads)
 assert any(x[2]=='08' and 55<=int(x[0])<60 for x in pads)
 def summary(name):
  a=[line.split() for line in (out/name).read_text().splitlines()];bad={}
  for x in a:
   if x[2]=='0':bad[x[3]]=bad.get(x[3],0)+1
  return dict(samples=len(a),valid=sum(x[2]=='1' for x in a),rejected=bad)
 r=dict(completed=True,preinput26_states_equal=True,preinput24_25_pixels_equal=True,serial_START_and_release_verified=True,
 immediate=summary('states.tsv'),held10=summary('slow-states.tsv'),scope=m['scope'],logs={n:sha(out/n) for n in ['core.log','states.tsv','slow-states.tsv','pad.tsv','scene.tsv']})
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run','verify']);p.add_argument('--baseline',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=100);p.add_argument('--questa-bin',type=Path)
 a=p.parse_args()
 if a.mode=='prepare':prepare(a.baseline,a.out,a.frames)
 elif a.mode=='run':run(a.out,a.questa_bin)
 else:verify(a.out)
