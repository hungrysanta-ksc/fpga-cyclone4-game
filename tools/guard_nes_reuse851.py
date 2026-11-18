"""Exercise malformed and interrupted map references on the linked ARM receiver."""
import argparse
import binascii
import json
from pathlib import Path
import struct

from build_nes_game164 import palette
from check_nes_game478 import Machine
from nes_direct653 import encode


def check(arm,data):
    geo=(data/'frame905.geometry').read_bytes()
    raw=(data/'frame905.raw').read_bytes()
    original=encode(geo,raw,905)[0]
    def header(g):
        return encode(geo,raw,g)[0][0][:12]
    def ref(g,start=0,count=80):
        return struct.pack('>5H',0xfffe,g,start,count,binascii.crc_hqx(geo[2*start:2*(start+count)],65535))
    result={}
    for case in ('cold','bad_crc','corrupt_ram','wrong_generation','bad_range','extra_byte',
                 'truncated','skipped_generation','abort_partial','stop_partial','valid'):
        m=Machine(arm,palette())
        if case!='cold':
            m.frame(original,geo,raw,905,1)
        def put(wire):
            address=0x20017000
            m.u.mem_write(address,wire)
            ok=m.call('nes_native165_packet',[m.state,m.token,address,len(wire)])
            if ok:
                m.token=(m.token+1)&65535
            return bool(ok)
        g=907 if case=='skipped_generation' else 906
        assert put(header(g))
        if case in ('abort_partial','stop_partial'):
            assert put(ref(g))
            if case=='stop_partial':
                m.call('nes_native165_reset',[m.state])
                m.token=0
            else:
                assert put(struct.pack('>HHQ',0xe002,g,0))
            g+=1
            assert put(header(g))
        wire=ref(g)
        if case=='bad_crc':
            wire=wire[:-1]+bytes([wire[-1]^1])
        if case=='corrupt_ram':
            m.u.mem_write(m.state,bytes([m.u.mem_read(m.state,1)[0]^1]))
        if case=='wrong_generation':
            wire=ref(g-1)
        if case=='bad_range':
            wire=ref(g,1,80)
        if case=='extra_byte':
            wire+=bytes(1)
        if case=='truncated':
            wire=wire[:-1]
        assert put(wire)==(case=='valid'),case
        if case!='valid':
            assert m.state_value()==5,case
            m.call('nes_native165_reset',[m.state])
            m.call('nes_resident211_reset',[m.resident])
            m.token=0
            m.frame(original,geo,raw,905,1)
        result[case]='accepted' if case=='valid' else 'rejected; complete cold frame restored'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','data','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.arm,a.data),indent=2)+'\n')
