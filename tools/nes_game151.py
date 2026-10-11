# SPDX-License-Identifier: MIT
"""Materialize151 from the exact selected150 board; preserve old evidence."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
from build_nes_game151 import build
MODULES=['nes_game_frame150.sv','nes_game_pad150.sv','nes_game_bus151.sv','nes_screen_status151.sv']
def prepare(baseline,out):
    e=baseline/'nes-game150/evidence'
    meta=json.loads((ROOT/'analysis/game150-verification.json').read_bytes())
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    qsf=(e/'asm/board.qsf').read_text()
    names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)
    inputs={}
    for n in names+['board.sdc','game-program.hex']:
        src=e/'asm'/n;assert sha(src)==pins['asm/'+n]
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);inputs[n]=sha(src)
    replacements={'nes_game_bus150':'nes_game_bus151','nes_screen_status142':'nes_screen_status151'}
    for old,new in replacements.items():
        qsf=qsf.replace(old,new)
        p=out/'fxpak_nes_screen137_top.sv';s=p.read_text();assert s.count(old)==1;p.write_text(s.replace(old,new))
        (out/(old+'.sv')).unlink()
    for n in MODULES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
    for n,old,new in [('nes_rom_spi.sv',"snapshot<={8'h60,","snapshot<={8'h61,"),('nes_run_observer134.sv',"8'hda","8'hdb")]:
        p=out/n;s=p.read_text();assert old in s;p.write_text(s.replace(old,new))
    shutil.copy2(build(out/'client'),out/'game-program.hex')
    (out/'board.qsf').write_text(qsf);(out/'board.qpf').write_text('PROJECT_REVISION = "board"\n')
    (out/'materialization151.json').write_text(json.dumps(dict(inputs150=inputs,id=['61','DB'],changes='Write completion capture; actual game held30vblanks. Core/reader/loader/frame memory unchanged.'),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
