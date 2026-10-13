# SPDX-License-Identifier: MIT
"""Split cause storage compared through its logical projection and actual retirement."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_compare165 import transform,causes
from test_nes_compare165 import bench as compare_bench
from test_nes_check165 import REGS

def bench():
    s=compare_bench()
    s=s.replace("dut.pending_causes='0;", "dut.pending_causes='0;dut.pending_check_begin_error=0;dut.pending_check_read_error=0;")
    projection='{dut.pending_causes[4:3],(dut.pending_causes[2] | dut.pending_check_begin_error | dut.pending_check_read_error),dut.pending_causes[1:0]}'
    s=s.replace('if(dut.pending_causes!==refdut.pending_causes)',f'if({projection}!==refdut.pending_causes)')
    # Check both capture and the following retirement, not just projected storage.
    compare='\n'.join(f'if({projection if n=="pending_causes" else "dut."+n}!==refdut.{n})$fatal(1,"CAUSES165 retirement {n}");' for n in REGS)
    needle='mem_clk=0;#1;captures++;';assert s.count(needle)==1
    s=s.replace(needle,'mem_clk=0;#1;mem_clk=1;#1;\n'+compare+'\n mem_clk=0;#1;captures++;')
    # Independently vary every lifecycle input for all command identities.
    s=s.replace('input [6:0] f,input [7:0] argument','input [11:0] f,input [7:0] argument')
    s=s.replace('loaded=!f[5];run_enable=0;load_ready=!f[4];check_ready=1;','loaded=!f[5];run_enable=f[7];load_ready=!f[4];check_ready=!f[8];')
    s=s.replace('dut.check_busy=f[5];refdut.check_busy=dut.check_busy;','dut.check_busy=f[9];refdut.check_busy=dut.check_busy;')
    s=s.replace('dut.check_done=!f[5];refdut.check_done=dut.check_done;','dut.check_done=!f[10];refdut.check_done=dut.check_done;')
    s=s.replace('dut.next_below_length=!f[5];refdut.next_below_length=dut.next_below_length;','dut.next_below_length=!f[11];refdut.next_below_length=dut.next_below_length;')
    # Prior full capture matrix plus independent lifecycle sweep for relevant commands.
    needle='$display("PASS COMPARE165 states=%0d captures=%0d",count,captures);'
    assert s.count(needle)==1
    s=s.replace(needle,'''for(integer cmd=96;cmd<=106;cmd++)for(integer f=0;f<4096;f++)capture(cmd,f,0,0);
 $display("PASS CAUSES165 states=%0d captures=%0d",count,captures);''')
    return s

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new==causes(transform(old))
    a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1))
    (a.out/'candidate.sv').write_text(new);(a.out/'check165_tb.sv').write_text(bench())
    def run(tool,args,label,expected=None):
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if expected:assert expected in log and 'PASS CAUSES165' not in log,(label,log[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','check165_tb.sv'],'compile')
    args=['-c','check165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    assert 'PASS CAUSES165 states=1409024 captures=438272' in run('vsim',args,'equivalence')
    needle=' || pending_check_read_error)?4\'d6:';assert new.count(needle)==1
    (a.out/'wrong-cause.sv').write_text(new.replace(needle,")?4'd6:"))
    run('vlog',['-sv','wrong-cause.sv'],'negative-compile');run('vsim',args,'negative','CAUSES165 retirement')
    result=dict(passed=True,states=1409024,captures=438272,capture_retirement_checked=True,wrong_read_cause_rejected=True,source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_compare165.py','tools/test_nes_causes165.py','tools/test_nes_compare165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
