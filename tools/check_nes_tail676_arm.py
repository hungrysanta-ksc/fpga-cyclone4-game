"""Check final13-record E9 admission while a prior tile retains its identity."""
import argparse,json
from pathlib import Path
from check_nes_bg675_arm import CheckARM,Grant,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR

class Tail(Grant):
    def __init__(self,case):
        super().__init__('normal');self.case=case;self.final_waiting=False
        self.final_overlap=False;self.busy_seen=False
    def exchange(self,tx,clock):
        old=bool(self.jobs)
        r=super().exchange(tx,clock)
        if tx[0]==0xe9 and tx[3]==13:self.final_overlap=old
        if tx[0]==0xe8 and self.final_waiting:
            r=bytearray(r)
            if self.case=='busy_once' and not self.busy_seen:r[3]=0;self.busy_seen=True
            if self.case=='bad_count':r[5]^=1
            if self.case=='wrong_generation':r[12]^=1
            if self.case=='mutated_token' and self.bulk:r[10]^=1
            r[19]=crc(r[1:19],8,7,0)^(self.case=='bad_crc')
            return bytes(r)
        return r

class Machine(CheckARM):
    def __init__(self,src,case):
        super().__init__(src,'normal');self.endpoint=Tail(case);self.case=case
    def hook(self,u,at,size,user):
        if at==getattr(self,'spi',0):
            self.endpoint.final_waiting=bool(self.get(self.p,'nes_plan200','ending')) and self.endpoint.accepted==3
        if at==self.guard485 and self.case=='STOP_before_final' and self.get(self.p,'nes_plan200','ending') and self.endpoint.accepted==3:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)

def run(src,case):
    m=Machine(src,case);m.setup();m.put(m.p,'nes_plan200','bank_history',2,1)
    jobs=[(2,0,0)]+[(0,i,4+i) for i in range(1,11)]+[(1,i,30+i) for i in range(12)]
    for job in jobs:assert m.emit(*job)
    ok=m.call('nes_plan200_end',[m.p])
    if ok:ok=m.call('nes_plan200_progress',[m.p,1])
    good=case in ('normal','busy_once');assert bool(ok)==good,(case,ok)
    e=m.endpoint
    if good:
        assert e.counts==[2,2,7,13] and e.final_overlap
        assert e.sent==e.retired==len(jobs) and not e.jobs
        assert not m.get(m.p,'nes_plan200','bulk_pending')
    else:
        assert e.accepted==3 and e.counts==[2,2,7]
        n=len(e.calls);assert not m.call('nes_plan200_progress',[m.p,1]) and len(e.calls)==n
    assert not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
    assert not m.get(m.s,'nes_native_sink165','displayed')
    return dict(case=case,counts=e.counts,final_overlap=e.final_overlap,error=m.get(m.p,'nes_plan200','error'),final_ACK_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();rows=[run(a.arm,c) for c in ('normal','busy_once','bad_count','wrong_generation','mutated_token','bad_crc','STOP_before_final')]
    a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope='Actual linked M4, independent modeled credit and delayed receipts; final display ACK not synthesized.'),indent=2)+'\n')
    print('PASS676 final13-record grant',len(rows),'cases')
