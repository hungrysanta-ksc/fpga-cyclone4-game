"""Compare BEGIN collision chains on linked M4 through commit, abort, cold and epoch changes."""
import hashlib
import json
from check_nes_game478 import Machine
from nes_handoff945 import base, work


def run(arm, preindex):
    m = Machine(arm/'link/src', bytes(128))
    layout = m.layout['nes_resident211']
    def address(field):
        return m.resident + layout[field]
    def begin(epoch, generation):
        return m.call('nes_resident211_begin',[m.resident, epoch, 1, generation, m.writer|1, 0])
    def digest():
        return hashlib.sha256(m.u.mem_read(address('index_head'), 512) +
                              m.u.mem_read(address('index_next'), 2304)).hexdigest()
    assert begin(0, 1)
    assert bytes(m.u.mem_read(address('index_head'),512)) == b'\xff'*512
    # Include unused slots, duplicate keys and collisions across both kinds.
    for field,slots,width in [('bg',64,2),('obj',32,4)]:
        m.u.mem_write(address(field+'_slots'),slots.to_bytes(2,'little'))
        keys = [2**(width*8)-1 if i%7==1 else (i%17)*257 for i in range(slots)]
        m.u.mem_write(address(field),b''.join(k.to_bytes(width,'little') for k in keys))
    assert m.call('nes_resident211_prepare',[m.resident,0,0,0])
    if preindex:
        m.call('nes_resident945_preindex',[m.resident])
        done=digest()
        m.call('nes_resident945_preindex',[m.resident])
        assert done==digest()
    assert m.call('nes_resident211_commit',[m.resident,1,1,0,1])
    before=m.instructions
    assert begin(0,2)
    instructions=m.instructions-before
    chains=digest()
    assert m.call('nes_resident211_prepare',[m.resident,0,0,0])
    if preindex:
        m.call('nes_resident945_preindex',[m.resident])
    assert m.call('nes_resident211_commit',[m.resident,2,2,1,1])
    assert begin(1,3)
    assert bytes(m.u.mem_read(address('index_head'),512)) == b'\xff'*512
    assert m.call('nes_resident211_prepare',[m.resident,0,0,0])
    if preindex:
        m.call('nes_resident945_preindex',[m.resident])
    assert not m.call('nes_resident211_commit',[m.resident,3,0,0,1])
    assert not begin(1,4)
    m.call('nes_resident211_reset',[m.resident])
    assert begin(1,4)
    assert bytes(m.u.mem_read(address('index_head'),512)) == b'\xff'*512
    return dict(chains=chains, begin_instructions=instructions, resident_bytes=layout['size'])


def receipt_checks(mode):
    from check_nes_credit709_arm import machine, packet, send, crc
    def sealed(serial):
        b=bytearray(packet(3,4,1)); b[4:8]=serial.to_bytes(4,'little'); return bytes(b)
    def make(source):
        m=machine(source/'link/src')
        m.endpoint.auto=True
        assert send(m,packet(1,4,0),True)
        return m
    def corrupt(m, field):
        original=m.endpoint.exchange
        def exchange(tx,clock):
            r=bytearray(original(tx,clock))
            if tx[0]==0xe0:
                r[field]^=1
                if field!=19:
                    r[19]=crc(r[1:19],8,7,0)
            return bytes(r)
        m.endpoint.exchange=exchange
    evidence={}
    for name,source in [('944',base.work('smallbg')),('945',work(mode))]:
        m=make(source)
        assert send(m,sealed(2),True)
        start=len(m.endpoint.calls)
        assert send(m,packet(1,4,2),True)
        calls=m.endpoint.calls[start:]
        assert calls==([0xe0,0xe1,0xe0] if name=='944' else [0xe1,0xe0])
        evidence[name]=calls
    if mode in ('warm_begin','warm_header'):
        m=make(work(mode))
        assert send(m,sealed(1),True)
        start=len(m.endpoint.calls)
        assert send(m,packet(1,4,2),True)
        assert m.endpoint.calls[start:]==[0xe0,0xe1,0xe0]
        evidence['first_serial']=m.endpoint.calls[start:]
    for where in ('previous_seal','following_begin'):
        for field in (9,19):
            m=make(work(mode))
            if where=='following_begin':
                assert send(m,sealed(2),True)
            corrupt(m,field)
            assert not send(m,packet(3 if where=='previous_seal' else 1,4,2),True)
            start=len(m.endpoint.calls)
            assert not send(m,packet(1,4,3),True) and len(m.endpoint.calls)==start
    m=make(work(mode))
    assert send(m,sealed(2),True)
    m.endpoint.mode='STOP_after_bulk'
    start=len(m.endpoint.calls)
    assert not send(m,packet(1,4,2),True) and len(m.endpoint.calls)==start
    evidence.update(bad_identity_and_CRC=['previous_seal','following_begin'],stop_before_begin=True)
    (work(mode)/'receipt945.json').write_text(json.dumps(evidence)+'\n')


if __name__=='__main__':
    for mode in ('receipt','receipt_fit','warm_begin','warm_header'):
        receipt_checks(mode)
    ref=run(base.work('smallbg'),False)
    for mode in ('prepared_index','sealed_index'):
        result=run(work(mode),mode=='sealed_index')
        assert result['chains']==ref['chains'] and result['resident_bytes']==ref['resident_bytes']
        if mode=='sealed_index':
            assert run(work(mode),False)['chains']==ref['chains']
        (work(mode)/'index945.json').write_text(json.dumps(dict(reference=ref,result=result))+'\n')
        print(mode,result)
