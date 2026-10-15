# SPDX-License-Identifier: MIT
"""Actual board collector with original raster cycle-exact output comparison."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','board','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True);sources={}
    bp=json.loads((a.board/'preparation.json').read_bytes())['sources']
    names=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv',
           'nes_patch_rows181.sv','nes_patch_capture181.sv','nes_native_compact181.sv','nes_native_raster181.sv','nes_native_frame181.sv']
    for n in names:
        assert sha(a.board/n)==bp[n],n
        shutil.copy2(a.board/n,a.out/n);sources[n]=bp[n]
    original=a.baseline/'nes_native_raster181.sv'
    assert sha(original)==json.loads((ROOT/'analysis/board181-verification.json').read_bytes())['verification']['fits']['map03']['sources'][original.name]
    (a.out/'original.sv').write_text(original.read_text().replace('module nes_native_raster181(','module raster181_original('),encoding='utf8')
    tb=ROOT/'tests/nes-functional/collect181_tb.sv';s=tb.read_text()
    inputs=['clk','reset','release_packet','begin_packet','end_packet','ppu_ce','source_fault','scanline','dot',
            'scroll_v','scroll_t','fine_x','pattern_mode','display_mask','palette','scroll_access','row_commit','row_patched',
            'committed_row','row_slot','query','query_palette','query_row','query_bank','query_color']
    widths={'row_needs_patch':'','owned':'','valid':'','scroll_seen':'','errors':'[7:0]',
            'row_count':'[7:0]','palette_count':'[5:0]','response':'','hit':'','data':'[55:0]'}
    extra='\ninteger equivalent_cycles=0,copy_checks=0;\n'
    extra+='\n'.join('wire '+w+' reference_'+n+';' for n,w in widths.items())+'\n'
    extra+='raster181_original reference_raster(\n'+',\n'.join(
        ['.'+n+'(dut.raster.'+n+')' for n in inputs]+['.'+n+'(reference_'+n+')' for n in widths])+');\n'
    extra+='always @(posedge clk)begin #2; if(!reset)begin\n'
    for n in widths:
        extra+=' if(reference_'+n+'!==dut.raster.'+n+')$fatal(1,"palette mismatch '+n+'");\n'
    extra+=' if(dut.raster.copy_busy)begin\n'
    extra+='  if(dut.raster.copy_color!==reference_raster.held_palette[reference_raster.copy_offset*6+:6])$fatal(1,"palette selected color");\n'
    extra+='  copy_checks++;end\n equivalent_cycles++;end end\n'
    s=s.replace(' integer scenario=0,',extra+' integer scenario=0,')
    s=s.replace('$display("PASS COLLECT181','$display("PASS PALETTE181 cycles=%0d copy_checks=%0d",equivalent_cycles,copy_checks);\n  $display("PASS COLLECT181')
    (a.out/'bench.sv').write_text(s,encoding='utf8')
    def run(exe,args):
        with (a.out/(exe+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
        s=(a.out/(exe+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
        return s
    run('vlib',['work']);run('vlog',['-sv',*names,'original.sv','bench.sv'])
    s=run('vsim',['-c','work.collect181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    m=re.search(r'PASS COLLECT181 cases=(\d+) pixels=(\d+) baseline_words=(\d+) recovered_cells=(\d+)',s)
    eq=re.search(r'PASS PALETTE181 cycles=(\d+) copy_checks=(\d+)',s);assert m and eq and int(eq[2])>=32
    result=dict(passed=True,cases=int(m[1]),raw_pixels=int(m[2]),baseline_words=int(m[3]),recovered_cells=int(m[4]),
        equivalent_cycles=int(eq[1]),copy_checks=int(eq[2]),sources=sources,baseline_sha256=sha(original),
        generated_bench_sha256=sha(a.out/'bench.sv'),bench_public_sha256=sha(tb),runner_sha256=sha(Path(__file__)),hardware=False,
        scope='Synthetic PPU interface; original raster compared on every output and copied color. No latency change; not formal/full board or game proof.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0],eq[0])

if __name__=='__main__':main()
