# SPDX-License-Identifier: MIT
"""Observe 951 source fields, raw packing and linked packet preparation on the existing joint timeline."""
import hashlib
import runpy
import struct
from unittest.mock import patch

from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP
from test_nes_raw506_joint import Runtime
from unicorn import UC_HOOK_MEM_WRITE


def observe(init):
    def attach(m,a,link):
        init(m,a,link)
        video=m.layout['nes_native_video165']
        base=m.video
        raw=base+video['patch']
        scratch=base+video['bg_keys']+4096
        writes={}
        packed_started=False
        source_frozen=False
        def written(u,access,addr,n,value,cookie):
            nonlocal packed_started
            if m.generation==951:
                if addr==scratch and source_frozen and not packed_started:
                    log('pack_start627')
                    packed_started=True
                for address in range(addr,addr+n):
                    writes[address]=m.clock
        for start,n in ((raw,2298),(scratch,384)):
            m.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=start,end=start+n-1)
        def log(event,**fields):
            m.events.append(dict(event=event,generation=951,clock=m.clock,**fields))
        def frozen(u,pc,size,cookie):
            nonlocal source_frozen
            if m.generation!=951:return
            n=int.from_bytes(u.mem_read(base+video['hdma_size'],2),'little')
            canonical=bytes(u.mem_read(base+video['hdma'],n))+bytes(1121-n)+bytes(u.mem_read(raw,2291))+bytes(u.mem_read(raw+2292,6))
            assert canonical==(a.capture/'frame951/expected-hdma.bin').read_bytes()
            count=u.mem_read(base+video['patch_count'],1)[0]
            assert count==2
            source_frozen=True
            fields=[raw+t*64+p*16+r*2+b for p in range(3) for r in range(count) for t in range(32) for b in range(2)]
            fields.extend(range(raw+2048,raw+2291))
            fields.extend(range(raw+2292,raw+2298))
            # Field addresses read from the committed planner, indexed by wire offset-1121.
            log('frozen627',writes=[writes.get(v) for v in fields],data=bytes(u.mem_read(v,1)[0] for v in fields).hex())
        def ready(u,pc,size,cookie):
            if m.generation!=951:return
            sec,off=(u.reg_read(k) for k in (UC_ARM_REG_R2,UC_ARM_REG_R3))
            if sec!=5 and u.reg_read(UC_ARM_REG_R1)!=3:return
            ptr,n,expanded=struct.unpack('<III',u.mem_read(u.reg_read(UC_ARM_REG_SP),12))
            log('payload627',section=sec,offset=off,n=n,expanded=expanded,
                pack_last=max((writes.get(v,0) for v in range(scratch,scratch+384)),default=0))
        def span(u,pc,size,cookie):
            if m.generation==951 and u.reg_read(UC_ARM_REG_R1)==5:
                log('span_start627',offset=u.reg_read(UC_ARM_REG_R2),length=int.from_bytes(u.mem_read(u.reg_read(UC_ARM_REG_SP),4),'little'))
        def header(u,pc,size,cookie):
            if m.generation!=951:return
            h=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
            if h[1]==5 or h[0]==3:
                log('header627',seq=int.from_bytes(h[2:4],'little'),digest=hashlib.sha256(h).hexdigest())
        for symbol,fn in [('nes_resident211_prepare',frozen),('span',span),('packet_wire',ready),
                          ('nes_window184_enqueue',header),('nes_window184_barrier',header)]:
            pc=m.syms[symbol]
            m.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
    return attach


if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_board611',run_name='__main__')
