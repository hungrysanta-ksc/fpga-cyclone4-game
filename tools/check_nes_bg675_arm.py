"""Execute actual linked ARM with independent plan credit and delayed tile receipts."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR


class Grant(Endpoint):
    def __init__(self,mode):
        super().__init__('normal');self.test_mode=mode;self.pair_seen=False;self.overlap=False;self.counts=[]
    def exchange(self,tx,clock):
        self.advance(clock)
        if tx[0]==0xe9:
            old=self.jobs;self.jobs=[]
            r=super().exchange(tx,clock)
            self.jobs=old+self.jobs;self.counts.append(tx[3])
            if self.accepted==2:self.overlap=bool(old)
            return r
        r=super().exchange(tx,clock)
        if tx[0]==0xe1:
            when,b=self.pending[-1];self.pending[-1]=(clock+50000,b)
            if self.test_mode=='STOP_after_zero':self.mode='STOP_after_bulk'
            if self.test_mode=='ambiguous':self.mode='ambiguous_E1'
        if tx[0]==0xe8:
            r=bytearray(r);r[3]=2 if self.end else 1
            # A writable bank does not imply that the zero tile was consumed.
            if self.accepted==1 and self.pair_seen:
                if self.test_mode=='busy_once':r[3]=0;self.test_mode='normal'
                if self.test_mode=='bad_count':r[5]^=1
                if self.test_mode=='wrong_generation':r[12]^=1
                if self.test_mode=='mutated_token' and self.bulk:r[10]^=1
            r[19]=crc(r[1:19],8,7,0)
            if self.accepted==1 and self.pair_seen and self.test_mode=='bad_crc':r[19]^=1
            return bytes(r)
        return r


class CheckARM(ARM):
    def __init__(self,src,mode):
        self.test_mode=mode;self.after_pair_query=False
        super().__init__(src,'normal');self.endpoint=Grant(mode)
    def hook(self,u,at,size,user):
        if at==getattr(self,'spi',0):
            self.endpoint.pair_seen=self.get(self.p,'nes_plan200','count')==2 and self.endpoint.accepted==1
            if self.endpoint.pair_seen:self.after_pair_query=True
        if at==self.guard485:
            pair=self.endpoint.accepted==1 and self.get(self.p,'nes_plan200','count')==2
            if (self.test_mode=='STOP_before_pair' and pair) or (self.test_mode=='STOP_before_E9' and self.after_pair_query):
                u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)


def run(src,history,mode):
    m=CheckARM(src,mode);m.setup();m.put(m.p,'nes_plan200','bank_history',history,1)
    prefix=[];ok=True
    jobs=[(2,0,0)]+[(0,i,4+i) for i in range(1,11)]+[(1,i,30+i) for i in range(12)]
    for kind,slot,tag in jobs:
        ok=bool(m.emit(kind,slot,tag));prefix.append(m.endpoint.accepted)
        if not ok:break
    positive=mode in ('normal','busy_once')
    if ok:ok=bool(m.call('nes_plan200_end',[m.p]))
    if ok:ok=bool(m.call('nes_plan200_progress',[m.p,1]))
    assert ok==positive,(history,mode,prefix,m.get(m.p,'nes_plan200','error'))
    e=m.endpoint
    if positive:
        assert len(e.plans)==len(jobs) and e.sent==e.retired==len(jobs) and not e.jobs
        if history==2:
            assert prefix[:4]==[0,1,1,2] and e.counts==[2,2,7,13],(prefix,e.counts)
            assert e.overlap
        else:assert prefix[:4]==[0,1,1,1]
        assert not m.get(m.p,'nes_plan200','bulk_pending')
        assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
    else:
        count=len(e.calls);assert not m.emit(0,22,23) and len(e.calls)==count
        assert e.accepted==1 and not e.rearmed
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(history=history,case=mode,accepted_counts=e.counts,overlap=e.overlap,
                error=m.get(m.p,'nes_plan200','error'),final_ACK_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();rows=[run(a.arm,h,'normal') for h in (0,1,2)]
    rows += [run(a.arm,2,c) for c in ('busy_once','bad_crc','bad_count','wrong_generation','mutated_token','STOP_after_zero','STOP_before_pair','STOP_before_E9','ambiguous')]
    a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,
        scope='Linked ARM, independently modeled bank credit and delayed consumption. No fabricated final ACK, no hardware timing claim.'),indent=2)+'\n')
    print('PASS675',len(rows),'linked ARM ownership/STOP/integrity cases')
