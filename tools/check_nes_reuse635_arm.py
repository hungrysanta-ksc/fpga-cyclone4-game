# SPDX-License-Identifier: MIT
"""Execute the linked compare, serializer and history update with the actual scene bytes."""
import argparse
import json
import struct
from pathlib import Path
from check_nes_supply485_arm import ARM
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from replay_nes_bank633 import target
from analyze_nes_map628 import packets,sha


class Sender(ARM):
    callback=0x0807ff98

    def hook(self,u,at,size,user):
        if at==self.callback:
            self.head=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
            if hasattr(self,'heads'):self.heads.append(self.head)
            if self.head[0]==3:
                self.before_final=self.get(self.test_sink,'nes_native_sink165','ack635',8)
                ack=bytes((1,3))+self.head[2:10]+bytes((0x65,0x9a))
                if getattr(self,'reject_final',False):ack=bytes((0xe4,))+ack[1:]
                u.mem_write(u.reg_read(UC_ARM_REG_R3),ack)
            u.reg_write(UC_ARM_REG_R0,1)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,at,size,user)


def run(a):
    m=Sender(a.arm,'normal')
    cmds=packets(a.trace)
    sink=0x20015800;kind='nes_native_sink165'
    for key in ('enqueue','exchange'):
        m.put(sink,kind,key,m.callback|1,4)
    layout=m.layout['nes_native_video165']
    costs={}
    for g in (949,950,951):
        pal=target(cmds[g],3);oam=target(cmds[g],4)
        m.u.mem_write(m.video+layout['cgram'],bytes(pal))
        m.u.mem_write(m.video+layout['oam'],bytes(oam))
        serial=int.from_bytes(cmds[g][0][0][4:8],'little')
        bank=(serial-1)&1
        m.put(sink,kind,'serial',serial,4);m.put(sink,kind,'generation',g,2)
        before=m.instructions
        same=m.call('same635',[sink,m.video])
        costs[f'compare{g}']=m.instructions-before
        assert same==(g!=949)
        if g==951:
            m.put(sink,kind,'sequence',13,2)
            before=m.instructions
            assert m.call('send635',[sink,m.video,bank])
            costs['serialize951']=m.instructions-before
            expected=struct.pack('<BBHI4H',9,4,13,serial,951,0,116,0)+oam[:112]+struct.pack('<I',serial-2)
            assert m.head==expected
        before=m.instructions
        m.call('commit635',[sink,m.video,bank,same])
        costs[f'commit{g}']=m.instructions-before
        assert m.get(sink,kind,'ack635',8)>>(32*bank)&0xffffffff==serial
    for key,offset in [('oam',112),('cgram',511)]:
        at=m.video+layout[key]+offset;old=bytes(m.u.mem_read(at,1))
        m.u.mem_write(at,bytes((old[0]^1,)));assert not m.call('same635',[sink,m.video])
        m.u.mem_write(at,old)
    m.u.mem_write(at,bytes((old[0]^1,)))
    m.call('commit635',[sink,m.video,bank,0])
    assert m.get(sink,kind,'ack635',8)>>(32*(1-bank))&0xffffffff==0
    # Normal seal entry runs the real eligibility, fallback, packet ACK check
    # and history commit. Only the transport endpoint is modeled here.
    normal=[]
    for scenario in ('warm','changed','missing','stop_final'):
        m=Sender(a.arm,'normal');m.heads=[];m.test_sink=sink
        for key in ('enqueue','exchange'):m.put(sink,kind,key,m.callback|1,4)
        gen=951;serial=47;bank=0
        for key,value,n in (('serial',serial,4),('generation',gen,2),('displayed',1,1),('state',1,1)):
            m.put(sink,kind,key,value,n)
        m.put(sink,kind,'ack635',45|(46<<32),8)
        pal=bytes(target(cmds[951],3));oam=bytes(target(cmds[951],4))
        m.u.mem_write(sink+m.layout[kind]['palette635'],pal)
        m.u.mem_write(sink+m.layout[kind]['tail635'],oam[112:])
        vkind='nes_native_video165';rkind='nes_resident211'
        m.u.mem_write(m.video+m.layout[vkind]['cgram'],pal)
        m.u.mem_write(m.video+m.layout[vkind]['oam'],oam)
        for key,value,n in (('valid',1,1),('generation',gen,2),('bg_count',1,2),('hdma_size',1,2),('display_mask',0x1e,1)):
            m.put(m.video,vkind,key,value,n)
        for key,value,n in (('prepared',1,1),('open',1,1),('displayed',1,1),('serial',serial,4),('generation',gen,2),('target',bank,1)):
            m.put(m.resident,rkind,key,value,n)
        if scenario=='changed':m.u.mem_write(m.video+m.layout[vkind]['cgram'],bytes((pal[0]^1,)))
        if scenario=='missing':m.put(sink,kind,'ack635',0,4)
        m.reject_final=scenario=='stop_final'
        prior=m.get(sink,kind,'ack635',8)
        passed=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
        assert bool(passed)==(scenario!='stop_final')
        op9=[h for h in m.heads if h[0]==9]
        assert bool(op9)==(scenario in ('warm','stop_final'))
        if op9:assert op9[0][16:]==expected[16:]
        assert m.before_final==prior
        assert m.get(sink,kind,'ack635',4)==(47 if passed else 45)
        if scenario=='changed':assert m.get(sink,kind,'ack635',8)>>32==0
        m.call('nes_sink165_reset',[sink,m.callback|1,0])
        assert m.get(sink,kind,'ack635',8)==0
        normal.append(scenario)
    fw=a.arm/'obj-nes-100/firmware.stm'
    a.out.write_text(json.dumps(dict(head=expected.hex(),instructions=costs,firmware_B=fw.stat().st_size,
                                  firmware=sha(fw),sink_B=m.layout[kind]['size'],normal_seal_cases=normal),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','arm','out'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
