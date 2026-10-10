# SPDX-License-Identifier: MIT
"""Causal70ns replay of the first real SMB3 PPUDATA deadline boundary."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
    m=json.loads((a.prepared/'result.json').read_bytes());assert m['prefetch']
    a.out.mkdir();names=['nes_rom_service.sv','nes_rom_physical.sv']
    for n in names:
        assert sha(a.prepared/n)==m['sources'][n],n
        shutil.copy2(a.prepared/n,a.out/n)
    shutil.copy2(ROOT/'tests/nes-functional/game147_prefetch_tb.sv',a.out/'game147_prefetch_tb.sv')
    def run(exe,args,log):
        with (a.out/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=(a.out/log).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2500:]);return s
    run('vlib',['work'],'vlib.log');run('vlog',['-sv','-mfcu',*names,'game147_prefetch_tb.sv'],'vlog.log')
    s=run('vsim',['-c','work.game147_prefetch_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation.log')
    assert 'PASS PREFETCH147 ALL' in s
    result=dict(passed=True,cases=re.findall(r'PASS PREFETCH147 enable=[^\r\n]+',s),
                sources={n:sha(a.out/n) for n in names+['game147_prefetch_tb.sv']},
                scope='Seeded game-prefix two-cache-byte state,70ns physical reader, phases0/3.5ns. Prefetch enabled meets deadline; disabled must report PPU error2. Not all PPUDATA timing, whole game, fitted board, or native SNES display proof.')
    assert len(result['cases'])==4
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(result['cases']),flush=True)
if __name__=='__main__':main()
