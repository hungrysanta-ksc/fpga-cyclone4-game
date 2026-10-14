# SPDX-License-Identifier: MIT
"""Exact178 collectors with actual SMB3 CPU/PPU/MMC3 and serial pad.

Ideal ROM only. One immediate consumer avoids repeating the old held-intro
test. Private pixel/tap evidence must establish the actual reached scene.
No ROM or CPU RAM patches, physical PSRAM, export, SPI or SNES timing claim.
"""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_game147 import ROOT, sha, VHDL
from probe_nes_admission176 import FILES, COLLECTORS
from probe_nes_transition178 import bench as old_bench


def bench():
    s = old_bench()
    # The prior second collector was useful for ownership testing, but this
    # investigation needs the first failed frame, not another held-intro run.
    begin = s.index('reg slow_release_frame')
    s = s[:begin] + 'endmodule\n'
    s = s.replace('slow_errors);', "25'd0);")
    s = s.replace('frame>=55&&frame<59', 'frame>=90&&frame<96')
    s = s.replace('(frame>=80&&frame<84)?16\'h0080:16\'d0;', """(frame>=400&&frame<420)?16'h0100:
               (frame>=450&&frame<470)?16'h0800:
               (frame>=500&&frame<506)?16'h0080:16'd0;""")
    s = s.replace('// START30..33, release, START55..58, release, A80..83.',
                  '// START30/90; RIGHT400; UP450 to tile1; A500. Release between.')
    picture = 'if(frame==24 || frame==25 || frame==29 || frame==40 || frame==54 || frame==65 || frame==79 || frame==95)fp='
    assert picture in s
    s = s.replace(picture, 'if(frame==24 || frame==25 || frame==95 || frame==180 || frame==350 || frame==430 || frame==480 || frame==550 || frame==600 || frame==650)fp=')
    # Full queries only at baseline snapshots; row/error evidence is every frame.
    s = s.replace('if(frame==24 || frame==25)begin', 'if(frame==24 || frame==25 || frame==480 || frame==650)begin')
    anchor = 'nes_native_frame165 native_frame('
    assert anchor in s
    extra = '''
 integer failure_file,mask_file;
 reg [7:0] old_fetch_errors=0,old_compact_errors=0,old_raster_errors=0,old_mask=0;
 initial begin failure_file=$fopen("first-errors.tsv","w");mask_file=$fopen("mask.tsv","w");end
 always @(negedge clk) if(!reset)begin
  if(native_frame.fetch_errors!=old_fetch_errors || native_frame.compact_errors!=old_compact_errors || native_frame.raster_errors!=old_raster_errors)begin
   $fwrite(failure_file,"%0d %0d %0d %02h %02h %02h %02h %0d %0d %0d %0d %0d %0d\\n",
    frame,scanline,cycle,native_display_mask,native_frame.fetch_errors,native_frame.compact_errors,native_frame.raster_errors,
    native_row_count,native_group_count,native_object_count,native_exception_count,native_palette_count,native_frame.compact.column);
   $fflush(failure_file);
  end
  old_fetch_errors=native_frame.fetch_errors;old_compact_errors=native_frame.compact_errors;old_raster_errors=native_frame.raster_errors;
  if(native_display_mask!=old_mask)begin
   $fwrite(mask_file,"%0d %0d %0d %02h\\n",frame,scanline,cycle,native_display_mask);$fflush(mask_file);
  end
  old_mask=native_display_mask;
 end
'''
    return s.replace(anchor, extra+anchor, 1)


def prepare(baseline, deployed, out, frames):
    assert not out.exists() and str(out).isascii() and 27 <= frames <= 1200
    baseline=baseline.resolve(); deployed=deployed.resolve()
    pins=json.loads((ROOT/'analysis/cross174-verification.json').read_bytes())['replay_inputs']
    hpins=json.loads((deployed.parent/'manifest01.json').read_bytes())
    pad=ROOT.parent/'probes/nes-boundary177/evidence/fit/nes_game_pad150.sv'
    padpins=json.loads((ROOT/'analysis/boundary177-verification.json').read_bytes())['verification']['sources']
    out.mkdir(parents=True)
    for n in FILES+['prg.hex','chr.hex']:
        src=deployed/n if n in COLLECTORS else baseline/n
        assert sha(src)==(hpins['sources/'+n] if n in COLLECTORS else pins[n]), n
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    assert sha(pad)==padpins[pad.name];shutil.copy2(pad,out/pad.name)
    (out/'native_frame165_tb.sv').write_text(bench(),encoding='utf8',newline='\n')
    info=dict(frames=frames,baseline=str(baseline),sources={n:sha(out/n) for n in FILES+['prg.hex','chr.hex',pad.name,'native_frame165_tb.sv']},
              public_sources={n:sha(ROOT/n) for n in ['tools/probe_nes_level179.py','tools/probe_nes_transition178.py','tools/probe_nes_admission176.py','tests/nes-functional/cross174_replay_tb.sv']},scope=__doc__)
    (out/'inputs.json').write_text(json.dumps(info,indent=2)+'\n');print('Prepared level179',out)


def run(out, questa):
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    m=json.loads((out/'inputs.json').read_bytes())
    for n,h in m['sources'].items():assert sha(out/n)==h,n
    def call(exe,args,label):
        assert not (out/(label+'.log')).exists()
        with (out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(questa/(exe+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=21600)
        text=(out/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3500:]
        return text
    call('vlib',['work'],'vlib')
    for i,n in enumerate(VHDL):call('vcom',['-2008',n],f'vcom-{i}')
    call('vlog',['-sv','-mfcu',*[n for n in FILES if n not in VHDL],'nes_game_pad150.sv','native_frame165_tb.sv'],'vlog')
    text=call('vsim',['-c','work.native_frame165_tb',f"+FRAMES={m['frames']}",'-do','onerror {quit -code 1}; run -all; quit -f'],'core')
    assert f"PASS GAME147 frames={m['frames']} " in text
    baseline=Path(m['baseline'])
    assert (out/'states.tsv').read_text().splitlines()[:26]==(baseline/'states.tsv').read_text().splitlines()[:26]
    for f in [24,25]:assert (out/f'game-{f}.hex').read_bytes()==(baseline/f'game-{f}.hex').read_bytes()
    result=dict(completed=True,baseline26_states_equal=True,baseline24_25_pixels_equal=True,
                scope=m['scope'],scene_confirmation_required=True,
                logs={n:sha(out/n) for n in ['core.log','states.tsv','pad.tsv','scene.tsv','mask.tsv','first-errors.tsv']})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
    for n in ['baseline','deployed','out','questa-bin']:p.add_argument('--'+n,type=Path)
    p.add_argument('--frames',type=int,default=650);a=p.parse_args()
    if a.mode=='prepare':prepare(a.baseline,a.deployed,a.out,a.frames)
    else:run(a.out,a.questa_bin)
