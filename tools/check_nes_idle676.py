"""Execute linked bounded input callback and its checked map-tail caller."""
import argparse,json,struct
from pathlib import Path
from check_nes_game478 import Machine,crc,sha,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from check_nes_dma637 import QuietProbe
from elftools.elf.elffile import ELFFile
from test_nes_raw506_joint import member_offset

class Receiver(Machine):
    check=0x0807ffa0;service=0x0807ffb0;ticks=0x0807ffc0
    def __init__(self,src,case):
        self.case=case;self.ops=[];self.checks=0
        super().__init__(src,bytes(128));self.rt=0x20001000
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            for cu in ELFFile(f).get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and d.attributes.get('DW_AT_byte_size'):
                        self.layout['nes_native_runtime165']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
        self.index=self.start_token=self.spi_calls=0;self.prepared=True
        header=(0x2233<<48)|(32<<42)|(2<<36)|(224<<28)
        self.packets=[struct.pack('>HHQ',0xe000,953,header)] if case!='empty' else []
        for name,value,n in [('receiver',self.state,4),('transfer',self.spi|1,4),('ticks',self.ticks|1,4),('service',self.service|1,4),('ctx',self.rt,4),('limit',10000000,4)]:
            self.put(self.rt,'nes_native_runtime165',name,value,n)
        self.put(self.state,'nes_native165','state',2 if case=='complete' else 4,1)
        if case=='complete':self.put(self.rt,'nes_native_runtime165','prefetch_left',3,1)
    def put(self,addr,kind,name,value,n):self.u.mem_write(addr+self.layout[kind][name],value.to_bytes(n,'little'))
    def get(self,addr,kind,name,n=1):return int.from_bytes(self.u.mem_read(addr+self.layout[kind][name],n),'little')
    def hook(self,u,at,size,user):
        if at in (self.check,self.service,self.ticks):
            if at==self.ticks:value=self.instructions
            else:
                self.checks+=1;value=int(not(self.case=='STOP_before' or self.case=='STOP_after_READ' and 0xd1 in self.ops))
            u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==self.spi:
            n=u.reg_read(UC_ARM_REG_R3);op=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))[0];self.ops.append(op)
            rxptr=u.reg_read(UC_ARM_REG_R2)
            super().hook(u,at,size,user)
            if self.case=='bad_CRC' and op==0xd1:
                b=bytes(u.mem_read(rxptr+n-1,1));u.mem_write(rxptr+n-1,bytes([b[0]^1]))
            if self.case=='bad_retire' and op==0xd0 and self.index:
                b=bytearray(u.mem_read(rxptr,8));b[4]^=1;b[7]=crc(b[1:7],8,7,0);u.mem_write(rxptr,bytes(b))
            if self.case=='failed_IO' and op==0xd1:u.reg_write(UC_ARM_REG_R0,0)
            return
        super().hook(u,at,size,user)

def receiver(src,case):
    m=Receiver(src,case);ok=m.call('wait634',[m.rt,m.check|1,4,0]);positive=case in ('normal','empty','complete')
    assert bool(ok)==positive,(case,ok,m.ops)
    assert not any(x in (0xd3,0xe1,0xea) for x in m.ops)
    if case=='normal':assert m.ops==[0xd0,0xd1,0xd2,0xd0] and m.state_value()==1 and m.index==1
    if case=='empty':assert m.ops==[0xd0] and m.state_value()==0
    if case=='complete':assert not m.ops and m.state_value()==2
    if case in ('STOP_before','STOP_after_READ','bad_CRC','failed_IO'):assert 0xd2 not in m.ops
    return dict(case=case,passed=bool(ok),ops=m.ops,receiver_state=m.state_value(),checks=m.checks)

def caller(src,case):
    m=QuietProbe(src,'normal');m.heads=[];m.test_sink=sink=0x20015800;plan,window=0x20016300,0x20016b00
    m.samples=m.drains=0;m.reasons=[];m.stop_at=1 if case=='STOP' else 0;m.bad_drain=1 if case=='bad_credit' else 0;m.reject_final=case=='bad_final'
    m.u.mem_write(m.data_symbols['nes_cost471_available'],bytes(4))
    for k,v,n in [('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',45|(46<<32),8),('obj_next',15 if case=='under_threshold' else 16,2)]:m.put(sink,'nes_native_sink165',k,v,n)
    for k,v in [('window',window),('guard',m.guard|1)]:m.put(plan,'nes_plan200',k,v,4)
    m.put(window,'nes_sink_window184','wait',m.guard|1,4)
    for k,v,n in [('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),('target',1,1),('map_upload',0x7ffff<<32,8)]:m.put(m.resident,'nes_resident211',k,v,n)
    for k,v,n in [('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1)]:m.put(m.video,'nes_native_video165',k,v,n)
    ok=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
    assert bool(ok)==(case in ('normal','under_threshold'))
    assert m.reasons==([] if case in ('under_threshold','bad_credit') else [4]),(case,m.reasons)
    assert any(h[0]==3 for h in m.heads)==(case not in ('STOP','bad_credit'))
    assert m.get(sink,'nes_native_sink165','ack635',8)==(45|((48 if ok else 46)<<32))
    return dict(case=case,committed=bool(ok),idle_calls=m.samples,drains=m.drains)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),receiver=[receiver(a.arm,c) for c in ('normal','empty','complete','bad_CRC','bad_retire','STOP_before','STOP_after_READ','failed_IO')],caller=[caller(a.arm,c) for c in ('normal','under_threshold','bad_credit','STOP','bad_final')])
    a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS676 8 receiver and5 map-tail caller cases; no display ACK fabricated')
