"""Execute map-to-tile ownership, checked drain and callback faults in linked M4."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR

class Handoff(ARM):
    callback=0x0807ffb0
    def __init__(self,src,case):
        self.case=case;self.reasons=[];self.ops=[]
        super().__init__(src,'normal')
    def hook(self,u,at,size,user):
        if at==self.callback:
            reason=u.reg_read(UC_ARM_REG_R2)
            if reason!=4:
                assert reason in (0,1,2,3),(self.case,reason)
                u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
            self.reasons.append(reason)
            assert self.get(self.w,'nes_sink_window184','sent',2)==self.get(self.w,'nes_sink_window184','retired',2)
            assert not self.get(self.p,'nes_plan200','bulk_pending')
            if self.case=='STOP_after_input':self.endpoint.mode='STOP_after_bulk';self.endpoint.bulk=1
            u.reg_write(UC_ARM_REG_R0,int(self.case!='failed_input'))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)

def run(src,case,sent=2,multi=False,flush=False):
    m=Handoff(src,case);m.setup()
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',0 if case=='cold' else 2,1),('bulk_valid',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
    old=bytes((1,0))+struct.pack('<HHHI',16,0,907,1)
    m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],old)
    for k,v,n in [('sent',sent,2),('retired',(sent-1)&65535,2),('ever_sent',1,1),('wait',m.callback|1,4)]:m.put(m.w,'nes_sink_window184',k,v,n)
    last=bytes((2,0 if case=='last_tile' else 2))+struct.pack('<HIH',(sent-1)&65535,1,907)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    # Queue counters persist across frames; packet sequence is frame-local.
    m.put(m.s,'nes_native_sink165','sequence',2,2)
    count=0
    def exchange(tx,clock):
        nonlocal count
        m.ops.append(tx[0]);r=bytearray(len(tx))
        if tx[0]==0xe8:
            count+=1;r[1:3]=bytes((0xd7,4))
            if case=='repeat' and count>1:r[3]=2
            else:
                kind=int(case in ('single_OBJ','multi_OBJ'))
                size={'single_BG':16,'single_OBJ':32,'multi_OBJ':64}.get(case,48)
                r[6:18]=old if case=='repeat' else bytes((1,kind))+struct.pack('<HHHI',size,32,908 if case=='generation' else 907,2)
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_E8_CRC')
        elif tx[0]==0xe0:
            r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack('>HH',(sent-int(case=='credit'))&65535,sent)
            r[7:19]=bytes((0,last[0]))+last[2:10]+bytes((0x65,0x9a))
            if case=='identity':r[10]^=1
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_E0_CRC')
        elif tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            assert tx[1]==7 and tx[17:21]==struct.pack('<I',2)
        else:raise AssertionError(tx.hex())
        return bytes(r)
    m.endpoint.exchange=exchange
    ok=m.call('nes_plan527_map_credit',[m.p,m.q]) if flush else m.call('nes_plan200_progress',[m.p,0])
    positive=case in ('normal','cold','last_tile','repeat','single_BG','single_OBJ','multi_OBJ')
    assert bool(ok)==positive,(case,ok,m.ops,m.reasons)
    entered=case in ('normal','generation','failed_input','STOP_after_input','multi_OBJ') or (not multi and case in ('single_BG','single_OBJ'))
    assert m.reasons==([4] if entered else []),(case,m.reasons)
    assert (0xe1 in m.ops)==(positive and case!='repeat')
    if case=='normal':assert m.ops==[0xe8,0xe0,0xe1]
    if not positive or case=='repeat':assert bytes(m.u.mem_read(m.p+m.layout['nes_plan200']['bulk'],12))==old
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,sent=sent,result=bool(ok),operations=m.ops,input_callbacks=m.reasons,final_ACK_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--multi',action='store_true');p.add_argument('--credit',action='store_true');a=p.parse_args()
    rows=[run(a.arm,c,multi=a.multi) for c in ('normal','cold','last_tile','repeat','generation','bad_E8_CRC','credit','identity','bad_E0_CRC','failed_input','STOP_after_input','single_BG','single_OBJ','multi_OBJ')]
    rows.append(run(a.arm,'normal',65535,multi=a.multi))
    if a.credit:rows += [run(a.arm,c,flush=True) for c in ('normal','last_tile','STOP_after_input')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope='Linked plan/window/sink; modeled input callback. Actual callback CRC/STOP/cold behavior is checked separately by check_nes_idle676.'),indent=2)+'\n',newline='\n')
    print('PASS678',len(rows),'handoff/credit/identity/STOP/cold/wrap cases')
