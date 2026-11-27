"""Exercise the release ELF with synthetic bus events, keeping the trace reader and SD ABI real."""
import argparse
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from check_ff3_airship1051 import layouts
from check_ff3_sd1043 import Machine,fat16
from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC
from compare_ff3_movement1052 import decode,summary

def check(src,edition):
    m=Machine(src,fat16())
    video=0x21000000
    m.u.mem_map(video,0x10000)
    rx,v=layouts(src,('nes_native165','nes_native_video165'))
    for group in range(64):
        m.call('nes_native165_reset',video)
        word=(0x2235<<48)|(1<<42)|(1<<36)|(224<<28)|(group<<4)
        m.u.mem_write(video+0x8000,struct.pack('>HHQ',0xe000,1,word))
        assert m.call('nes_native165_packet',video,0,video+0x8000,12)
        dirty=int.from_bytes(m.u.mem_read(video+rx['dirty_chr'],2),'little')
        assert dirty==(1<<(group//8) if edition==1052 else 256+group)
    m.u.mem_write(video,bytes(0x10000))
    regs=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)
    clock=0
    generation=0
    queries=0
    def event(u,pc,size,name):
        nonlocal queries
        val=clock
        if name=='nes_native165_bulk':
            _,tx,dst,length=[u.reg_read(r) for r in regs]
            assert length==16 and u.mem_read(tx,1)==b'\x78'
            queries+=1
            p=bytearray(16)
            p[1]=0xd2
            struct.pack_into('<H',p,2,generation)
            p[4]=0 if generation<=2 else 0x31
            stamps=[((clock>>16)-n)&4095 for n in (6,3,1,0)]
            for i,t in enumerate(stamps):p[5+i]=t&255
            p[9]=(stamps[0]>>8)|((stamps[1]>>8)<<4)
            p[10]=(stamps[2]>>8)|((stamps[3]>>8)<<4)
            p[11]=190;p[15]=0x5a;u.mem_write(dst,bytes(p));val=1
        u.reg_write(regs[0],val);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for name in ('nes_native165_bulk','nes_cost471_now'):
        pc=m.sym[name]&~1
        m.u.hook_add(UC_HOOK_CODE,event,name,pc,pc)
    def display():
        m.u.mem_write(video+v['generation'],struct.pack('<H',generation))
        m.call('e0900',generation,0)
        m.call('nes_budget210_display',generation*5,video)
    m.call('nes_budget210_reset');display();assert queries==0
    m.u.mem_write(m.sym['movement_slot'],b'\x01')
    m.u.mem_write(m.sym['movement_save'],struct.pack('<III',0x4be84aa7,13,0x12345678))
    m.call('nes_budget210_reset')
    for generation in range(1,90):
        clock=generation*4200000
        display()
    with TemporaryDirectory() as tmp:
        file=Path(tmp)/'test.bin'
        file.write_bytes(m.u.mem_read(m.sym['ptrcache'],7200))
        identity,ed,misses,rows=decode(file)
        assert identity==(1,0x4be84aa7,13,0x12345678) and ed==edition and misses==0
        assert rows[0]['gen']==2 and rows[1]['gen']==3 and rows[-1]['gen']==83 and queries==83
        assert abs(summary(rows)['fps']-20)<.02
    return dict(edition=edition,groups=64,queries=queries,rows=len(rows),first_move_gen=3,last_gen=83)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('work',type=Path);a=p.parse_args()
    for ed in (1052,1053):
        dest=a.work/str(ed)
        result=check(dest/'link/src',ed)
        (dest/'movement.json').write_text(json.dumps(result,indent=2))
        print(result)
