"""Carry measured RTL D2 age bins through the linked receiver and guarded retire."""
import json
import re

from check_nes_game478 import crc
from check_nes_kirby1023_release import widened_wire
from check_nes_sram897 import check_game_path
from prepare_nes_kirby1031 import WORK


def run(edition=1031):
    assert edition in (1031,1032)
    work=WORK.with_name(f'nes-kirby{edition}')
    logs=work if edition==1031 else work/'bus-test'
    pattern=r'^# PASS1031 mode=(\d+) bytes=(\d+) available=(\d+) positive=(\d+) D1=(\d+) age=(\d+)$'
    rows={}
    for f in (750,1830,3030,3570):
        for mode in (range(5) if f==1830 else [0]):
            log=(logs/f'replay-{f}-{mode}.log').read_text()
            sample,=re.findall(pattern,log,re.M)
            row=dict(zip(('mode','bytes','ready','D0','D1','age'),map(int,sample)))
            assert row['mode']==mode and row['ready']<=row['D0']<row['D1']
            rows[f,mode]=row
    late,occupied=(rows[1830,m] for m in (1,2))
    assert late['D0']==occupied['D0'] and late['D1']==occupied['D1']
    assert late['ready']-occupied['ready']==1008000
    assert late['age']==0 and occupied['age']==31
    oracle={905:occupied['age'],906:rows[1830,4]['age']}
    def with_age(transactions):
        tagged=[]
        pending=None
        seen=[]
        for tx,rx in widened_wire(transactions):
            reply=bytearray.fromhex(rx)
            if tx.startswith('d1') and reply[1:3]==b'\xe0\x00':
                pending=int.from_bytes(reply[3:5],'big')
            if tx.startswith('d2') and pending is not None:
                assert reply[5]<2
                reply[5]|=oracle[pending]<<1
                reply[7]=crc(reply[1:7],8,7,0)
                seen.append(pending)
                pending=None
            tagged.append((tx,reply.hex()))
        assert seen==list(oracle)
        return tagged
    cases,_,_=check_game_path(work/'link/src',order=with_age,rom_revision=0x7c,
                              rom_pages=12,content_crc=0x248c7140,ready_age_oracle=oracle)
    result=dict(RTL={f'{f}-{m}':r for (f,m),r in rows.items()},ARM_cases=cases,ARM_age_bins=oracle)
    (work/'proof').mkdir(exist_ok=True)
    (work/'proof/age.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    import sys
    run(int(sys.argv[1]) if len(sys.argv)>1 else 1031)
