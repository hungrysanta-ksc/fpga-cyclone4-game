"""Check final ARM image's checked D2 timing metadata and the existing menu-return contract."""
import json

from check_nes_game478 import crc
from check_nes_kirby1023_release import run, widened_wire
from check_nes_kirby1024_journal import replay
from check_nes_kirby1034 import sampling, timer_cases, check
from check_nes_sram897 import check_game_path
from prepare_nes_kirby1035 import BASE

WORK=BASE.parents[1]/'nes-kirby1035'


def qualify():
    src=WORK/'link/src'
    offers={905:1,906:127}
    intervals={905:(4,53),906:(126,127)}
    def observed(rows):
        generation=None
        phase=3
        for tx,rx in widened_wire(rows):
            reply=bytearray.fromhex(rx)
            if tx.startswith('d1') and reply[1:3]==bytes.fromhex('e000'):
                generation=int.from_bytes(reply[3:5],'big')
                phase=0
            if tx.startswith('d2') and phase<3:
                reply[5]|=(offers[generation],*intervals[generation])[phase]<<1
                reply[7]=crc(reply[1:7],8,7,0)
                phase+=1
            yield tx,reply.hex()
    cases,_,_=check_game_path(src,order=lambda rows:list(observed(rows)),rom_revision=0x7c,
                              rom_pages=12,content_crc=0x248c7140,ready_age_oracle=offers,
                              checked_d2_stamp=True,capture_intervals=intervals)
    assert cases['normal']['checked_retire'] and not cases['bad-crc']['input_observer']
    proof=WORK/'proof'
    proof.mkdir(exist_ok=True)
    # Sampling tests rewrite generation and descriptor for each checked mailbox reply.
    header=bytearray.fromhex(json.loads((WORK/'banks.json').read_text())['header'])
    info=dict(cases=cases,windows=sampling(src,header,1035),timer=timer_cases(src),
              menu=check(src,'1035'),journal=replay(WORK,1035,[]))
    assert info['timer']['passed'] and info['menu']['rows']['normal']['released']
    (proof/'return.json').write_text(json.dumps(info,indent=2)+'\n')
    run('base',1035)


if __name__=='__main__':
    qualify()
