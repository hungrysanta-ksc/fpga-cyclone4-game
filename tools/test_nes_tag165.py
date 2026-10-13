# SPDX-License-Identifier: MIT
"""Prove the new tag invariant on actual CHECK wiring and conditional steps."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_tag165 import transform
from test_nes_compare165 import bench as step_bench
from test_nes_check165 import REGS

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new==transform(old)
    a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1))
    (a.out/'candidate.sv').write_text(new)
    m=json.loads((a.prepared/'preparation.json').read_bytes())
    for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:
        assert sha(a.prepared/n)==m['sources'][n];(a.out/n).write_bytes((a.prepared/n).read_bytes())
    s=step_bench();needle='#1;mem_clk=1;#1;'
    assert s.count(needle)==2
    # This is a conditional one-step equivalence check, NOT an invariant proof.
    # The connected sequential test below checks establishment/preservation.
    s=s.replace(needle,' dut.check_request_tag=dut.check_next;\n'+needle)
    (a.out/'check165_tb.sv').write_text(s)
    s=(ROOT/'tests/nes-functional/tag165_tb.sv').read_text()
    regs=REGS+['pending_counter_clear','pending_counter_inc']
    s=s.replace('// COMPARE_ALL_REGISTERS','\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"TAG165 difference {n}");' for n in regs))
    (a.out/'tag165_tb.sv').write_text(s)
    def run(tool,args,label,expected=None):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if expected:assert expected in log and 'PASS TAG165' not in log,(label,log[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib')
    files=['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','check165_tb.sv','tag165_tb.sv']
    run('vlog',['-sv',*files],'compile')
    def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
    steps=run('vsim',sim('check165_tb'),'steps');assert 'PASS COMPARE165 states=1409024 captures=393216' in steps
    seq=run('vsim',sim('tag165_tb'),'sequential');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
    for name,needle,replacement in [
        ('capture','check_request_tag<=check_next;',"check_request_tag<=check_next ^ 19'h100;"),
        ('compare','check_response_address!=check_request_tag',"(check_response_address & 19'h7feff)!=(check_request_tag & 19'h7feff)")]:
        wrong=new.replace(needle,replacement);assert wrong!=new
        (a.out/(name+'-wrong.sv')).write_text(wrong)
        run('vlog',['-sv',name+'-wrong.sv'],name+'-compile')
        run('vsim',sim('tag165_tb'),name+'-negative','TAG165 invariant' if name=='capture' else 'TAG165 difference')
    sources=['tools/nes_tag165.py','tools/test_nes_tag165.py','tests/nes-functional/tag165_tb.sv','tools/test_nes_compare165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py']
    result=dict(passed=True,conditional_states=1409024,captures=393216,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],wrong_capture_rejected=True,missing_compare_bit_rejected=True,
        source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in sources})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
