# SPDX-License-Identifier: MIT
"""Replay already captured real-game pixels through new RTL; no CPU rerun."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_game150 import MODULES
from build_nes_game150 import build

def planar(pixels):
    out=bytearray(57344)
    for y in range(224):
        for x in range(256):
            v=pixels[(y+8)*256+x]&63;tile=(y//8)*32+x//8
            for p in range(6):
                off=tile*64+(p//2)*16+(y%8)*2+p%2
                out[off]|=((v>>p)&1)<<(7-x%8)
    return out

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
    e=a.baseline/'nes-game148/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game148-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files'];src=e/'core03/game-30.hex'
    assert sha(src)==pins['core03/game-30.hex']
    a.out.mkdir(parents=True);shutil.copy2(src,a.out/'pixels.hex')
    values=[int(v,16) for v in src.read_text().split()];assert len(values)==61440
    expected=planar(values);(a.out/'expected.hex').write_text(''.join(f'{v:02x}\n' for v in expected))
    (a.out/'expected.bin').write_bytes(expected)
    for n in MODULES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,a.out/n)
    shutil.copy2(ROOT/'tests/nes-functional/game150_video_tb.sv',a.out/'game150_video_tb.sv')
    shutil.copy2(build(a.out/'client'),a.out/'game-program.hex')
    def run(exe,args,log):
        with (a.out/log).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        s=(a.out/log).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-3000:])
        return s
    run('vlib',['work'],'vlib.log');run('vlog',['-sv',*MODULES,'game150_video_tb.sv'],'vlog.log')
    s=run('vsim',['-c','work.game150_video_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation.log')
    assert 'PASS GAME150' in s
    result=dict(passed=True,summary=re.search(r'PASS GAME150[^\r\n]+',s)[0],
      inputs={'pixels':sha(src)},sources={n:sha(a.out/n) for n in MODULES+['game150_video_tb.sv']},
      scope='Stored real-game frame replay; final pixel mapping, frozen ownership, continuous DMA address changes, pad serial order and reset. Not concurrent CPU/PPU or physical timing.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['summary'],flush=True)
if __name__=='__main__':main()
