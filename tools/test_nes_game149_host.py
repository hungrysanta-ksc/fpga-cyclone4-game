# SPDX-License-Identifier: MIT
"""Changed SPI engine and actual MCU full-size CHECK loop; no ROM assets."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
    src=a.arm/'src';assert sha(src/'nes_game149_spi.inc')==sha(ROOT/'src/nes/firmware/nes_game149_spi.inc')
    results={}
    for name,extra in [('spi',[]),('verify',['nes_rom_spi.c','nes_rom_verify.c'])]:
        exe=a.out/(name+'.exe')
        args=[str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-I',str(src),
              str(ROOT/'tests/nes-functional'/('game149_'+name+'_host.c')),
              *[str(src/n) for n in extra],'-o',str(exe)]
        for step,command in [('compile',args),('execute',[str(exe)])]:
            r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
            (a.out/(name+'-'+step+'.log')).write_bytes(r.stdout)
            assert r.returncode==0,(name,step,r.stdout.decode(errors='replace'))
        line=r.stdout.decode().strip();assert line.startswith('PASS149 '),line
        results[name]=line;print(line)
    assert 'cases=80' in results['spi'] and 'payload=393216' in results['verify']
    results.update(passed=True,production_sources={n:sha(src/n) for n in ['nes_game149_spi.inc','nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h']},
                   scope='Register and protocol peer models; no hardware, ARM execution, SD filesystem or physical PSRAM writes')
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
