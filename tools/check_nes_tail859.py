"""Run existing corruption, STOP, restart and menu checks on the selected tail link."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import check_nes_seal858 as guards
from check_nes_menu533 import check as menu
from prepare_nes_tail859 import ROOT, BASE
from guard_nes_output852 import run as run_receiver
from nes_raw506 import once


def tail_gap(temp,tag):
    folder=temp/f'nes-tile821-demo-jointmirror-p1-{tag}-on'
    def limit(b,g,case):
        return b,g==906
    def change_offset(lua,labels):
        point='packet=requests[index];'
        change="""if pw(8)==906 and pb(0)==2 and pb(1)==5 and pw(10)==1322 then
 assert(pw(12)==240 and not tail_gap_injected)
 tail_gap_injected=true
 packet=packet:sub(1,10)..string.char(pb(10)+1)..packet:sub(12)
end;"""
        lua=once(lua,'local function loaded()','local tail_gap_injected=false\nlocal function loaded()')
        lua=once(lua,'  assert(captured==commits)','  assert(tail_gap_injected)\n  assert(captured==commits)')
        return once(lua,point,point+change)
    return run_receiver(temp,folder,'tail-gap-confirmed',column_client=BASE/'client-e',edit_seal=limit,adapt_lua=change_offset)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('variant')
    p.add_argument('cases',nargs='+',choices=('coverage','consumer','table','stop','identity','menu','gap'))
    args=p.parse_args()
    arm=ROOT/f'link-{args.variant}'/'src'
    tag='859'+args.variant
    with patch.object(guards,'ROOT',ROOT):
        for case in args.cases:
            if case=='menu':
                (ROOT/f'{tag}-menu.json').write_text(json.dumps(menu(arm,'855'),indent=2)+'\n')
                subprocess.run([sys.executable,str(Path(__file__).with_name('check_nes_transfer512_recovery.py')),
                    '--arm',str(arm),'--trial','855','--fault','none','--out',str(ROOT/f'{tag}-base')],check=True)
            elif case=='gap':
                (ROOT/f'{tag}-gap.json').write_text(json.dumps(tail_gap(args.temp,tag),indent=2)+'\n')
            else:
                guards.check(args.temp,tag,BASE/'client-e',arm,case)
