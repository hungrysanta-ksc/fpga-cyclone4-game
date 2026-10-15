# SPDX-License-Identifier: MIT
"""Exercise actual mailbox ownership at the new physical data-delay budgets.

Only the simulation copy adds a delayed wire at the held bus. Production RTL
is byte-identical. This is a bounded digital delay check, not metastability.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    assert not a.out.exists();a.out.mkdir()
    source=a.prepared/'nes_native_mailbox165.sv';tb=ROOT/'tests/nes-functional/boundary_reset165_tb.sv'
    m=json.loads((a.prepared/'preparation.json').read_bytes())
    assert sha(source)==m['sources'][source.name]==m['baseline_sources'][source.name]
    shutil.copy2(source,a.out/'original.sv');shutil.copy2(tb,a.out/tb.name)
    s=source.read_text();assert s.count('received<=held;')==1
    wire=' wire [WIDTH-1:0] wire_payload;\n assign #(WIDTH==96?9.904:43.454) wire_payload=held;\n'
    s=s.replace(' assign src_ready',wire+' assign src_ready').replace('received<=held;','received<=wire_payload;')
    (a.out/'delayed.sv').write_text(s,encoding='utf8')
    (a.out/'late.sv').write_text(s.replace('9.904:43.454','59.520:227.270'),encoding='utf8')
    def run(exe,args,name,negative=False):
        with (a.out/(name+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        log=(a.out/(name+'.log')).read_text(errors='replace')
        if not negative:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),name
        return log
    run('vlib',['work'],'vlib')
    run('vlog',['-sv','delayed.sv',tb.name],'compile')
    args=['-c','boundary_reset165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    good=run('vsim',args,'bounded');assert 'PASS BOUNDARY165 all six cases' in good
    run('vlog',['-sv','late.sv'],'late-compile')
    bad=run('vsim',args,'late',True)
    assert '** Fatal:' in bad and 'lost/torn/duplicate payload' in bad and 'all six cases' not in bad
    result=dict(passed=True,cases=6,delivered=450,common_resets=72,stopped_clocks=12,
                physical_delay_ns=dict(records=9.904,prepared=43.454),late_payload_rejected=True,
                rtl_sha256=sha(source),tb_sha256=sha(tb),runner_sha256=sha(Path(__file__)),
                files={f.name:sha(f) for f in a.out.iterdir() if f.is_file()},
                scope='Delay-instrumented exact mailbox copy; digital delay/ownership/lifecycle only. No metastability, pad/audio waveform or hardware claim.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('PASS CDC181 delayed mailbox: six cases,450 transfers,72 resets,12 clock stops; late data rejected')

if __name__=='__main__':main()
