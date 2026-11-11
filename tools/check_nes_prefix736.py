"""Exercise both section orders and aborts in the linked ARM sender."""
import argparse
import json
from pathlib import Path
from check_nes_dma637 import QuietProbe
from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1
from nes_raw506 import sha


class Receiver(QuietProbe):
    def hook(self,u,at,size,user):
        if at==self.callback:
            header=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),16))
            if (header[1],int.from_bytes(header[10:12],'little'))==self.reject_packet:
                self.rejected=True
                u.reg_write(UC_ARM_REG_R0,0)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                return
        super().hook(u,at,size,user)


def case(src,variant,name):
    m=Receiver(src,'normal')
    sink=m.test_sink=0x20015800
    plan=0x20016300
    m.heads=[]
    m.rejected=False
    m.reject_packet={'prefix_fault':(5,0),'padding_fault':(5,21),'table_fault':(5,1505)}.get(name)
    m.reject_final=name=='final_fault'
    mask={'split':0x033f,'empty':0,'last_row':1<<63}.get(name,0x3f00)
    start={'cursor_end':64,'skip_gap':8}.get(name,0)
    if name=='skip_gap':
        mask|=1
    fields=[
        (sink,'nes_native_sink165',[('serial',5,4),('generation',957,2),('displayed',1,1),('state',1,1),
                                    ('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),
                                    ('ack635',3|(4<<32),8),('map_next',start,1)]),
        (plan,'nes_plan200',[('bank_history',0 if name=='cold' else 2,1)]),
        (m.resident,'nes_resident211',[('prepared',1,1),('open',1,1),('serial',5,4),('generation',957,2),
                                      ('displayed',1,1),('map_upload',mask,8)]),
        (m.video,'nes_native_video165',[('valid',1,1),('generation',957,2),('bg_count',1,2),
                                       ('obj_count',1,2),('display_mask',0x1e,1),('hdma_size',21,2),
                                       ('patch_count',2,1)])]
    for addr,kind,values in fields:
        for key,v,n in values:
            m.put(addr,kind,key,v,n)
    for key in ('dirty','used'):
        m.u.mem_write(m.resident+m.layout['nes_resident211'][key]+143,bytes([0 if name=='no_obj' else 128]))
    if name=='changed':
        m.u.mem_write(m.video+m.layout['nes_native_video165']['cgram'],b'\x19')
    m.u.mem_write(m.video+2292,b'\x15\0'*3)
    ok=m.call('nes_sink212_seal',[sink,m.video,m.resident])
    success=m.reject_packet is None and not m.reject_final
    assert bool(ok)==success and m.rejected==(m.reject_packet is not None),name
    assert m.get(sink,'nes_native_sink165','ack635',4)==(5 if success else 3)
    assert any(h[0]==3 for h in m.heads)==(m.reject_packet is None)
    if not success:
        m.call('nes_sink165_reset',[sink,m.callback|1,0])
        assert m.get(sink,'nes_native_sink165','ack635',8)==0
        return name
    rows=[(h[1],int.from_bytes(h[10:12],'little')) for h in m.heads]
    maps=[i for i,(section,_) in enumerate(rows) if section==2]
    if maps:
        assert maps==list(range(min(maps),max(maps)+1))
        early=name in ('joined','last_row','skip_gap')
        assert (rows.index((5,21))<min(maps))==early
        assert (rows.index((5,1505))<min(maps))==(early and variant=='a')
    else:
        assert name in ('empty','cursor_end')
    return name


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('arm',type=Path)
    p.add_argument('variant',choices=('a','b'))
    p.add_argument('out',type=Path)
    a=p.parse_args()
    cases=[case(a.arm,a.variant,k) for k in ('joined','cold','no_obj','changed','split','empty','last_row',
                                             'skip_gap','cursor_end','prefix_fault','padding_fault','table_fault','final_fault')]
    a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=cases),indent=2)+'\n')
