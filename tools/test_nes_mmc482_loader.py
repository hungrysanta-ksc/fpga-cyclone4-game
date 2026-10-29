# SPDX-License-Identifier: MIT
"""482 same-edge loader equivalence against selected481, including prior codes.

One authorized FLOAT seat, sequential runs. Does not repeat the full ROM load.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from prepare_nes_mmc482 import transform

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['old', 'new', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
p.add_argument('--bin', type=Path, default=Path('C:/altera_standard/25.1std/questa_fse/win64'))
a = p.parse_args()
d = a.out.resolve()
d.mkdir(parents=True, exist_ok=False)
old = a.old.read_text(encoding='utf8')
new = a.new.read_text(encoding='utf8')
assert new == transform(old)
(d/'reference.sv').write_text(old.replace('module nes_rom_loader #', 'module nes_rom_loader_reference #'), encoding='utf8')
(d/'candidate.sv').write_text(new, encoding='utf8')
b = ROOT.parent/'probes/nes-board206/test01/loader/bench.sv'
s = b.read_text(encoding='utf8')
anchor = '  sequential=0;\n  for(integer v=0;v<524288;v++)begin'
assert s.count(anchor) == 1
extra = '''  sequential=0;
  for(integer st=0;st<16;st++)for(integer c=0;c<64;c++)
  for(integer prior=0;prior<16;prior++)for(integer blocked=0;blocked<2;blocked++)
  for(integer complete=0;complete<2;complete++)for(integer sticky=0;sticky<2;sticky++)begin
   @(negedge mem_clk);clear_commands();
   {load_begin,load_valid,load_end,start,stop,load_chr32}=c;commands_blocked=blocked;
   dut.phase=16'b1<<st;refdut.phase=16'b1<<st;
   dut.error_code=prior;refdut.error_code=prior;dut.fault=sticky;refdut.fault=sticky;
   dut.count_complete=complete;refdut.count_complete=complete;
   @(posedge mem_clk);#0.01;
   if(dut.error_code!==refdut.error_code)$fatal(1,"CODE482 state=%0d command=%0d prior=%0d blocked=%0d complete=%0d fault=%0d got=%h expected=%h",st,c,prior,blocked,complete,sticky,dut.error_code,refdut.error_code);
  end
  @(negedge mem_clk);clear_commands();commands_blocked=0;
'''
s = s.replace(anchor, extra+anchor).replace('#30000000;', '#40000000;')
s = s.replace('exhaustive=524288"', 'exhaustive=524288 codes=131072"')
(d/'bench.sv').write_text(s, encoding='utf8')

def run(label, cmd, negative=False):
    with (d/(label+'.log')).open('wb') as f:
        r = subprocess.run([str(a.bin/(cmd[0]+'.exe')), *cmd[1:]], cwd=d,
                           stdout=f, stderr=subprocess.STDOUT, timeout=240)
    text = (d/(label+'.log')).read_text(encoding='utf8', errors='replace')
    if negative:
        assert re.search(r'\*\* Fatal: (DIFF131|CODE482|STATE165)', text) and 'PASS STATE165' not in text
    else:
        assert r.returncode == 0 and not re.search(r'\*\* (Error|Fatal):', text), label
    return text

run('vlib', ['vlib', 'work'])
run('compile', ['vlog', '-sv', 'reference.sv', 'candidate.sv', 'bench.sv'])
args = ['vsim', '-c', 'counter131_diff_tb', '-do', 'onerror {quit -code 1};run -all;quit -f']
text = run('equivalence', args)
assert 'states=294912 sequences=1056 exhaustive=524288 codes=131072' in text
for label, bad in [('blocked-stop', new.replace("error_code<=4'd6", "error_code<=4'd2")),
                   ('blocked-gate', new.replace('if(commands_blocked)begin', "if(1'b0)begin"))]:
    assert bad != new
    (d/'wrong.sv').write_text(bad, encoding='utf8')
    run(label+'-compile', ['vlog', '-sv', 'wrong.sv'])
    run(label+'-negative', args, True)
r = {'passed': True, 'scope': __doc__, 'states': 294912, 'sequences': 1056,
     'exhaustive_counts': 524288, 'prior_code_cases': 131072,
     'negative_controls': ['blocked STOP wrong code', 'blocked-command gate bypass'],
     'old_SHA256': sha(a.old), 'new_SHA256': sha(a.new), 'bench_base_SHA256': sha(b),
     'physical': False}
(d/'result.json').write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
print(json.dumps({'passed': True, 'states': 294912, 'sequences': 1056, 'prior_codes': 131072, 'negative_controls': 2}))
