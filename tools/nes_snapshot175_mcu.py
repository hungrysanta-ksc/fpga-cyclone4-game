# SPDX-License-Identifier: MIT
"""175 A5 MCU: retain174 history wire reader and runtime; names/label only."""
from pathlib import Path
import argparse,json
from nes_game147 import sha
from nes_lifecycle175_mcu import prepare as event_prepare

def prepare(prior,out):
    r=event_prepare(prior,out)
    n='src/nes_run136.inc'
    (out/n).write_bytes((prior/n).read_bytes());r['changed'][n]=sha(out/n)
    n='src/nes_menu_diagnostic.c'
    s=(out/n).read_text();assert s.count('LAST16_NATIVE_LIFECYCLE_A4')==1
    (out/n).write_text(s.replace('LAST16_NATIVE_LIFECYCLE_A4','LAST16_NATIVE_STATE_A5'),encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
    r['public_sources']['tools/nes_snapshot175_mcu.py']=sha(Path(__file__))
    r['history_wire_version']=1;r['history_schema']='A5';r['runtime_unchanged']=True
    for n in ['preparation-snapshot175.json','preparation-runlease165.json']:
        (out/n).write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
