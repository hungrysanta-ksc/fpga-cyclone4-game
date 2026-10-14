# SPDX-License-Identifier: MIT
"""174/175 loader differential, reset-release invariant and negative controls."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_timer175 import transform
from test_nes_legality174 import bench as previous

def bench():
    s=previous()
    for bit in range(4):
        pattern=rf'dut.reject_state\[{bit}\]=[^;]+;'
        m=re.search(pattern,s);assert m
        s=s[:m.end()]+m[0].replace('dut.','refdut.')+s[m.end():]
    marker='  $display("PASS STATE165 states=%0d sequences=%0d",checks,sequences);$finish;'
    assert s.count(marker)==1
    return s.replace(marker,'''  // BEGIN during each release edge must not escape IDLE. Pulse reset
  // at sub-cycle offsets, including a pulse entirely between clock edges.
  clear_commands();
  for(integer delay_ps=1;delay_ps<5952;delay_ps+=317)begin
   fresh();
   @(negedge mem_clk);#(delay_ps*0.001);reset=1;#0.020;
   if(dut.load_ready || refdut.load_ready)$fatal(1,"TIMER175 reset clamp");
   reset=0;load_begin=1;
   repeat(6)tick();load_begin=0;
   reset=1;tick();reset=0;repeat(4)tick();
  end
  $display("PASS TIMER175 states=%0d sequences=%0d reset_offsets=19",checks,sequences);$finish;''').replace(
    ' if(!$onehot(dut.phase))', ''' if(dut.release_reset!=0 && dut.phase[1])$fatal(1,"TIMER175 release invariant");
 if(!$onehot(dut.phase))''')

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True,exist_ok=False)
    old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.candidate/'nes_rom_loader.sv').read_text()
    assert new==transform(old)
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #'))
    (a.out/'candidate.sv').write_text(new);(a.out/'bench.sv').write_text(bench())
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert re.search(r'\*\* Fatal: (DIFF131|STATE165|TIMER175)',log) and 'PASS TIMER175' not in log,(label,log[-3000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Fatal|Error):',log),(label,log[-3000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','bench.sv'],'compile')
    args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    log=run('vsim',args,'equivalence');assert 'PASS TIMER175 states=294912 sequences=1056 reset_offsets=19' in log
    for label,needle,wrong in [
        ('ready','!reset && !fault && phase[RECEIVE] && loaded_bytes<total','!reset && !fault && loaded_bytes<total'),
        ('release',"else if(active_reset)phase<=16'b1;","else if(1'b0)phase<=16'b1;")]:
        assert new.count(needle)==1
        (a.out/(label+'.sv')).write_text(new.replace(needle,wrong))
        run('vlog',['-sv',label+'.sv'],label+'-compile');run('vsim',args,label,True)
    r=dict(passed=True,states=294912,sequences=1056,reset_offsets=19,negatives=['ready','release'],
        scope=__doc__,source_sha256=sha(a.candidate/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),
        bench_sha256=sha(a.out/'bench.sv'),public_sources={n:sha(ROOT/n) for n in [
        'tools/nes_ready175.py','tools/nes_timer175.py','tools/test_nes_timer175.py','tools/test_nes_legality174.py','tools/test_nes_directloader165.py',
        'tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']})
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS TIMER175 differential/reset/negative controls')
if __name__=='__main__':main()
