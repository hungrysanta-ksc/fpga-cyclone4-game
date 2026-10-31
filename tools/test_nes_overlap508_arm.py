# SPDX-License-Identifier: MIT
"""Linked508 watermark, plan guards and ordinary/bulk ownership; no timing claim."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc,sha
from check_nes_hardware503_termination import GuardDeadline

def plan_case(src,mode):
    m=ARM(src,mode);m.setup();ok=True
    for k,s,t in [(2,0,0),(0,1,4),(0,2,7),(1,0,8),(1,1,9)]:
        if not m.emit(k,s,t):ok=False;break
    if ok:ok=bool(m.call('nes_plan200_end',[m.p]))
    if ok:ok=bool(m.call('nes_plan200_progress',[m.p,1]))
    if mode=='normal':
        assert ok and m.endpoint.sent==m.endpoint.retired==5 and not m.endpoint.jobs
        assert m.call('nes_plan200_retire',[m.p])==0 and not m.endpoint.rearmed
    else:
        assert not ok,mode
        before=len(m.endpoint.calls);assert m.emit(0,3,10)==0 and len(m.endpoint.calls)==before,mode
    return dict(mode=mode,accepted=ok,plan_error=m.get(m.p,'nes_plan200','error'),window_error=m.get(m.w,'nes_sink_window184','error'))

class Mixed(Endpoint):
    def __init__(self,mode='normal'):
        super().__init__(mode);self.release=0;self.ordinary=0;self.early=False
    def advance(self,clock):
        while self.pending and self.pending[0][0]<=clock:
            _,b=self.pending.pop(0)
            if b[0]==7:
                assert int.from_bytes(b[16:20],'little')==self.jobs[0][3]
                self.stale=self.descriptor();self.stale_reads=2;self.jobs.pop(0)
            self.retired+=1;self.last=bytes([0,b[0]])+b[2:10]+b'\x65\x9a'
    def exchange(self,tx,clock):
        op=tx[0];self.advance(clock)
        if op==0xe8 and clock<self.release and not self.stale_reads:
            self.calls.append(tx.hex());r=bytearray(20);r[1:3]=b'\xd7\x04';r[4:6]=self.accepted.to_bytes(2,'big');r[19]=crc(r[1:19],8,7,0);return bytes(r)
        if op==0xe1 and tx[1]!=7:
            self.calls.append(tx.hex());b=tx[1:-2]
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            assert b[0]in[2,4] and b[2:4]==self.sent.to_bytes(2,'little')
            assert self.sent-self.retired<4
            self.early|=bool(self.jobs);self.sent+=1;self.ordinary+=1;self.pending.append((clock+1000,b))
            return bytes(len(tx))
        r=super().exchange(tx,clock)
        if op==0xe9 and self.end:self.release=clock+5000
        return r

def mixed_case(src,stop):
    m=ARM(src,'normal');m.endpoint=Mixed();m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    assert m.emit(2,0,0) and m.emit(0,1,4) and m.emit(0,2,7)
    assert m.call('nes_plan200_end',[m.p])==1
    payload=0x20002300;m.u.mem_write(payload,b'\x01\x02\x03\x04')
    assert m.call('packet_wire',[m.s,2,3,0,payload,4,0])==1
    assert m.endpoint.ordinary==1 and m.endpoint.early
    if stop:
        m.endpoint.mode='STOP_after_E9';before=len(m.endpoint.calls)
        assert m.call('packet_wire',[m.s,2,3,4,payload,4,0])==0
        assert len(m.endpoint.calls)==before and not m.get(m.s,'nes_native_sink165','displayed')
    else:
        for i in range(1,6):assert m.call('packet_wire',[m.s,2,3,i*4,payload,4,0])==1
        assert m.call('nes_plan200_progress',[m.p,1])==1
        ack=0x20002400;assert m.call('nes_window184_drain',[m.w,ack])==1
        assert m.endpoint.bulk==3 and m.endpoint.ordinary==6 and m.endpoint.sent==m.endpoint.retired==9
        assert m.emit(0,3,8)==0 # no plan after END
    assert not m.endpoint.rearmed
    return dict(STOP=stop,early_ordinary=m.endpoint.early,ordinary=m.endpoint.ordinary,bulk=m.endpoint.bulk,no_EA=True)

class Window:
    mode='normal';bulk=0;accepted=0
    def __init__(self,sent,retired,last,bad):self.sent=sent;self.retired=retired;self.last=last;self.bad=bad;self.calls=[]
    def exchange(self,tx,clock):
        assert tx[0]==0xe0;self.calls.append(tx.hex());r=bytearray(20);r[1]=0xf7
        used=(self.sent-self.retired)&65535;r[2]=int(used!=0)|2|(4 if used==4 else 0)
        r[3:7]=struct.pack('>HH',self.sent,self.retired);r[7:19]=bytes([0,self.last[0]])+self.last[2:10]+b'\x65\x9a'
        if self.bad=='endpoint_fault':r[2]|=8
        if self.bad=='identity':r[9]^=1
        if self.bad=='future_retire':r[5:7]=struct.pack('>H',(self.sent+1)&65535)
        if self.bad=='accepted':r[4]^=1
        r[19]=crc(r[1:19],8,7,0)
        if self.bad=='crc':r[19]^=1
        return bytes(r)

def watermark_case(src,base,kind):
    m=ARM(src,'normal');m.setup();sent=(base+2)&65535;target=(base+1)&65535
    retired=target if kind=='partial'else sent
    if kind=='future_target':target=(sent+1)&65535
    if kind=='stale_target':target=(sent-5)&65535
    last=bytes([2,3])+struct.pack('<HIH',1,1,907)
    for k,v,n in [('sent',sent,2),('retired',base,2),('ever_sent',1,1)]:m.put(m.w,'nes_sink_window184',k,v,n)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    m.endpoint=Window(sent,retired,last,kind)
    ok=m.call('nes_window184_through',[m.w,0x20002400,target]);assert bool(ok)==(kind in ['partial','full']),(base,kind,ok)
    if kind=='partial':assert m.get(m.w,'nes_sink_window184','retired',2)==target!=sent
    return dict(base=base,mode=kind,accepted=bool(ok),E0=len(m.endpoint.calls))

def termination_case(src,mode):
    m=GuardDeadline(src,mode);p=m.rt+m.layout['nes_native_runtime165']['plan']
    # Directed fixture starts after modeled tile completion. Real final SEAL,
    # native deadline guard, window, sink and resident commit execute below.
    for k,v,n in [('started',1,1),('ending',1,1),('finished',1,1),('generation',907,2)]:m.put(p,'nes_plan200',k,v,n)
    ok=m.call('nes_sink212_seal',[m.s,m.video,m.resident])
    r=dict(mode=mode,ok=ok,runtime=m.get(m.rt,'nes_native_runtime165','result'),window=m.get(m.w,'nes_sink_window184','error'),sink=m.get(m.s,'nes_native_sink165','error'),displayed=m.get(m.s,'nes_native_sink165','displayed'),resident_displayed=m.get(m.resident,'nes_resident211','displayed'))
    if mode=='normal':assert ok and r['displayed'] and r['resident_displayed'] and r['runtime']==r['window']==r['sink']==0,r
    else:
        assert not ok and r['runtime']==(3 if mode=='IO_fault'else 1) and r['window']==(2 if mode=='guard_deadline'else 3) and r['sink']==2,r
        assert r['displayed']==r['resident_displayed']==0
        before=len(m.calls);assert m.call('nes_sink212_seal',[m.s,m.video,m.resident])==0 and len(m.calls)==before
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    plans=[plan_case(a.arm,n)for n in ['normal','bad_E8_CRC','wrong_generation','same_token_mutation','old_token','bad_ACK','bad_accepted','STOP_after_E9','STOP_after_bulk','ambiguous_E1']]
    mixed=[mixed_case(a.arm,s)for s in [False,True]]
    marks=[watermark_case(a.arm,b,k)for b in [0,65534]for k in ['partial','full','future_target','stale_target','future_retire','identity','accepted','crc','endpoint_fault']]
    termination=[termination_case(a.arm,k)for k in ['normal','guard_deadline','deadline','IO_fault']]
    r=dict(passed=True,scope=__doc__,firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),plans=plans,mixed=mixed,watermarks=marks,termination=termination)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
