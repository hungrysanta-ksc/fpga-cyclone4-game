# SPDX-License-Identifier: MIT
"""Same-edge comparison against selected predecode, including every mismatched bit."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_compare165 import transform
from test_nes_predecode165 import bench as previous_bench

def bench():
    s=previous_bench().replace('integer count=0;',"integer count=0;reg [18:0] mismatch=19'h40001;")
    for name in ['pending_counter_clear','pending_counter_inc']:
        s=re.sub(r'(dut\.'+name+r'=([^;]+);)',lambda m:m[1]+'refdut.'+name+'='+m[2]+';',s)
    assert s.count("n^19'h40001")==1;s=s.replace("n^19'h40001",'n^mismatch')
    needle='for(integer c=0;c<256;c++)'
    assert s.count(needle)==1
    s=s.replace(needle,'''// Every address bit, equal plus single-bit mismatch, across all lifecycle/fault flags.
 for(integer bitnum=0;bitnum<19;bitnum++)begin
  mismatch=19'b1<<bitnum;
  for(integer f=0;f<2048;f++)for(integer op=0;op<16;op++)
   step((19'h55555 ^ (19'b1<<bitnum)),f,op,0);
 end
 '''+needle)
    return s.replace('PASS PREDECODE165','PASS COMPARE165')

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text()
    assert new==transform(old);a.out.mkdir()
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1))
    (a.out/'candidate.sv').write_text(new);(a.out/'check165_tb.sv').write_text(bench())
    def run(tool,args,label,expected=None):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if expected:assert expected in log and 'PASS COMPARE165' not in log,(label,log[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','check165_tb.sv'],'compile')
    args=['-c','check165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    log=run('vsim',args,'equivalence');assert 'PASS COMPARE165 states=1409024 captures=393216' in log
    needle='assign counter_response_bit_ok[9]=!check_response || (check_response_address[9]==check_next[9]);'
    assert new.count(needle)==1
    (a.out/'wrong-bit.sv').write_text(new.replace(needle,"assign counter_response_bit_ok[9]=1'b1;"))
    run('vlog',['-sv','wrong-bit.sv'],'negative-compile');run('vsim',args,'negative','CHECK165 mismatch check_next')
    result=dict(passed=True,states=1409024,captures=393216,single_bit_response_cases=622592,wrong_response_bit_rejected=True,source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_compare165.py','tools/test_nes_compare165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
