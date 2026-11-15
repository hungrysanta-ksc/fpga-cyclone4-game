# SPDX-License-Identifier: MIT
"""Observe the prepared video at the existing resident-prepare boundary, generation 969."""
from hashlib import sha256
from unicorn import UC_HOOK_MEM_WRITE
from check_nes_game478 import UC_HOOK_CODE


def observe(original):
    def init(cpu, args, link):
        original(cpu,args,link)
        layout=cpu.layout['nes_native_video165']
        fields={'oam':(layout['oam'],112),'scroll':(layout['hdma'],1121),
                'table':(layout['patch']+2048,240),'palette':(layout['cgram'],512)}
        last={k:[None]*n for k,(_,n) in fields.items()}
        def register(name,offset,length):
            base=cpu.video+offset
            def write(u,access,address,size,value,_):
                if cpu.generation!=969:return
                lo=max(0,address-base)
                hi=min(length,address+size-base)
                if hi>lo:last[name][lo:hi]=[cpu.clock]*(hi-lo)
            cpu.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=base,end=base+length-1)
        for name,(offset,length) in fields.items():register(name,offset,length)
        def prepared(u,pc,size,_):
            if cpu.generation!=969 or cpu.irq:return
            hdma=int.from_bytes(u.mem_read(cpu.video+layout['hdma_size'],2),'little')
            assert 0<hdma<=1121
            observed={}
            for name,(off,n) in fields.items():
                count=hdma if name=='scroll' else n
                writes=[v for v in last[name][:count] if v is not None]
                data=bytes(u.mem_read(cpu.video+off,count))
                observed[name]=dict(bytes=count,written=len(writes),last_write=max(writes,default=None),
                                    sha256=sha256(data).hexdigest())
            cpu.events.append(dict(event='prepared777',generation=969,clock=cpu.clock,fields=observed))
        pc=cpu.syms['nes_resident211_prepare']
        cpu.u.hook_add(UC_HOOK_CODE,prepared,begin=pc,end=pc)
    return init
