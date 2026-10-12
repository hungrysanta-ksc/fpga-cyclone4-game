# SPDX-License-Identifier: MIT
"""Observe actual low/high fetch pairs and the BgPainter bytes they load.

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
 edit('module game147_tb;','module native_pair165_tb;')
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
 monitor+=r'''
 integer pair_file,replay_file,painter_checks=0,rejected_pairs=0;
 reg [7:0] observed_low,observed_high;
 reg [7:0] reverse_low,reverse_high;
 integer bit_index;
 initial begin pair_file=$fopen("pairs.tsv","w");replay_file=$fopen("replay.tsv","w");end
 always @(posedge clk)begin
  if(!reset && native_required_initialized && tap_ce &&
     (native_fetch.begin_frame || native_fetch.end_frame ||
      (native_fetch.capturing && native_fetch.relevant && (native_fetch.low_event || native_fetch.high_event))))begin
   $fwrite(replay_file,"%0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %02h %02h %0d %0d %04h %06h %02h\n",
    frame,ticks,scanline,cycle,native_bg_low,native_bg_high,native_obj_low,native_obj_high,native_obj_valid,
    native_extra_sprites,tap_attribute,native_obj_attribute,native_obj_x,ppumem_read,rom_ppu_valid,native_chr_logical,ppumem_addr,ppumem_din);
  end
  if(!reset && tap_ce && native_fetch.capturing && native_fetch.relevant && native_bg_low)
   observed_low=ppumem_din;
  if(!reset && tap_ce && native_fetch.capturing && native_fetch.relevant && native_bg_high)begin
   observed_high=ppumem_din;
   if(dut.core.ppu.bg_painter.bg0!==observed_low || dut.core.ppu.bg_painter.bg1!==observed_high)
    $fatal(1,"actual BgPainter input does not match observed ROM bytes");
   painter_checks=painter_checks+1;
   if(!native_fetch.pair_ok)begin
    rejected_pairs=rejected_pairs+1;
    $fwrite(pair_file,"%0d %0d %0d %0d %06h %06h %04h %04h %016h %016h %02h %02h %0d %0d %0d %04h %0d\n",
     frame,ticks,scanline,cycle,native_fetch.pair_address,ppumem_addr,native_fetch.pair_logical,native_chr_logical,
     native_fetch.pair_description,native_fetch.description,observed_low,observed_high,
     native_fetch.pair_pending,native_fetch.address_ok,native_chr_logical[3],native_scroll_v,native_scroll_access);
    $fflush(pair_file);
   end
   for(bit_index=0;bit_index<8;bit_index=bit_index+1)begin
    reverse_low[bit_index]=observed_low[7-bit_index];reverse_high[bit_index]=observed_high[7-bit_index];
   end
   #1;
   if(dut.core.ppu.bg_painter.playfield_pipe_1[15:8]!==reverse_low ||
      dut.core.ppu.bg_painter.playfield_pipe_2[15:8]!==reverse_high)
    $fatal(1,"actual BgPainter did not load observed low/high planes");
  end
 end
 final begin $display("PAIR165 painter_checks=%0d rejected_pairs=%0d",painter_checks,rejected_pairs);end
'''
 edit('endmodule',monitor+bind+'\nendmodule')
 (a.out/'native_pair165_tb.sv').write_text(text,encoding='utf8')
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
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,*additions,'native_pair165_tb.sv'],'vlog')
 s=run('vsim',['-c','work.native_pair165_tb',f'+FRAMES={a.frames}','-do','onerror {quit -code 1}; run -all; quit -f'],'core')
 assert 'PASS GAME147 frames=' in s
 counts=re.search(r'PAIR165 painter_checks=(\d+) rejected_pairs=(\d+)',s);assert counts
 assert int(counts[1])>0 and int(counts[2])>0
 result=dict(passed=True,painter_checks=int(counts[1]),rejected_pairs=int(counts[2]),rom_sha256=ROM_SHA,frames=a.frames,inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_native_pair165.py','tools/nes_native_fetch165.py','src/nes/diagnostic/nes_native_fetch165.sv','src/nes/diagnostic/nes_native_raster165.sv']},
  raw_sha256={n:sha(a.out/n) for n in ['events.tsv','rows.tsv','states.tsv','pairs.tsv','replay.tsv','core.log']},
  scope='Actual SMB3 CPU/PPU/MMC3/70ns reader without buttons, preloaded ROM. Fetch+raster collection only; online producer replay is separate. No live hardware fill/host/SNES/fit proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual native stream collection',flush=True)
if __name__=='__main__':main()
