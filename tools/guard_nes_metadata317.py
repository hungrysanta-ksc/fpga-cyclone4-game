# SPDX-License-Identifier: MIT
"""Actual M4 preparation priority, cancellation and separate early buffer."""
import inspect
import guard_nes_prepare309 as old
from probe_nes_arm264 import crc

def main():
    s=inspect.getsource(old.main)
    s=s.replace('0,4,0,0,True','0,2,0,0,True').replace('0,4,0,0,False','0,2,0,0,False')
    s=s.replace('1,4,0,0,False','1,2,0,0,False').replace('0,3,0,0,False','0,1,0,0,False')
    s=s.replace('0,1,65533,0,True','0,1,65535,0,True').replace("struct.pack('<HH',4,0)","struct.pack('<HH',2,0)")
    pos=s.index('    r=dict(passed=True')
    extra='''    class Reply317:
        def __init__(self):self.tx=[];self.bad=False
        def transfer(self,tx):
            assert tx[0]==0xe1 and tx[1]==15
            assert crc(tx[:-2])==int.from_bytes(tx[-2:],'big')
            self.tx.append(tx);r=bytearray(len(tx));r[1]=0xfb
            state=bytes(arm.uc.mem_read(arm.symbols['state259'],4))
            a=int.from_bytes(state[:2],'little');t=int.from_bytes(state[2:],'little');used=(a-t)&65535
            r[2]=(used!=0)|((used==2)<<2);r[3:5]=a.to_bytes(2,'big');r[5:7]=t.to_bytes(2,'big')
            r[13]=crc(r[1:13],8)^int(self.bad);return bytes(r)
    for label,full,bad,stop,wrap in [('early',False,False,False,False),('full',True,False,False,False),
                                   ('CRC reject',False,True,False,False),('STOP',False,False,True,False),
                                   ('counter wrap',False,False,False,True)]:
        restore()
        for _ in range(12):assert arm.call('prepare_slice309',[])
        put('begin',1);put('requirements264',0)
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HHHHIIBB',65535 if wrap else 2 if full else 0,65535 if wrap else 0,0,1,1,0,0,0))
        ep=Reply317();ep.bad=bad;arm.endpoint=ep;arm.symbols['io259']=arm.symbols['physical267']
        arm.uc.mem_write(arm.symbols['wire259'],b'\\xa5'*259)
        if stop:arm.call('stop286',[])
        ok=arm.call('issue_metadata317',[])
        assert bytes(arm.uc.mem_read(arm.symbols['wire259'],259))==b'\\xa5'*259
        assert len(ep.tx)==(0 if full or stop else 1)
        if bad:assert not ok and word('requirements264')==0
        elif not full and not stop:
            assert ok and word('requirements264')==1
            packet=ep.tx[0][1:-2]
            if packet[1]==1:
                from analyze_nes_ingress306 import decode
                payload=packet[16:40]+decode(packet[41:],166)
            else:payload=packet[16:]
            assert payload==expected[16:]
            assert arm.call('issue_metadata317',[]) and len(ep.tx)==1
        rows.append(dict(case='metadata '+label,transfers=len(ep.tx)))
'''
    s=s[:pos]+extra+s[pos:]
    ns=dict(old.__dict__);ns.update(crc=crc,__file__=__file__)
    exec(compile(s,'guard317','exec'),ns);ns['main']()
if __name__=='__main__':main()
