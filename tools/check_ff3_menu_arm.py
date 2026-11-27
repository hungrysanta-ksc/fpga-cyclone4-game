"""Run FF3's linked foreground menu dispatcher through two MCU boots on one FAT16 image."""
import json
import struct
from check_ff3_sd1043 import Machine, fat16
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR

class Player(Machine):
    def __init__(self,src,disk,crc):
        super().__init__(src,disk)
        self.rom(crc)
        self.tick=0
        for name in ('nes_native165_bulk','nes_cf86_check094','delay_us'):
            address=self.sym[name]&~1
            self.u.hook_add(UC_HOOK_CODE,self.device,name,address,address)
    def device(self,u,pc,size,name):
        if name=='nes_native165_bulk':
            tx,rx,length=[u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            data=bytes(u.mem_read(tx,length))
            assert data[0]==0x7a and length in (3,5)
            u.mem_write(rx,(bytes((0,self.request,self.request^255))+bytes(2))[:length])
            if length==5:
                assert data[1:3]==bytes((self.request,self.request^255)) and data[3]^data[4]==255
                self.reply.append(data[3])
        u.reg_write(UC_ARM_REG_R0,1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(self,u,pc,size,name):
        if name=='checkpoint_exchange' and getattr(self,'cold_slot',False):
            op=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R0),2))[1]
            assert op==1, 'cold slot requires reset-to-pause before RESTORE'
            self.cold_slot=False
        return super().hook(u,pc,size,name)
    def command(self,request,result=1):
        self.tick+=5
        self.u.mem_write(self.sym['ticks'],struct.pack('<I',self.tick))
        self.request=request;self.reply=[]
        assert self.call('ff3_play_step',0x20008000,live=True)==1
        assert self.reply==[result],(request,self.reply)

def dispatch(src,crc,checkpoint,export=None):
    disk=fat16()
    battery=bytes((13*i+23)&255 for i in range(8192))
    writer=Player(src,disk,crc)
    writer.state[:]=checkpoint;writer.battery[:]=battery
    writer.pending_frames=2
    writer.command(1);writer.command(2);writer.command(0x11);writer.command(5)
    assert writer.flags==0 and writer.drain_steps==2
    reader=Player(src,disk,crc)
    reader.flags=3
    assert reader.call('nes_restore_boot_battery')==1 and reader.battery==battery
    reader.command(1);reader.command(0x20,2);reader.command(0x21)
    assert reader.u.mem_read(reader.sym['ff3_next_slot'],1)==bytes([2])
    assert reader.flags&3==3
    # Verified loader STOP/CHECK/START resets the checkpoint peripheral and
    # renderer. Boot hold remains asserted until the one-shot slot is applied.
    reader.flags=3
    reader.cold_slot=True
    assert reader.call('nes_restore_boot_battery')==1 and reader.flags==0 and not reader.cold_slot
    assert reader.u.mem_read(reader.sym['ff3_next_slot'],1)==bytes(1)
    assert reader.state==checkpoint and not reader.writes
    if export is not None:export.extend(reader.state)
    return dict(slot=2,words=len(checkpoint)//8,battery=len(battery),drained=writer.drain_steps,
                sectors_written=writer.writes,free_stack_observed_B=min(reader.free,writer.free))

def verify_slots(src, image):
    disk=fat16()
    writer=Player(src,disk,0x7169ada2)
    writer.command(1)
    expected={}
    for slot in range(1,5):
        state=bytearray(image)
        state[-32:]=bytes([slot])*32
        expected[slot]=state
        writer.state[:]=state
        writer.command(0x10+slot-1)
    writer.command(5)
    for slot in (4,1,3,2):
        boot=Player(src,disk,0x7169ada2)
        boot.command(1)
        boot.command(0x20+slot-1)
        boot.flags=3
        boot.cold_slot=True
        assert boot.call('nes_restore_boot_battery')==1
        assert boot.state==expected[slot] and not boot.cold_slot and not boot.writes
    return len(expected)


if __name__=='__main__':
    from pathlib import Path
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for a in ('src','report'):parser.add_argument(a,type=Path)
    args=parser.parse_args()
    image=bytearray((31*i+i//256)&255 for i in range(21264))
    image[:8]=bytes.fromhex('00000000c4140000');image[14]&=252
    result=dispatch(args.src,0x7169ada2,image)
    result['distinct_slots_reloaded']=verify_slots(args.src,image)
    args.report.write_text(json.dumps(result,indent=2))
    print(result)
