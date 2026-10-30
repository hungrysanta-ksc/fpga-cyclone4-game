# SPDX-License-Identifier: MIT
"""Bounded actual493 PPU/collector replay of recorded179 register boundaries.

Deterministic external VRAM, no CPU/MMC3/PSRAM/game or FPS claim. Register-write
times come from a different PPU implementation; exercise0/1/3-dot offsets.
"""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/bus_savestates.vhd','rtl/regs_savestates.sv','rtl/ppu.sv',
       'nes_native_frame201.sv','nes_native_planes165.sv','nes_native_compact181.sv',
       'nes_native_raster181.sv','nes_patch_capture181.sv','nes_patch_rows181.sv']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def bench():
    s=(ROOT/'tests/nes-functional/patch_ppu181_tb.sv').read_text()
    s=s[:s.index(' wire begin_frame=')]
    s=s.replace('patch_ppu181_tb','capture500_tb')
    s=s.replace(' wire [1:0] sys_type', ''' reg oam_write=0;reg [7:0] oam_address=0;
 wire bg_low,bg_high,obj_low,obj_high,obj_valid,vram_read,address_valid;
 wire [7:0] obj_attribute,obj_x;wire [1:0] bg_attribute;
 wire [14:0] scroll_v,scroll_t;wire [2:0] fine_x,pattern_mode;
 wire [191:0] palette;wire scroll_access;
 wire [1:0] sys_type''')
    s=s.replace(' PPU ppu(',''' PPU ppu(.native_bg_low(bg_low),.native_bg_high(bg_high),
 .native_obj_low(obj_low),.native_obj_high(obj_high),.native_obj_valid(obj_valid),
 .native_obj_attribute(obj_attribute),.native_obj_x(obj_x),.tap_attribute(bg_attribute),
 .native_scroll_v(scroll_v),.native_scroll_t(scroll_t),.native_fine_x(fine_x),
 .native_pattern_mode(pattern_mode),.native_palette(palette),.native_scroll_access(scroll_access),
 .vram_r(vram_read),.rom_ppu_address_valid(address_valid),''')
    s=s.replace(".Savestate_OAMAddr(8'd0)",'.Savestate_OAMAddr(oam_address)')
    s=s.replace(".Savestate_OAMWrEn(1'b0),.Savestate_OAMWriteData(8'd0)",".Savestate_OAMWrEn(oam_write),.Savestate_OAMWriteData(8'hff)")
    return s+'''
 wire owned,geometry_valid;wire [24:0] errors,observe_errors;
 wire [7:0] rows,objects,exceptions,patch_errors;wire [5:0] groups,palettes;
 wire [2:0] patches;wire [15:0] generation;
 nes_native_frame201 capture(.clk(clk),.reset(reset),.release_frame(1'b0),.ppu_ce(ce),.rom_fault(1'b0),
 .scanline(scanline),.dot(cycle),.color(color),.emphasis(emphasis),
 .bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),.obj_valid(obj_valid),
 .extra_sprites(1'b0),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
 // Always-ready deterministic memory: collector ppu_valid is ROM DATA valid,
 // not PPU ALE/address-valid (which is false at the pattern load edge).
 .ppu_read(vram_read),.ppu_valid(1'b1),.logical_address(vram_addr),
 .physical_address(22'h200000+{9'd0,vram_addr[12:0]}),
 .scroll_v(scroll_v),.scroll_t(scroll_t),.fine_x(fine_x),.pattern_mode(pattern_mode),
 .display_mask(mask),.palette(palette),.scroll_access(scroll_access),
 .query(1'b0),.query_kind(3'd0),.query_index(13'd0),.query_generation(16'd0),
 .owned(owned),.geometry_valid(geometry_valid),.generation(generation),.errors(errors),
 .observe_errors180(observe_errors),.row_count(rows),.object_count(objects),
 .exception_count(exceptions),.group_count(groups),.palette_count(palettes),
 .patch_errors(patch_errors),.patch_count(patches));
 reg [5:0] pixels[0:57343];integer patch_row[0:6];reg sampled_ce=0;
 reg [7:0] old_errors=0;integer pixel_count=0,first_y=-1,first_x=-1;
 reg [8:0] cause_y,cause_x;reg [7:0] cause_mask;reg [13:0] cause_addr;
 reg cause_low,cause_high,cause_read,cause_pending;
 always @(posedge clk)if(ce)begin
  cause_y=scanline;cause_x=cycle;cause_mask=mask;cause_addr=vram_addr;
  cause_low=capture.fetch.low_event;cause_high=capture.fetch.high_event;
  cause_read=vram_read;cause_pending=capture.fetch.pair_pending;
  if($test$plusargs("TRACE") && (scanline==193 || scanline==194) &&
      capture.fetch.relevant && (capture.fetch.low_event || capture.fetch.high_event))
   $display("EVENT500 y=%0d x=%0d mask=%02h lo=%b hi=%b pending=%b oldrow=%0d newrow=%0d addr=%h oldaddr=%h address_ok=%b pair_ok=%b ordinary=%b bgpair=%b",
    scanline,cycle,mask,capture.fetch.low_event,capture.fetch.high_event,capture.fetch.pair_pending,
    capture.fetch.pair_description[32:25],capture.fetch.target_row,vram_addr,capture.fetch.pair_logical,
    capture.fetch.address_ok,capture.fetch.pair_ok,capture.fetch.ordinary_pair,capture.fetch.bg_pair);
 end
 always @(posedge clk)sampled_ce<=ce&&!reset;
 always @(negedge clk)begin
  if(sampled_ce && scanline>=8 && scanline<232 && cycle>=2 && cycle<=257)begin
   if($isunknown(color))$fatal(1,"unknown PPU pixel");
   pixels[(scanline-8)*256+cycle-2]=color;pixel_count++;
  end
  if(capture.row_commit && capture.row_patched && capture.row_slot<7)
   patch_row[capture.row_slot]=capture.committed_row;
  if(!reset && capture.fetch.errors!=old_errors)begin
   if(first_y<0)begin first_y=cause_y;first_x=cause_x;end
   $display("FETCH500 y=%0d x=%0d errors=%02h mask=%02h low=%b high=%b pending=%b addr=%h valid=%b read=%b",
    cause_y,cause_x,capture.fetch.errors,cause_mask,cause_low,cause_high,
    cause_pending,cause_addr,1'b1,cause_read);
   old_errors=capture.fetch.errors;
  end
 end
 integer event_y[0:63],event_x[0:63],event_a[0:63],event_v[0:63];
 integer events=0,fd,ret,n=0,at=0,checked=0;string stimulus;
 initial begin
  if(!$value$plusargs("STIMULUS=%s",stimulus))$fatal(1,"stimulus required");
  fd=$fopen(stimulus,"r");if(!fd)$fatal(1,"missing stimulus");
  while(!$feof(fd))begin
   ret=$fscanf(fd,"%d %d %d %d\\n",event_y[events],event_x[events],event_a[events],event_v[events]);
   if(ret==4)events++;else if(!$feof(fd))$fatal(1,"bad stimulus");
  end
  $fclose(fd);
  repeat(5)@(negedge clk);ss_reset=0;
  for(integer i=0;i<256;i++)begin oam_write=1;oam_address=i;@(negedge clk);end
  oam_write=0;repeat(5)@(negedge clk);reset=0;
  while(!owned)begin
   n++;ce=n%4==0;write=0;
   if(ce && scanline==0 && cycle==100)begin write=1;ain=1;din=8'h18;end
   if(ce && at<events && scanline==event_y[at] && cycle==event_x[at])begin
    write=1;ain=event_a[at];din=event_v[at];at++;
   end
   @(negedge clk);
  end
  ce=0;write=0;
  if(at!=events || pixel_count!=57344)$fatal(1,"incomplete events/pixels %0d/%0d pixels%0d",at,events,pixel_count);
  for(integer i=0;i<patches;i++)for(integer x=0;x<256;x++)begin
   if(capture.pixels.rows.pixels[i*256+x]!==pixels[patch_row[i]*256+x])$fatal(1,"retained pixel mismatch");
   checked++;
  end
  $display("RESULT500 valid=%0d errors=%07h fetch=%02h compact=%02h raster=%02h patch_errors=%02h patches=%0d exact_pixels=%0d first_y=%0d first_x=%0d rows=%0d",
   geometry_valid,errors,capture.fetch.errors,capture.compact.errors,capture.raster.errors,
   patch_errors,patches,checked,first_y,first_x,rows);
  $finish;
 end
 initial begin #10000000;$fatal(1,"bounded PPU watchdog");end
endmodule
'''

def prepare(board,reference,out,focus=None,phase_sweep=False):
    assert not out.exists();out.mkdir(parents=True)
    pins=json.loads((ROOT/'analysis/boot493-verification.json').read_text())['FPGA']['source_inputs']
    for n in FILES:
        assert sha(board/n)==pins[n],n
        p=out/n;p.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(board/n,p)
    ref=json.loads((reference/'result.json').read_text());assert sha(reference/'writes.tsv')==ref['trace_sha256']
    records=[l.split() for l in (reference/'writes.tsv').read_text().splitlines()]
    cases=[dict(name='baseline',frame=None,delay=0,address_writes=False,events=[])]
    for frame in [620,650,699]:
        for address in [False,True]:
            for delay in (range(8) if phase_sweep else [0,1,3]):
                events=[]
                for f,y,x,a,v in records:
                    if int(f)==frame and int(y) in [193,194] and (a=='2001' or address and a=='2006'):
                        xx=int(x)+delay;events.append([int(y)+xx//341,xx%341,int(a,16)&7,int(v,16)])
                cases.append(dict(name=f'f{frame}-addr{int(address)}-d{delay}',frame=frame,
                                  delay=delay,address_writes=address,events=events))
    if focus:cases=[c for c in cases if c['name'] in focus.split(',')]
    assert cases
    for c in cases:
        (out/(c['name']+'.txt')).write_text(''.join(' '.join(map(str,r))+'\n' for r in c['events']))
    (out/'capture500_tb.sv').write_text(bench(),encoding='utf8')
    data=dict(cases=cases,sources={n:sha(out/n) for n in FILES},testbench_SHA256=sha(out/'capture500_tb.sv'),
              reference_SHA256=ref['trace_sha256'],scope=__doc__)
    (out/'inputs.json').write_text(json.dumps(data,indent=2)+'\n');print('Prepared',len(cases),'cases',out)

def run(out,questa):
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    m=json.loads((out/'inputs.json').read_text())
    for n,h in m['sources'].items():assert sha(out/n)==h
    assert sha(out/'capture500_tb.sv')==m['testbench_SHA256']
    def call(exe,args,label):
        p=out/(label+'.log');assert not p.exists()
        with p.open('wb') as f:
            r=subprocess.run([str(questa/(exe+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=p.read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
        return s
    call('vlib',['work'],'vlib');call('vcom',['-2008',FILES[0]],'vcom')
    call('vlog',['-sv',*FILES[1:],'capture500_tb.sv'],'vlog')
    results=[]
    for c in m['cases']:
        s=call('vsim',['-L','altera_mf_ver','-c','work.capture500_tb','+TRACE','+STIMULUS='+c['name']+'.txt','-do','onerror {quit -code 1}; run -all; quit -f'],c['name'])
        row=re.search(r'RESULT500 (.*)',s);assert row,s[-2000:]
        if c['name']=='baseline':assert row[1].startswith('valid=1 errors=0000000 fetch=00'),row[1]
        results.append(dict(case=c,summary=row[1],log_SHA256=sha(out/(c['name']+'.log'))))
        print(c['name'],row[1],flush=True)
    (out/'result.json').write_text(json.dumps(dict(completed=True,results=results,inputs_SHA256=sha(out/'inputs.json'),scope=__doc__),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run'])
    for n in ['board','reference','out','questa-bin']:p.add_argument('--'+n,type=Path)
    p.add_argument('--focus')
    p.add_argument('--phase-sweep',action='store_true')
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.board,a.reference,a.out,a.focus,a.phase_sweep)
    else:run(a.out,a.questa_bin)
