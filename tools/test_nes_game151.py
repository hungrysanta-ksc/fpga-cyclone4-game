# SPDX-License-Identifier: MIT
"""151 changed write boundary: causal150 controls and stored game replay."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from build_nes_game151 import build
def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
    a.out.mkdir(parents=True);e=a.baseline/'nes-game150/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game150-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    names=['nes_game_bus150.sv','nes_game_bus151.sv','nes_screen_status151.sv','nes_game_frame150.sv','nes_game_pad150.sv']
    for n in names:shutil.copy2(ROOT/'src/nes/diagnostic'/n,a.out/n)
    for src,n in [('asm/nes_screen_status142.sv','nes_screen_status142.sv'),('video/pixels.hex','pixels.hex'),('video/expected.hex','expected.hex')]:
        assert sha(e/src)==pins[src];shutil.copy2(e/src,a.out/n)
    shutil.copy2(ROOT/'tests/nes-functional/game151_write_tb.sv',a.out/'game151_write_tb.sv')
    for kind in ['rom','video']:
        s=(ROOT/f'tests/nes-functional/game150_{kind}_tb.sv').read_text()
        s=s.replace('game150_'+kind+'_tb','game151_'+kind+'_tb').replace('nes_game_bus150','nes_game_bus151')
        if kind=='video':
            old='data_in=d;read_n=1;write_n=0;#350;write_n=1;#150;'
            assert s.count(old)==1
            s=s.replace(old,"data_in=8'h60;read_n=1;write_n=0;#160;data_in=d;#190;write_n=1;data_in=8'hee;#150;")
        (a.out/f'game151_{kind}_tb.sv').write_text(s)
    shutil.copy2(build(a.out/'client'),a.out/'game-program.hex')
    def run(exe,args,log):
        with (a.out/log).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        s=(a.out/log).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2000:])
        return s
    run('vlib',['work'],'vlib.log')
    run('vlog',['-sv',*names,'nes_screen_status142.sv','game151_write_tb.sv','game151_rom_tb.sv','game151_video_tb.sv'],'vlog.log')
    results={}
    for kind in ['write','rom','video']:
        s=run('vsim',['-c',f'work.game151_{kind}_tb','-do','onerror {quit -code 1}; run -all; quit -f'],kind+'.log')
        results[kind]=re.search(r'PASS GAME15[01][^\r\n]+',s)[0]
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,results=results,scope='Late data model0/80/160ns at3 phases, old causal controls; stored pixels, not measured physical write timing.'),indent=2)+'\n')
    print(json.dumps(results))
if __name__=='__main__':main()
