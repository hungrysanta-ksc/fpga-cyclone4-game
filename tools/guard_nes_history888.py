"""Compare complete ARM bank state and both guard regions after receipt publication."""
import json
import random

from check_nes_game478 import Machine
from prepare_nes_history888 import BASE, WORK


def verify():
    cpus = [Machine(p/'link-credit/src',bytes(128)) for p in (BASE,WORK)]
    fields=cpus[0].layout['nes_resident211']
    assert fields==cpus[1].layout['nes_resident211']
    at=0x20012000
    size=fields['size']
    rng=random.Random(888)
    total=0
    timings=set()
    for bank in (0,1):
        for case in ('mixed','all','empty','not_visible','old_serial','old_generation','wrong_bank',
                     'not_prepared','not_open','fault'):
            image=bytearray(rng.randbytes(size))
            def put(name,value,n=1):
                pos=fields[name]
                image[pos:pos+n]=value.to_bytes(n,'little')
            serial,gen=0x12345678,0x89ab
            put('serial',serial,4)
            put('generation',gen,2)
            put('target',bank)
            put('open',int(case!='not_open'))
            put('prepared',int(case!='not_prepared'))
            put('fault',int(case=='fault'))
            offset=fields['dirty']
            if case in ('all','empty'):
                image[offset:offset+144]=bytes([255 if case=='all' else 0])*144
            successes=case in ('mixed','all','empty')
            args=[at,serial+(case=='old_serial'),gen+(case=='old_generation'),
                  bank^(case=='wrong_bank'),int(case!='not_visible')]
            states=[]
            counts=[]
            for m in cpus:
                m.u.mem_write(at-16,b'\xa5'*16+bytes(image)+b'\x5a'*16)
                before=m.instructions
                assert m.call('nes_resident211_commit',args)==int(successes)
                counts.append(m.instructions-before)
                states.append(bytes(m.u.mem_read(at-16,size+32)))
            assert states[0]==states[1]
            assert states[1][:16]==b'\xa5'*16 and states[1][-16:]==b'\x5a'*16
            if successes:
                for dst in (0,1):
                    start=fields['resident']+144*dst
                    expected=bytes((image[start+i]|image[offset+i]) if dst==bank else image[start+i]
                                   for i in range(144))
                    assert states[1][16+start:16+start+144]==expected
                timings.add(tuple(counts))
            total+=1
    assert len(timings)==1
    return dict(cases=total,resident_offset=fields['resident'],dirty_offset=offset,
                success_instructions=list(timings.pop()),compared_bytes=size+32)


if __name__=='__main__':
    (WORK/'history-guards.json').write_text(json.dumps(verify(),indent=2)+'\n')
