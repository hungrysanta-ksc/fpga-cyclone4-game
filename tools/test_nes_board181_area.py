# SPDX-License-Identifier: MIT
"""Collector suite plus cycle-exact old/new compact comparison for shared read.

Uses the prepared actual board collector files. Other board logic is synthesized
separately; this test is not a complete board/game/PSRAM execution.
"""
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
    old=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv']
    new=['nes_patch_rows181.sv','nes_patch_capture181.sv','nes_native_compact181.sv','nes_native_raster181.sv','nes_native_frame181.sv']
    for n in old+new:
        assert sha(a.board/n)==bp[n],n
        shutil.copy2(a.board/n,a.out/n);sources[n]=bp[n]
    original=ROOT/'src/nes/video/nes_native_compact181.sv'
    s=original.read_text().replace('module nes_native_compact181(','module compact181_original(')
    (a.out/'original.sv').write_text(s,encoding='utf8');sources['original_public']=sha(original)
    tb=ROOT/'tests/nes-functional/collect181_tb.sv';s=tb.read_text()
    inputs=['clk','reset','release_scene','begin_scene','end_scene','source_fault','event_valid','event_data',
            'row_commit','row_patched','committed_row','query','query_kind','query_address']
    widths={'row_needs_patch':'','active':'','owned':'','valid':'','errors':'[7:0]',
            'row_count':'[7:0]','object_count':'[7:0]','exception_count':'[7:0]',
            'group_count':'[5:0]','response':'','hit':'','data':'[63:0]'}
    extra='\ninteger equivalent_cycles=0;\n'
    extra+='\n'.join('wire '+w+' reference_'+n+';' for n,w in widths.items())+'\n'
    extra+='compact181_original reference_compact(\n'+',\n'.join(
        ['.'+n+'(dut.compact.'+n+')' for n in inputs]+['.'+n+'(reference_'+n+')' for n in widths])+');\n'
    extra+='always @(posedge clk)begin #2; if(!reset)begin\n'
    for n in widths:
        extra+=' if(reference_'+n+'!==dut.compact.'+n+')$fatal(1,"shared read mismatch '+n+'");\n'
    extra+=' equivalent_cycles++;end end\n'
    s=s.replace(' integer scenario=0,',extra+' integer scenario=0,')
    s=s.replace('$display("PASS COLLECT181', '$display("PASS SHARED181 cycles=%0d",equivalent_cycles);\n  $display("PASS COLLECT181')
    (a.out/'bench.sv').write_text(s,encoding='utf8');sources['bench_public']=sha(tb)
    def run(exe,args):
        with (a.out/(exe+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
        text=(a.out/(exe+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
        return text
    run('vlib',['work']);run('vlog',['-sv',*old,*new,'original.sv','bench.sv'])
    s=run('vsim',['-c','work.collect181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    m=re.search(r'PASS COLLECT181 cases=(\d+) pixels=(\d+) baseline_words=(\d+) recovered_cells=(\d+)',s)
    eq=re.search(r'PASS SHARED181 cycles=(\d+)',s);assert m and eq
    result=dict(passed=True,cases=int(m[1]),raw_pixels=int(m[2]),baseline_words=int(m[3]),recovered_cells=int(m[4]),
        equivalent_cycles=int(eq[1]),sources=sources,generated_bench_sha256=sha(a.out/'bench.sv'),
        runner_sha256=sha(Path(__file__)),hardware=False,
        scope='Prepared board collector hierarchy driven by synthetic PPU interface. Original181 compact compared on all output ports every clock; no event latency added. Not full board/game/physical.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(m[0],eq[0])

if __name__=='__main__':main()
