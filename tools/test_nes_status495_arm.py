# SPDX-License-Identifier: MIT
"""Linked495 progress CRC/credit and full final ACK;493 comparison on fixed polls.

SPI/consumer latency is a fixture, not physical ARM/IRQ/ROM/common-clock time.
"""
import argparse,inspect,json
from pathlib import Path
import check_nes_supply485_arm as base
from check_nes_hardware494_termination import SealDeadline
from check_nes_game478 import crc,sha
from unicorn.arm_const import UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3

class Endpoint(base.Endpoint):
    def exchange(self,tx,clock):
        if tx[0]!=0xeb:return super().exchange(tx,clock)
        assert len(tx)==8
        r=super().exchange(b'\xe0'+bytes(19),clock);self.calls[-1]=tx.hex()
        b=bytearray(r[:7]+b'\0');b[1]=0xf8;b[7]=crc(b[1:7],8,7,0);return bytes(b)

class Seal(SealDeadline):
    def __init__(self,src,delay,mutation=None,pressure=True):
        self.delay=delay;self.mutation=mutation;self.wire=[]
        super().__init__(src,'normal')
        if pressure:
            for field,size in [('cgram',512),('oam',544),('hdma',1121)]:
                self.u.mem_write(self.video+self.layout['nes_native_video165'][field],bytes((i*37+17)&255 for i in range(size)))
            self.put(self.video,'nes_native_video165','hdma_size',1121,2)
    def hook(self,u,at,size,user):
        if at!=getattr(self,'spi',0):super().hook(u,at,size,user);return
        n=u.reg_read(UC_ARM_REG_R3);txat=u.reg_read(UC_ARM_REG_R1);rxat=u.reg_read(UC_ARM_REG_R2)
        tx=bytes(u.mem_read(txat,n));short=tx[0]==0xeb;self.wire.append(tx)
        if short:u.mem_write(txat,b'\xe0');u.reg_write(UC_ARM_REG_R3,20)
        self.mode='wait'if self.last and self.last[0]==3 and self.seal_polls<self.delay else 'normal'
        super().hook(u,at,size,user)
        if short:
            b=bytearray(u.mem_read(rxat,7)+b'\0');b[1]=0xf8
            if self.mutation=='header':b[1]=0xf7
            if self.mutation=='flags':b[2]|=8
            if self.mutation=='accepted':b[4]^=1
            if self.mutation=='retired':b[5]^=1
            b[7]=crc(b[1:7],8,7,0)
            if self.mutation=='CRC':b[7]^=1
            u.mem_write(rxat,bytes(b));u.mem_write(txat,b'\xeb');u.reg_write(UC_ARM_REG_R3,n)
        elif tx[0]==0xe0 and self.last and self.last[0]==3 and self.mutation=='full_ACK_identity':
            b=bytearray(u.mem_read(rxat,20));b[9]^=1;b[19]=crc(b[1:19],8,7,0);u.mem_write(rxat,bytes(b))

def seal(src,delay,mutation=None,pressure=True):
    m=Seal(src,delay,mutation,pressure);before=m.instructions;ok=m.call('nes_sink212_seal',[m.s,m.video,m.resident])
    row={'ok':ok,'delay_polls':delay,'mutation':mutation,'wire_B':sum(map(len,m.wire)),
         'E0':sum(q[0]==0xe0 for q in m.wire),'EB':sum(q[0]==0xeb for q in m.wire),
         'window_error':m.get(m.w,'nes_sink_window184','error'),'displayed':bool(m.get(m.s,'nes_native_sink165','displayed')),
         'instructions':m.instructions-before,'E1_bytes':[q.hex()for q in m.wire if q[0]==0xe1]}
    if mutation:
        assert not ok and not row['displayed'] and row['window_error']==(8 if mutation=='full_ACK_identity'else 5 if mutation in ['accepted','retired']else 4)
        before=len(m.wire);assert not m.call('nes_sink212_seal',[m.s,m.video,m.resident])and len(m.wire)==before
    else:assert ok and row['displayed'] and row['window_error']==0
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    base.Endpoint=Endpoint
    s=inspect.getsource(base.run);s=s.replace("and any(q['bulk'] for q in prefix[2:])","and all(q['accepted_E9']==1 and q['bulk']==0 for q in prefix[2:])")
    ns=dict(base.__dict__);exec(compile(s,'495 retained plan ownership','exec'),ns)
    modes=['normal','normal_final_grant','normal_two_frames','bad_E8_CRC','wrong_generation','same_token_mutation','old_token','bad_ACK','bad_accepted','STOP_after_E9','STOP_after_bulk','ambiguous_E1']
    ownership=[ns['run'](a.arm,m)for m in modes]
    pairs=[]
    for delay in [0,1,3,10,75]:
        old,new=seal(a.baseline,delay),seal(a.arm,delay);assert old['E1_bytes']==new['E1_bytes']
        pairs.append({'delay_polls':delay,'baseline':old,'candidate':new,'wire_saved_B':old['wire_B']-new['wire_B']})
    old,new=seal(a.baseline,0,pressure=False),seal(a.arm,0,pressure=False)
    assert old['E1_bytes']==new['E1_bytes'] and new['wire_B']-old['wire_B']==8
    no_wait={'baseline':old,'candidate':new,'wire_saved_B':-8}
    negatives=[seal(a.arm,3,m)for m in ['header','flags','CRC','accepted','retired','full_ACK_identity']]
    r={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),
       'baseline_SHA256':sha(a.baseline/'obj-nes-100/firmware.stm'),'ownership':ownership,'pairs':pairs,'negative_cases':negatives,'no_pressure_no_wait':no_wait,
       'physical_time':False,'zero_wait_can_regress':True,'no_final_ACK_bypass':True,'payloads_equal':True}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'ownership':len(ownership),'negative_cases':len(negatives),'wire_savings':[(x['delay_polls'],x['wire_saved_B'])for x in pairs]}))
