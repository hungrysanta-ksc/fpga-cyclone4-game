# SPDX-License-Identifier: MIT
"""Observe planner data and individual ordinary packet preparation without charging extra target work."""
import hashlib
import runpy
import struct
from unittest.mock import patch

import test_nes_tile532 as tile
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP
from unicorn import UC_HOOK_MEM_WRITE


class PreludeRuntime(tile.OutputRuntime):
    def __init__(self,a,link):
        super().__init__(a,link)
        video=self.layout['nes_native_video165']
        ranges={'palette':(video['cgram'],512),'oam':(video['oam'],544),'scroll':(video['hdma'],1121),
                'raw':(0,2048),'mode':(2048,243),'sizes':(2292,6)}
        last={}
        def record(event,**values):
            self.events.append(dict(event=event,generation=self.generation,clock=self.clock,**values))
        def write(u,access,addr,size,value,name):
            if self.generation==954:last[name]=self.clock
        for name,(off,n) in ranges.items():
            self.u.hook_add(UC_HOOK_MEM_WRITE,write,name,begin=self.video+off,end=self.video+off+n-1)

        def frozen(u,pc,size,user):
            if self.generation!=954:return
            def data(key):
                off,n=ranges[key]
                return bytes(u.mem_read(self.video+off,n))
            folder=a.capture/'frame954'
            same={key:data(key)==(folder/f'expected-{file}.bin').read_bytes()
                  for key,file in [('palette','cgram'),('oam','oam')]}
            n=struct.unpack('<H',u.mem_read(self.video+video['hdma_size'],2))[0]
            expected=(folder/'expected-hdma.bin').read_bytes()
            canonical=data('scroll')[:n]+bytes(1121-n)+data('raw')+data('mode')+data('sizes')
            same['hdma']=canonical==expected
            (a.out/'canonical954.bin').write_bytes(canonical)
            record('immutable554',matches_capture=same,last_writes=dict(last),scroll_B=n,
                   patch_count=u.mem_read(self.video+video['patch_count'],1)[0])

        def ready(u,pc,size,user):
            if self.generation!=954:return
            op,sec,at=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
            if sec not in (3,4,5) and op!=3:return
            addr,n,expanded=struct.unpack('<III',u.mem_read(u.reg_read(UC_ARM_REG_SP),12))
            record('ready554',op=op,section=sec,offset=at,n=n,expanded=expanded,
                   payload=bytes(u.mem_read(addr,n)).hex())

        def wire(u,pc,size,user):
            if self.generation!=954:return
            packet=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)))
            if packet[1] in (3,4,5) or packet[0]==3:
                record('wire554',sequence=int.from_bytes(packet[2:4],'little'),digest=hashlib.sha256(packet).hexdigest())
        for sym,fn in [('nes_resident211_prepare',frozen),('packet_wire',ready),('nes_window184_enqueue',wire),
                       ('nes_window184_barrier',wire)]:
            self.u.hook_add(UC_HOOK_CODE,fn,begin=self.syms[sym],end=self.syms[sym])


if __name__=='__main__':
    with patch.object(tile,'OutputRuntime',PreludeRuntime):
        runpy.run_module('test_nes_supply549',run_name='__main__')
