"""Real ARM SEAL -> bounded receive -> independent final identity ordering."""
import argparse,inspect,json,struct
from pathlib import Path
from check_nes_idle676 import Receiver
from check_nes_game478 import ELFFile,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from test_nes_raw506_joint import member_offset

class Seal(Receiver):
    def __init__(self,src,case):
        self.mode=case;self.sent=self.retired=self.e0=0;self.last=bytes(12);self.sealed=False
        super().__init__(src,case if case in ('STOP_after_READ','bad_CRC','bad_retire','failed_IO') else 'normal')
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            for cu in ELFFile(f).get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_sink_window184' and d.attributes.get('DW_AT_byte_size'):
                        self.layout['nes_sink_window184']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
        self.w=0x20016000;self.q=0x20017000
        assert self.call('nes_window184_init',[self.w,self.spi|1,self.check|1,self.rt,4])
        self.put(self.w,'nes_sink_window184','wait',self.syms['wait634']|1,4)
        self.ops.clear();self.e0=0
        self.put(self.rt,'nes_native_runtime165','prefetch_left',0,1)
        if case=='empty':self.packets=[]
        if case=='complete':self.put(self.state,'nes_native165','state',2,1)

    def hook(self,u,at,size,user):
        if at in (self.check,self.service) and self.mode=='STOP_after_SEAL' and self.sealed:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==self.spi:
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));op=tx[0]
            if op in (0xe0,0xe1):
                self.ops.append(op);rx=bytearray(n);ok=True
                if op==0xe1:
                    assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
                    p=tx[1:-2];self.sent+=1;self.sealed=p[0]==3
                    self.last=bytes((int(self.sealed),p[0]))+p[2:10]+bytes((0x65,0x9a))
                    ok=not(self.mode=='send_failure' and self.sealed)
                else:
                    self.e0+=1;self.retired=self.sent
                    if self.sealed and self.mode=='pending' and self.e0==1:self.retired-=1
                    if self.sealed and self.mode=='never_ACK':self.retired-=1
                    used=self.sent-self.retired
                    rx[1:3]=bytes((0xf7,(1 if used else 0)|(2 if self.retired else 0)))
                    rx[3:7]=struct.pack('>HH',self.sent,self.retired)
                    if self.retired:rx[7:19]=self.last
                    if self.sealed:
                        if self.mode=='wrong_identity':rx[10]^=1
                        if self.mode=='future_retire':rx[6]=(self.sent+1)&255
                        if self.mode=='fault':rx[2]|=0x80
                        if self.mode=='bad_magic':rx[18]^=1
                    rx[19]=crc(rx[1:19],8,7,0)^(self.sealed and self.mode=='bad_E0_CRC')
                u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx));u.reg_write(UC_ARM_REG_R0,int(ok));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)

def run(src,case):
    m=Seal(src,case)
    if case=='STOP_before':m.case='STOP_before'
    p=bytearray(16);p[0]=3;p[2:4]=(0).to_bytes(2,'little');p[4:8]=(123).to_bytes(4,'little');p[8:10]=(953).to_bytes(2,'little')
    m.u.mem_write(m.q,bytes(p));ack=0x20017100
    ok=m.call('nes_window184_barrier',[m.w,m.q,16,ack])
    positive=case in ('normal','pending','empty','complete')
    assert bool(ok)==positive,(case,ok,m.ops)
    if case=='STOP_before':
        assert not m.ops and not m.index
        return dict(case=case,passed=True,accepted=False,ops=[],input_blocks=0)
    assert m.ops[0]==0xe1 and not any(x in (0xd3,0xea) for x in m.ops)
    if case in ('send_failure','STOP_after_SEAL'):assert m.ops==[0xe1] and m.index==0
    elif case in ('STOP_after_READ','bad_CRC','bad_retire','failed_IO'):assert 0xe0 not in m.ops
    else:
        assert 0xe0 in m.ops
        if case not in ('empty','complete'):assert m.ops.index(0xd1)<m.ops.index(0xe0) and m.index==1
        if case=='empty':assert m.index==0 and m.get(m.rt,'nes_native_runtime165','prefetch_left')==7
    if positive:assert m.retired==m.sent and bytes(m.u.mem_read(ack,12))==m.last
    return dict(case=case,passed=True,accepted=bool(ok),ops=m.ops,input_blocks=m.index,remaining=m.get(m.rt,'nes_native_runtime165','prefetch_left'),final_identity_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cases=('normal','pending','empty','complete','send_failure','STOP_before','STOP_after_SEAL','STOP_after_READ','bad_CRC','bad_retire','failed_IO','bad_E0_CRC','wrong_identity','future_retire','fault','bad_magic','never_ACK')
    rows=[]
    for c in cases:rows.append(run(a.arm,c));print(c,'PASS',flush=True)
    import check_nes_receive682 as prior
    from nes_raw506 import once
    s=inspect.getsource(prior.burst)
    s=once(s,"ok=m.call('wait634',[m.rt,m.check|1,2,0])","m.put(m.rt,'nes_native_runtime165','prefetch_left',0,1);ok=m.call('wait634',[m.rt,m.check|1,3,0])")
    ns=dict(vars(prior));exec(s,ns)
    for c in ('cap7','empty_after3','STOP_after3','CRC_third','cache_CRC','cache_token'):
        rows.append(dict(ns['burst'](a.arm,c),reason=3));print('reason3',c,'PASS',flush=True)
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope='Linked ARM barrier and receiver, independent fake SPI endpoint; actual CRC/POP/final identity. Not hardware time.'),indent=2)+'\n')
