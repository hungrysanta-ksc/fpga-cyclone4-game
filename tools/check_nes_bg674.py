"""Execute the linked warm BG pair handoff, STOP and integrity boundaries."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR


class PairARM(ARM):
    def __init__(self,src,mode):
        self.pair_mode=mode;self.pair_ready=False
        super().__init__(src,'normal')
        original=self.endpoint.exchange
        def exchange(tx,clock):
            rx=original(tx,clock)
            if tx[0]==0xe8 and self.endpoint.accepted==1 and self.get(self.p,'nes_plan200','count')==2:
                if rx[3]&1:
                    self.pair_ready=True
                    if mode=='pair_bad_crc':rx=rx[:-1]+bytes([rx[-1]^1])
                    elif mode=='pair_bad_count':
                        r=bytearray(rx);r[5]^=1;r[19]=crc(r[1:19],8,7,0);rx=bytes(r)
            return rx
        self.endpoint.exchange=exchange

    def hook(self,u,at,size,user):
        if at==self.guard485:
            armed=self.endpoint.accepted==1 and self.get(self.p,'nes_plan200','count')==2
            if (self.pair_mode=='pair_STOP_before_query' and armed) or (self.pair_mode=='pair_STOP_before_send' and self.pair_ready):
                u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)


def run(src,history,mode):
    m=PairARM(src,mode);m.setup();m.put(m.p,'nes_plan200','bank_history',history,1)
    prefix=[];ok=True
    for kind,slot,tag in ((2,0,0),(0,1,4),(0,2,7),(0,3,8)):
        ok=bool(m.emit(kind,slot,tag));prefix.append(m.endpoint.accepted)
        if not ok:break
    positive=mode=='normal'
    assert ok==positive,(history,mode,prefix)
    if positive:
        assert prefix==([0,1,1,2] if history==2 else [0,1,1,1]),prefix
        assert m.emit(1,0,10) and m.call('nes_plan200_end',[m.p])
        assert m.call('nes_plan200_progress',[m.p,1])
        assert len(m.endpoint.plans)==5 and m.endpoint.sent==m.endpoint.retired==5 and not m.endpoint.jobs
        assert not m.get(m.s,'nes_native_sink165','displayed')
        assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    else:
        assert prefix==[0,1,1,1] and m.endpoint.accepted==1
        calls=len(m.endpoint.calls)
        assert not m.emit(0,4,9) and len(m.endpoint.calls)==calls
        assert not m.endpoint.rearmed and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(history=history,mode=mode,E9_after_each_BG=prefix,passed=True,
                SPI_bytes=sum(len(bytes.fromhex(c)) for c in m.endpoint.calls),
                plan_error=m.get(m.p,'nes_plan200','error'),final_ACK_required=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows=[run(a.arm,h,'normal') for h in (0,1,2)]
    rows += [run(a.arm,2,m) for m in ('pair_STOP_before_query','pair_STOP_before_send','pair_bad_crc','pair_bad_count')]
    a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,
        scope='Actual linked M4; independently modeled descriptor/CRC/delayed ACK endpoint, no new physical timing or FPGA proof. No final display grant fabricated.'),indent=2)+'\n',newline='\n')
    print('PASS674 cold/one-bank/warm BG handoff and four exact pair-boundary rejection cases; final ACK still required')
