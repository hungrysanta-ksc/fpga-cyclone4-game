"""Exercise linked final-ACK receive credit and useful-input pause ownership."""
import argparse,json,struct
from pathlib import Path
from check_nes_idle676 import Receiver
from check_nes_game478 import sha,crc,UC_HOOK_CODE,UC_ARM_REG_R3,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR

def check(src,case,reason,useful,batch=False):
    mode='normal' if case in ('wrap','output_progress','zero_credit','plan_busy') else case
    m=Receiver(src,mode);pauses=[]
    if reason<=1:
        from elftools.elf.elffile import ELFFile
        from test_nes_raw506_joint import member_offset
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            ds=[d for cu in ELFFile(f).get_dwarf_info().iter_CUs() for d in cu.iter_DIEs() if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_plan200' and d.attributes.get('DW_AT_byte_size')]
            off=next(member_offset(c) for c in ds[0].iter_children() if c.tag=='DW_TAG_member' and c.attributes['DW_AT_name'].value==b'finished')
        m.u.mem_write(m.rt+m.layout['nes_native_runtime165']['plan']+off,bytes([case!='plan_busy']))
        if case=='zero_credit':m.put(m.state,'nes_native165','state',0,1)
    m.put(m.rt,'nes_native_runtime165','prefetch_left',0 if case=='zero_credit' else 7,1)
    if case=='wrap':
        m.start_token=65535
        m.put(m.state,'nes_native165','next_token',65535,2)
        m.put(m.state,'nes_native165','token_valid',1,1)
    m.u.hook_add(UC_HOOK_CODE,lambda u,p,s,d:pauses.append(u.reg_read(UC_ARM_REG_R3)),begin=m.syms['nes_cost474_pause'],end=m.syms['nes_cost474_pause'])
    output=case=='output_progress'
    ok=m.call('wait634',[m.rt,m.check|1,reason,int(output)])
    success=case in ('normal','wrap','empty','complete','output_progress','zero_credit','plan_busy')
    assert bool(ok)==success,(reason,case,ok,m.ops)
    left=m.get(m.rt,'nes_native_runtime165','prefetch_left')
    if case in ('normal','wrap'):
        assert left==6 and m.ops==[0xd0,0xd1,0xd2,0xd0]+([0xd0] if batch and reason==2 else []),(case,left,m.ops)
        assert m.get(m.state,'nes_native165','next_token',2)==(0 if case=='wrap' else 1)
        assert pauses==([int(useful)] if reason!=4 else [])
    elif case=='empty':
        assert left==7 and m.ops==[0xd0]
        assert pauses==([0] if reason!=4 else [])
        assert m.call('wait634',[m.rt,m.check|1,reason,0]) and m.get(m.rt,'nes_native_runtime165','prefetch_left')==7
        header=(0x2233<<48)|(32<<42)|(2<<36)|(224<<28)
        m.packets=[struct.pack('>HHQ',0xe000,953,header)]
        assert m.call('wait634',[m.rt,m.check|1,reason,0]) and m.get(m.rt,'nes_native_runtime165','prefetch_left')==6
    elif case in ('complete','output_progress','zero_credit','plan_busy'):
        assert not m.ops and left==(0 if case=='zero_credit' else 7)
    else:assert left==7,(case,left)
    assert not any(x in (0xd3,0xe1,0xea) for x in m.ops)
    return dict(reason=reason,case=case,success=bool(ok),remaining=left,operations=m.ops,pause_progress=pauses)

class Burst(Receiver):
    def __init__(self,src,mode):
        self.burst_mode=mode
        super().__init__(src,'normal')
        self.packets += [struct.pack('>HHH',i,953,i) for i in range(7)]
        if mode=='empty_after3':self.packets=self.packets[:3]
        self.put(self.rt,'nes_native_runtime165','prefetch_left',7,1)
    def hook(self,u,at,size,user):
        if at==self.syms.get('nes_native165_poll') and self.index==1 and self.burst_mode in ('cache_CRC','cache_token'):
            ptr=self.state+self.layout['nes_native165']['status183'];b=bytearray(u.mem_read(ptr,8))
            if self.burst_mode=='cache_CRC':b[7]^=1
            else:b[4]^=1;b[7]=crc(b[1:7],8,7,0)
            u.mem_write(ptr,bytes(b))
        if at==self.spi:
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
            if tx[0]==0xd1:assert tx[1:]==bytes(n-1)
            elif tx[0] in (0xd0,0xd2):assert n==8 and tx[6]==crc(tx[:6],8,7,0) and tx[7]==0xa5
        if at==self.check and self.burst_mode=='STOP_after3' and self.index==3:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==self.spi and self.burst_mode=='CRC_third' and self.index==2 and bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))[0]==0xd1:
            rx=u.reg_read(UC_ARM_REG_R2);n=u.reg_read(UC_ARM_REG_R3)
            super().hook(u,at,size,user)
            b=bytes(u.mem_read(rx+n-1,1));u.mem_write(rx+n-1,bytes([b[0]^1]));return
        super().hook(u,at,size,user)

def burst(src,case):
    m=Burst(src,case);m.u.mem_write(0x20018000,bytes([0xa5])*0x8000);ok=m.call('wait634',[m.rt,m.check|1,2,0]);left=m.get(m.rt,'nes_native_runtime165','prefetch_left')
    expected={'cap7':(True,7,0),'empty_after3':(True,3,4),'STOP_after3':(False,3,4),'CRC_third':(False,2,5),'cache_CRC':(False,1,6),'cache_token':(False,1,6)}[case]
    assert (bool(ok),m.index,left)==expected,(case,ok,m.index,left,m.ops)
    assert not any(x in (0xd3,0xe0,0xe1,0xea) for x in m.ops)
    assert m.state_value()!=4
    return dict(case=case,success=bool(ok),checked_blocks=m.index,remaining=left,operations=m.ops,commit=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--progress',action='store_true');p.add_argument('--credit',action='store_true');p.add_argument('--batch',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cases=[check(a.arm,c,r,a.progress,a.batch) for r in (2,4) for c in ('normal','wrap','empty','complete','STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO')]
    cases.extend(check(a.arm,c,2,a.progress,a.batch) for c in ('output_progress','zero_credit'))
    if a.credit:
        cases.extend(check(a.arm,c,r,a.progress,a.batch) for r in (0,1) for c in ('normal','wrap','empty','complete','STOP_before','STOP_after_READ','bad_CRC','bad_retire','failed_IO','output_progress','zero_credit','plan_busy'))
    m=Receiver(a.reference,'empty');m.put(m.rt,'nes_native_runtime165','prefetch_left',7,1)
    assert m.call('wait634',[m.rt,m.check|1,2,0]);assert m.get(m.rt,'nes_native_runtime165','prefetch_left')==6
    if a.batch:cases.extend(burst(a.arm,c) for c in ('cap7','empty_after3','STOP_after3','CRC_third','cache_CRC','cache_token'))
    r=dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=cases,reference=dict(firmware=sha(a.reference/'obj-nes-100/firmware.stm'),empty_spends_credit=True),scope='Linked ARM callback, real CRC and checked READ/POP. Progress flag inspected at actual pause function entry; full timing checked separately.')
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print('PASS682',len(cases),'credit, CRC, STOP, wrap, output priority and pause cases')
