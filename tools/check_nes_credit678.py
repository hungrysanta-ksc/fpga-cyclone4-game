"""Keep geometry block credit across empty STATUS; debit only checked READ/POP."""
import argparse,json,struct
from pathlib import Path
from check_nes_idle676 import Receiver
from check_nes_game478 import sha

def check(src,case):
    mode='normal' if case=='wrap' else case
    m=Receiver(src,mode)
    if case=='wrap':
        m.start_token=65535
        m.put(m.state,'nes_native165','next_token',65535,2)
        m.put(m.state,'nes_native165','token_valid',1,1)
    ok=m.call('wait634',[m.rt,m.check|1,4,0])
    expected=case in ('normal','wrap','empty','complete')
    assert bool(ok)==expected,(case,ok,m.ops)
    left=m.get(m.rt,'nes_native_runtime165','prefetch_left')
    if case=='empty':
        assert left==7 and m.ops==[0xd0]
        assert m.call('wait634',[m.rt,m.check|1,4,0]) and m.get(m.rt,'nes_native_runtime165','prefetch_left')==7
        header=(0x2233<<48)|(32<<42)|(2<<36)|(224<<28)
        m.packets=[struct.pack('>HHQ',0xe000,953,header)]
        assert m.call('wait634',[m.rt,m.check|1,4,0])
        assert m.get(m.rt,'nes_native_runtime165','prefetch_left')==6
        assert m.ops==[0xd0,0xd0,0xd0,0xd1,0xd2,0xd0]
    elif case in ('normal','wrap'):
        assert left==6 and m.ops==[0xd0,0xd1,0xd2,0xd0]
        assert m.get(m.state,'nes_native165','next_token',2)==(0 if case=='wrap' else 1)
    elif case=='complete':assert left==3 and not m.ops
    elif case!='STOP_before':assert left==7
    assert not any(op in (0xd3,0xe1,0xea) for op in m.ops)
    return dict(case=case,success=bool(ok),remaining=left,operations=m.ops)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reference',type=Path);a=p.parse_args()
    cases=[check(a.arm,c) for c in ('normal','wrap','empty','complete','STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO')]
    reference=None
    if a.reference:
        m=Receiver(a.reference,'empty');assert m.call('wait634',[m.rt,m.check|1,4,0])
        left=m.get(m.rt,'nes_native_runtime165','prefetch_left');assert left==6 and m.ops==[0xd0]
        reference=dict(firmware=sha(a.reference/'obj-nes-100/firmware.stm'),remaining_after_empty=left,operations=m.ops)
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=cases,old_empty_debit=reference),indent=2)+'\n',newline='\n')
    print('PASS678 nine receive-credit cases, including two empty polls then real READ and token wrap')
