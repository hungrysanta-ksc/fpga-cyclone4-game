# SPDX-License-Identifier: MIT
"""Materialize152 from frozen151: input polling and tagged fault address only."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import ROOT,sha
from build_nes_game152 import build

def prepare(baseline,out):
    e=baseline/'nes-game151/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game151-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    qsf=(e/'asm/board.qsf').read_text()
    names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',qsf)
    inputs={}
    for n in names+['board.sdc','game-program.hex']:
        src=e/'asm'/n;assert sha(src)==pins['asm/'+n]
        dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);inputs[n]=sha(src)
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_rom_service152.sv',out/'nes_rom_service.sv')
    for n,old,new,count in [('nes_rom_spi.sv',"snapshot<={8'h61,","snapshot<={8'h62,",2),
                          ('nes_run_observer134.sv',"8'hdb","8'hdc",3),
                          ('nes_screen_status151.sv',"8'hdb","8'hdc",1)]:
        p=out/n;s=p.read_text();assert s.count(old)==count,(n,s.count(old));p.write_text(s.replace(old,new))
    shutil.copy2(build(out/'client'),out/'game-program.hex')
    (out/'board.qsf').write_text(qsf);(out/'board.qpf').write_text('PROJECT_REVISION = "board"\n')
    changed=[n for n,h in inputs.items() if sha(out/n)!=h]
    assert sorted(changed)==sorted(['nes_rom_service.sv','nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','game-program.hex'])
    (out/'materialization152.json').write_text(json.dumps(dict(inputs151=inputs,changed=changed,id=['62','DC'],ppu_error_fixed=False),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
