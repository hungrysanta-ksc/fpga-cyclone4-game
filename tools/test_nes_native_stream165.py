# SPDX-License-Identifier: MIT
"""Collect actual SMB3 fetch/raster events once for bounded-producer replay.

This does not force CPU/PPU state, supply buttons or install firmware. Complete
CHR for subsequent PC comparison comes from the private ROM, not hardware fill.
"""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha
from nes_native_fetch165 import prepare,PORTS as FETCH_PORTS,BINDING
from nes_native_raster165 import PORTS as RASTER_PORTS

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--frames',type=int,default=20);a=p.parse_args()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost' and sha(a.rom)==ROM_SHA
 inputs=prepare(a.evidence,a.out);text=(ROOT/'tests/nes-functional/game147_tb.sv').read_text()
 def edit(old,new):
  nonlocal text
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
 edit('module game147_tb;','module native_stream165_tb;')
 ports=(FETCH_PORTS+RASTER_PORTS).replace('output wire','wire').replace('output reg','wire').replace(',\n',';\n')
 ports+='''wire [13:0] native_chr_logical;wire [21:0] game148_hint_physical;
 wire [63:0] ppu_fault_state154;wire game147_prefetch_hint,game160_restart_hint;
 wire [7:0] native_oam_address=0;wire [7:0] native_oam_data;wire native_oam_write;
'''
 edit('wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;',ports+'wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample;')
 edit('nes_rom_early rom_service(','''nes_rom_early rom_service(
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),''')
 edit('if(frame<=2 || frame%10==0 || frame==target)fp=', 'if(frame>0)fp=')
 bind=BINDING[BINDING.index('nes_native_fetch165 native_fetch('):BINDING.index('assign native_scene_owned=')]
 bind=bind.replace('.query(native_required_query && native_scene_owned)',".query(1'b0)").replace('.query_tile(native_required_tile)',".query_tile(13'd0)")
 monitor='''
 reg native_release_scene=0;wire native_required_initialized,native_required_active,native_required_owned,native_required_valid;
 wire [15:0] native_required_generation;wire native_fetch_event,native_required_response;wire [1:0] native_required_kind;
 wire [63:0] native_fetch_data;wire [7:0] native_fetch_errors;
 wire raster_owned,raster_valid;wire [7:0] raster_errors;
 nes_native_raster165 raster(
 .clk(clk),.reset(reset),.ppu_ce(tap_ce && (native_required_active || native_required_owned)),.scanline(scanline),.dot(cycle),
 .scroll_v(native_scroll_v),.scroll_t(native_scroll_t),.fine_x(native_fine_x),.pattern_mode(native_pattern_mode),
 .display_mask(native_display_mask),.palette(native_palette),.scroll_access(native_scroll_access),.source_fault(rom_fault),
 .release_packet(native_release_scene),.query(1'b0),.query_palette(1'b0),.query_row(8'd0),.query_bank(5'd0),.query_color(5'd0),
 .owned(raster_owned),.valid(raster_valid),.errors(raster_errors));
 integer events_file,rows_file,states_file;reg old_owned=0;
 initial begin
  events_file=$fopen("events.tsv","w");rows_file=$fopen("rows.tsv","w");states_file=$fopen("states.tsv","w");
 end
 always @(posedge clk)begin
  native_release_scene<=0;
  if(!reset)begin
   if(tap_ce && scanline==240 && cycle==2 && native_required_owned)native_release_scene<=1;
   if(native_fetch_event)$fwrite(events_file,"%0d %0d %016h\\n",native_required_generation,ticks,native_fetch_data);
   if(tap_ce && native_required_active && scanline>=8 && scanline<232 && cycle==1)
    $fwrite(rows_file,"%0d %0d %0d %02h %048h\\n",native_required_generation,scanline-8,native_fine_x,native_display_mask,native_palette);
   if(native_required_owned && !old_owned)begin
    $fwrite(states_file,"%0d %0d %0d %02h %0d %02h\\n",native_required_generation,frame,native_required_valid,native_fetch_errors,raster_valid,raster_errors);
    $fflush(events_file);$fflush(rows_file);$fflush(states_file);
   end
   old_owned<=native_required_owned;
  end
 end
'''
 edit('endmodule',monitor+bind+'\nendmodule')
 (a.out/'native_stream165_tb.sv').write_text(text,encoding='utf8')
 image=a.rom.read_bytes()
 for n,b in [('prg',image[16:0x40010]),('chr',image[0x40010:])]:
  (a.out/(n+'.hex')).write_text(''.join(f'{v:02x}\n' for v in b))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 additions=['nes_native_fetch165.sv','nes_native_raster165.sv','nes_native_ciram165.sv']
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,*additions,'native_stream165_tb.sv'],'vlog')
 s=run('vsim',['-c','work.native_stream165_tb',f'+FRAMES={a.frames}','-do','onerror {quit -code 1}; run -all; quit -f'],'core')
 assert 'PASS GAME147 frames=' in s
 result=dict(passed=True,rom_sha256=ROM_SHA,frames=a.frames,inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_native_stream165.py','tools/nes_native_fetch165.py','src/nes/diagnostic/nes_native_fetch165.sv','src/nes/diagnostic/nes_native_raster165.sv']},
  raw_sha256={n:sha(a.out/n) for n in ['events.tsv','rows.tsv','states.tsv','core.log']},
  scope='Actual SMB3 CPU/PPU/MMC3/70ns reader without buttons, preloaded ROM. Fetch+raster collection only; online producer replay is separate. No live hardware fill/host/SNES/fit proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual native stream collection',flush=True)
if __name__=='__main__':main()
