"""Linked ARM window guards with pre-accept E1 snapshots and immutable ACKs.

Injected transport/clock at the callback boundary; target parser, credit,
barrier and STOP code execute. Actual RTL and full schedule are separate.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha

class Endpoint:
    def __init__(self):
        self.mode='normal';self.bulk=self.accepted=0;self.sent=self.retired=0
        self.last=bytes(12);self.pending=[];self.calls=[];self.corrupt=None
        self.auto=False;self.stop_after=False;self.final_polls=0
    def retire(self):
        if not self.pending:return
        b=self.pending.pop(0);self.retired=(self.retired+1)&65535
        self.last=bytes([int(b[0]==3),b[0]])+b[2:10]+b'\x65\x9a'
    def status(self):
        used=(self.sent-self.retired)&65535;assert used<=4
        b=bytearray(20);b[1]=0xf7;b[2]=int(bool(used))|(2 if self.last!=bytes(12) else 0)|(4 if used==4 else 0)
        b[3:7]=struct.pack('>HH',self.sent,self.retired);b[7:19]=self.last
        return b
    def exchange(self,tx,clock):
        self.calls.append(tx[0]);op=tx[0]
        if op==0xe0:
            if self.auto:self.retire()
            if self.pending and self.pending[0][0]==3:
                self.final_polls+=1
                if self.final_polls>=2:self.retire()
        elif op==0xe1 and self.auto:self.retire()
        r=self.status()
        if op==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            assert ((self.sent-self.retired)&65535)<4
            self.sent=(self.sent+1)&65535;self.pending.append(bytes(tx[1:-2]));self.bulk+=1
            if self.stop_after:self.mode='STOP_after_bulk'
            if self.corrupt and isinstance(self.corrupt[0],int):
                pos,value=self.corrupt
                r[pos]^=value
        r[19]=crc(r[1:19],8,7,0)
        if op==0xe1 and self.corrupt==('CRC',1):r[19]^=1
        if op==0xe1 and len(tx)<20:return bytes(r[:len(tx)])
        return bytes(r)+bytes(len(tx)-20)

def machine(src):
    m=ARM(src,'normal');m.endpoint=Endpoint();m.setup()
    m.put(m.w,'nes_sink_window184','wait',0,4)
    return m

def packet(op=2,n=1,seq=0):
    return bytes([op,5])+struct.pack('<HIHHHH',seq,1,907,0,n,0)+bytes((i*37+11)&255 for i in range(n))

def send(m,b,barrier=False):
    m.u.mem_write(m.q,b)
    return bool(m.call('nes_window184_barrier' if barrier else 'nes_window184_enqueue',
        [m.w,m.q,len(b),m.q+300] if barrier else [m.w,m.q,len(b)]))

def seed(m,count=1):
    e=m.endpoint;e.sent=e.retired=count;b=packet(seq=(count-1)&65535)
    e.last=bytes([0,2])+b[2:10]+b'\x65\x9a'
    for k,v,n in [('sent',count,2),('retired',count,2),('ever_sent',1,1)]:m.put(m.w,'nes_sink_window184',k,v,n)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],b[:10])

def run(a):
    rows=[]
    for n in (0,1,2,4,192,240):
        m=machine(a.arm);seed(m);before=len(m.endpoint.calls)
        assert send(m,packet(n=n,seq=1))
        assert m.get(m.w,'nes_sink_window184','sent',2)==2 and m.get(m.w,'nes_sink_window184','retired',2)==1
        assert m.endpoint.calls[before:]==[0xe1]
        rows.append(dict(case=f'length{n}',passed=True))
    for fault,code in [((1,1),4),((2,0x80),4),((2,8),4),((3,1),5),((5,1),5),
                       ((7,1),8),((8,1),8),((9,1),8),((16,1),8),((17,1),8),((18,1),8), (('CRC',1),4)]:
        m=machine(a.arm);seed(m);m.endpoint.corrupt=fault
        if a.needed:m.put(m.w,'nes_sink_window184','retired',65535,2)
        # An empty previous queue with progress is legal: force illegal progress
        # with pending flag for this explicit reserved/progress guard.
        if fault==(2,8):m.endpoint.corrupt=(2,9)
        assert not send(m,packet(seq=1)),fault
        assert m.get(m.w,'nes_sink_window184','error')==code,fault
        assert m.get(m.w,'nes_sink_window184','sent',2)==1 and m.get(m.w,'nes_sink_window184','retired',2)==(65535 if a.needed else 1)
        calls=len(m.endpoint.calls);assert not send(m,packet(seq=1));assert len(m.endpoint.calls)==calls
        rows.append(dict(case=str(fault),passed=True,error=code,no_retry=True))
    m=machine(a.arm);seed(m,65535);m.endpoint.auto=True
    for i in range(8):assert send(m,packet(seq=(65535+i)&65535))
    assert m.get(m.w,'nes_sink_window184','sent',2)==7 and m.get(m.w,'nes_sink_window184','retired',2)==(5 if a.needed else 6)
    assert m.endpoint.calls.count(0xe0)==1
    rows.append(dict(case='wrap_and_shared_credit',passed=True,E0=1,E1=8))
    m=machine(a.arm)
    for i in range(4):assert send(m,packet(n=0,seq=i))
    m.endpoint.auto=True;assert send(m,packet(n=0,seq=4));assert m.endpoint.calls.count(0xe0)==2
    rows.append(dict(case='short_full_credit_fallback',passed=True))
    for stop in (False,True):
        m=machine(a.arm);seed(m);m.endpoint.stop_after=stop
        ok=send(m,packet(op=3,n=168,seq=1),True)
        assert ok!=stop
        if stop:
            assert m.get(m.w,'nes_sink_window184','error')==2 and m.endpoint.retired==1
            assert m.endpoint.calls.count(0xe0)==1
        else:
            assert m.endpoint.final_polls==2 and m.endpoint.retired==2
            assert bytes(m.u.mem_read(m.q+300,12))==m.endpoint.last and m.endpoint.last[:2]==b'\1\3'
        rows.append(dict(case='STOP_after_E1' if stop else 'mandatory_final_ACK',passed=True))
    if a.needed:
        m=machine(a.arm);seed(m);m.endpoint.corrupt=('CRC',1)
        assert send(m,packet(seq=1)) and m.get(m.w,'nes_sink_window184','retired',2)==1
        rows.append(dict(case='unused_response_does_not_publish_credit',passed=True))
    r=dict(passed=True,needed=a.needed,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope=__doc__)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print('PASS709 linked guards',len(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--needed',action='store_true')
    run(p.parse_args())
