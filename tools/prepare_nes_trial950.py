"""Relink the 60-second client and distinguish the installed and proposed ROM suppliers."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_chain935
from nes_header950 import work, ROM, sha, once
from nes_rows931 import PlanTrace
from prepare_nes_trial802 import rename_edition

RELEASE = work('release')


def prepare():
    src = RELEASE/'link/src'
    import json
    reference = json.loads((Path(__file__).resolve().parents[1]/'analysis/header950-results.json').read_bytes())
    original = work('bound')/'link'
    assert sha(original/'src/obj-nes-100/firmware.stm') == reference['cases']['cold1']['bound']['firmware']
    shutil.copytree(original, src.parent)
    renamed = RELEASE/'markers'
    rename_edition(src, renamed, 925, 950)
    for p in renamed.iterdir():
        shutil.copyfile(p, src/p.name)
    p = src/'nes_budget210.c'
    p.write_text(once(p.read_text(), 'log900p->edition=925;', 'log900p->edition=950;'), newline='\n')


class BoardWireTrace(PlanTrace):
    """Record only received E9 transactions, including the CRC from the linked ARM."""
    def accept(self, tx, t):
        if tx[0]==0xe9 and self.generation==912:
            import json
            with (self.a.out/"e9wire914.jsonl").open("a") as out:
                print(json.dumps([t,tx.hex()]), file=out)
        return super().accept(tx,t)


def run(temp, phase, cache, supplier):
    from replay_nes_strip869 import dense
    from test_nes_receive649 import admission
    runtime = dense.joint.Runtime
    suppliers = {'rtl': BoardWireTrace, 'board': PlanTrace, 'release': nes_chain935.QueuedPages}
    with patch.object(runtime, 'offer_input', admission(runtime.offer_input)), patch.object(nes_chain935, 'output', lambda _: ROM):
        nes_chain935.replay(temp, 'final', phase, cache, 'bounded', work_arm=RELEASE,
                            tag='950'+supplier, edition=950,
                            supplier=suppliers[supplier])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare','replay','guards','board','fixture'))
    p.add_argument('temp', type=Path)
    p.add_argument('phase', nargs='?', type=int, choices=(1,2))
    p.add_argument('cache', nargs='?', choices=('warm','cold'))
    p.add_argument('supplier', nargs='?', choices=('board','release','rtl'))
    a=p.parse_args()
    if a.action=='prepare':
        prepare()
    elif a.action=='replay':
        run(a.temp,a.phase,a.cache,a.supplier)
    elif a.action=='fixture':
        from fixture_nes_port914 import fixture
        for phase in (1,2):
            fixture(a.temp,phase,True,tag='950rtl')
    elif a.action=='board':
        from prepare_nes_trial925 import replace_client, read, ROOT, QUARTUS
        source=a.temp/'nes-port914I/nes-trial816-board914'
        assert sha(source/'output_files/board.sof')==read(ROOT/'analysis/trial915-package.json')['board']['image']['SOF']
        target=a.temp/'nes-board950'
        target.mkdir(exist_ok=True)
        replace_client(950,source,target,QUARTUS,ROM)
    else:
        from nes_header950 import guards
        guards(a.temp,'release',edition=950)
