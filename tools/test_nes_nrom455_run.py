# SPDX-License-Identifier: MIT
"""Actual loader one-hot state and write-drain differential against selected RTL."""
import argparse,json,os,re,subprocess
from pathlib import Path
from nes_delta231 import BASE,sha
from prepare_nes_nrom455_run import transform
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True,type=Path);p.add_argument('--candidate',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--questa-bin',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.candidate/'nes_rom_loader.sv').read_text();assert new==transform(old);(d/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1));(d/'candidate.sv').write_text(new);(d/'bench.sv').write_bytes((BASE/'probes/nes-board206/test01/loader/bench.sv').read_bytes())
def run(tool,args,label,negative=False):
 with(d/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
 s=(d/(label+'.log')).read_text(errors='replace')
 if negative:assert '** Fatal:' in s and 'PASS STATE165' not in s
 else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
 return s
sim=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'];run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','bench.sv'],'compile');s=run('vsim',sim,'equivalence');assert 'states=294912 sequences=1056 exhaustive=524288' in s
needle='wire to_run=!fault && (';assert new.count(needle)==1;(d/'negative.sv').write_text(new.replace(needle,'wire to_run=1\'b1 && ('));run('vlog',['-sv','negative.sv'],'negative-compile');run('vsim',sim,'negative',True)
r={'passed':True,'states':294912,'write_sequences':1056,'count_cases':524288,'fault_negative_detected':True,'candidate_sha256':sha(d/'candidate.sv'),'reference_sha256':sha(d/'reference.sv'),'bench_sha256':sha(d/'bench.sv'),'scope':'one-step state sweep, timed byte-write sequences and count sweep; no full board or physical execution'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
