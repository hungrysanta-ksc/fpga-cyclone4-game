# SPDX-License-Identifier: MIT
"""Combine preapproved SPI pulses with the verified state-specific loader."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import ROOT,sha
from nes_commandpulse165 import prepare as pulse
from nes_commandguard165 import transform

def prepare(baseline,out):
 pulse(baseline,out)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 p=out/'preparation.json';m=json.loads(p.read_bytes())
 m['sources']['nes_rom_loader.sv']=sha(out/'nes_rom_loader.sv')
 m['changed']=['nes_rom_spi.sv','nes_rom_loader.sv']
 for n in ['tools/nes_pulsejoint165.py','tools/nes_commandguard165.py']:m['public_sources'][n]=sha(ROOT/n)
 assert set(n for n,h in m['sources'].items() if h!=m['baseline'][n])==set(m['changed'])
 p.write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
