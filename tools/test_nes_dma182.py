# SPDX-License-Identifier: MIT
"""Execute actual182 DMA driver with asynchronous flags and every-byte faults."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_dma182 import bulk

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    for n in ['prior','out','gcc']:setattr(a,n,getattr(a,n).resolve())
    a.out.mkdir(parents=True,exist_ok=False)
    old=a.prior/'src/nes_native165_bulk.inc'
    (a.out/'nes_native165_bulk.inc').write_text(bulk(old.read_text()),encoding='utf8',newline='\n')
    inputs=['src/nes/firmware/nes_dma182.inc','src/nes/firmware/nes_rom_spi.h','tests/nes-functional/dma182_host.c','tools/nes_dma182.py','tools/test_nes_dma182.py']
    for n in inputs:shutil.copy2(ROOT/n,a.out/Path(n).name)
    for tag,cmd in [('build',[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','dma182_host.c','-o','host.exe']),('host',[a.out/'host.exe'])]:
        with (a.out/(tag+'.log')).open('wb') as f:
            r=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60)
        assert r.returncode==0,(tag,r.returncode,(a.out/(tag+'.log')).read_text(errors='replace')[-3000:])
    result=dict(passed=True,host=(a.out/'host.log').read_text().strip(),baseline_sha256=sha(old),
                driver_sha256=sha(a.out/'nes_native165_bulk.inc'),public_sources={n:sha(ROOT/n) for n in inputs},
                scope='Actual C + asynchronous register model. Not DMA bus/arbitration/WCET, FPGA or physical FPS proof.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
