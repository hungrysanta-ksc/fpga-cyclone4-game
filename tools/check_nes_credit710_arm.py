"""Untrusted skip hints never publish credit/status or replace final ACK."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from check_nes_credit709_arm import run as prior,machine,seed,send,packet
from nes_raw506 import sha

def state(m):
    return {k:m.get(m.w,'nes_sink_window184',k,n) for k,n in
        [('retired',2),('status_flags',1),('ack_status',1)]}

def run(a):
    prior(SimpleNamespace(arm=a.arm,out=a.out,needed=True))
    r=json.loads(a.out.read_text());rows=r['cases']
    # Enough locally pending packets to consider E1, but no new remote credit.
    for corruption in [('CRC',1),(1,1),(2,0x80),(7,1),(9,1),(17,1)]:
        m=machine(a.arm);seed(m,1)
        m.put(m.w,'nes_sink_window184','sent',3,2)
        m.endpoint.sent=3;m.endpoint.pending=[packet(seq=1),packet(seq=2)]
        m.endpoint.corrupt=corruption;before=state(m)
        assert send(m,packet(seq=3)) and state(m)==before
        assert m.get(m.w,'nes_sink_window184','sent',2)==4
        assert m.endpoint.calls==[0xe0,0xe1]
        rows.append(dict(case='same_retired_'+str(corruption),passed=True,state_unchanged=True))
    # A changing raw hint is not a validated credit; failed checks must not
    # publish diagnostic flags/ACK status either (only latch the error).
    for corruption in [('CRC',1),(1,1),(2,0x80),(3,1),(5,1),(7,1),(9,1),(18,1)]:
        m=machine(a.arm);seed(m);m.put(m.w,'nes_sink_window184','retired',65535,2)
        m.put(m.w,'nes_sink_window184','status_flags',0x55,1)
        m.put(m.w,'nes_sink_window184','ack_status',0x33,1)
        m.endpoint.corrupt=corruption;before=state(m)
        assert not send(m,packet(seq=1)) and state(m)==before
        assert m.get(m.w,'nes_sink_window184','sent',2)==1
        rows.append(dict(case='changed_hint_'+str(corruption),passed=True,state_unchanged=True))
    # A bad same-credit E1 is skipped, but a later authoritative E0 cannot be
    # skipped. Corrupt its identity with a valid CRC and require rejection.
    m=machine(a.arm);seed(m);m.put(m.w,'nes_sink_window184','sent',3,2)
    m.endpoint.sent=3;m.endpoint.pending=[packet(seq=1),packet(seq=2)]
    m.endpoint.corrupt=('CRC',1);before=state(m)
    assert send(m,packet(seq=3)) and state(m)==before
    while m.endpoint.pending:m.endpoint.retire()
    m.endpoint.last=m.endpoint.last[:2]+bytes([m.endpoint.last[2]^1])+m.endpoint.last[3:]
    assert not m.call('nes_window184_through',[m.w,m.q+300,4])
    assert state(m)==before and m.get(m.w,'nes_sink_window184','error')==8
    rows.append(dict(case='ignored_hint_then_authoritative_E0_identity_failure',passed=True))
    m=machine(a.arm);seed(m);m.put(m.w,'nes_sink_window184','retired',65535,2)
    exchange=m.endpoint.exchange
    def forged_same(tx,clock):
        rx=bytearray(exchange(tx,clock))
        if tx[0]==0xe1:rx[5:7]=b'\xff\xff' # deliberately invalid CRC
        return bytes(rx)
    m.endpoint.exchange=forged_same;before=state(m)
    assert send(m,packet(seq=1)) and state(m)==before
    m.endpoint.retire()
    assert m.call('nes_window184_through',[m.w,m.q+300,2])
    assert m.get(m.w,'nes_sink_window184','retired',2)==2
    rows.append(dict(case='forged_same_hint_conservative_until_valid_E0',passed=True))
    m=machine(a.arm);seed(m);m.put(m.w,'nes_sink_window184','sent',3,2)
    m.endpoint.sent=3;m.endpoint.pending=[packet(seq=1),packet(seq=2)]
    m.endpoint.stop_after=True;before=state(m)
    assert send(m,packet(seq=3)) and state(m)==before
    count=len(m.endpoint.calls)
    assert not send(m,packet(seq=4)) and len(m.endpoint.calls)==count
    assert m.get(m.w,'nes_sink_window184','error')==2
    rows.append(dict(case='STOP_after_ignored_same_credit_response',passed=True))
    r.update(stage=710,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'))
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print('PASS710',len(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
