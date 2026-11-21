"""Feed the board's pre-release SPI73 snapshots to the linked ARM RUN/STOP routine."""
import argparse
import re
from pathlib import Path

from check_nes_reset796 import replay
from nes_reset892 import BASE,WORK
from package_nes_trial704 import save, sha


def verify(sim):
    src=WORK/'link/src'
    text=(sim/'sim.log').read_text(errors='replace')
    rows={}
    reference=replay(BASE/'src',1,'defer',probe=2,pre_snapshots=[])
    for ph in range(4):
        wire=[bytes.fromhex(v) for v in re.findall(rf'^# SNAP892 phase={ph} reply=([0-9a-f]+)$',text,re.M)]
        assert 1<len(wire)<=64 and wire[-1][3]&64 and all((s[3]&64)==0 for s in wire[:-1])
        rows[f'rtl-{ph}']=replay(src,1,'defer',probe=2,pre_snapshots=wire)
    quiet=bytes.fromhex('e6000000000003')
    ready=bytes.fromhex('e6000040000003')
    for key,snapshots,denied,bad_crc in [
        ('never-ready',[quiet]*64,True,False),('last-allowed',[quiet]*63+[ready],False,False),
        ('invalid-id',[bytes.fromhex('00000040000003')],True,False),
        ('invalid-version',[bytes.fromhex('e6000040000000')],True,False),
        ('bad-post-crc',[ready],False,True)]:
        rows[key]=replay(src,1,'defer',probe=2,pre_snapshots=snapshots,
                         deny_release=denied,bad_post_crc=bad_crc)
    rows['ready-E0']=replay(src,1,probe=2,pre_snapshots=[])
    rows['normal-game-entry']=replay(src,2,'defer',pre_snapshots=[quiet,ready])
    rows['start-only']=replay(src,1,probe=1)
    save(WORK/'arm.json',dict(firmware=sha(src/'obj-nes-100/firmware.stm'),rows=rows,
         reference=dict(firmware=sha(BASE/'src/obj-nes-100/firmware.stm'),deferred=reference)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('sim',type=Path)
    verify(p.parse_args().sim)
