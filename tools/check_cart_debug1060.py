"""Replay the two physical DQ4 files and exercise the logger boundary on both links."""
import struct
import zlib
from pathlib import Path
from check_ff3_sd1043 import Machine, fat16, UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from prepare_cart_debug1060 import PRIOR, OUT


class Card(Machine):
    fixture = False
    def hook(self, u, pc, size, name):
        if name == "disk_write" and (self.fixture or u.mem_read(self.sym["checkpoint_window112"],1)==b"\1"):
            drive, buf, sector, count = (u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            assert drive==0 and count>0 and (sector+count)*512<=len(self.disk)
            self.disk[sector*512:(sector+count)*512]=u.mem_read(buf,count*512)
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,pc,size,name)


def run(src, edition):
    disk=fat16()
    m=Card(src,disk)
    u=m.u
    u.mem_map(0x20010000,0x10000)
    u.mem_map(0xe000e000,0x1000)
    u.mem_map(0x40013000,0x1000)
    def result(value):
        def stub(cpu,*_):
            cpu.reg_write(UC_ARM_REG_R0,value);cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
        return stub
    for name,v in (("nes_diag_observe.constprop.0",0),("get_snes_reset",1),("nes_diag_ticks",10),("delay_us",0)):
        if name not in m.sym:continue
        addr=m.sym[name]&~1
        u.hook_add(UC_HOOK_CODE,result(v),None,addr,addr)
    path,fil,buf,n=0x20010000,0x20010200,0x20011000,0x20010100
    def name(s):u.mem_write(path,s.encode()+b"\0");return path
    m.fixture=True
    for directory in ("/sd2snes","/sd2snes/nesstate"):
        assert m.call("f_mkdir",name(directory))==0
    game=next((Path.home()/"Downloads/test").glob("Dragon Quest IV*.nes")).read_bytes()
    crc=zlib.crc32(game)
    assert crc==0x9ac62bb9 and len(game)==0x100010
    supplied=[]
    for slot,size in ((0,8192),(1,22280)):
        filename=f"9ac62bb9-100000-{slot}a.nsv"
        data=(Path.home()/"Downloads"/filename).read_bytes()
        h=struct.unpack_from("<9I",data)
        assert h[:6]==(0x5353454e,1,crc,0x100000,slot,size) and len(data)==36+size
        assert h[7:]==(zlib.crc32(data[36:]),zlib.crc32(data[:32]))
        u.mem_write(buf,data)
        assert m.call("f_open",fil,name("/sd2snes/nesstate/"+filename),10)==0
        assert m.call("f_write",fil,buf,len(data),n)==0 and int.from_bytes(u.mem_read(n,4),"little")==len(data)
        assert m.call("f_close",fil)==0
        supplied.append(data[36:])
    m.fixture=False
    m.call("nes_diag_begin")
    assert m.call("nes_checkpoint_begin112")==1
    for i in range(1,520):
        rc=m.call("nes_checkpoint112",name("VALIDATE"),i*256,0x100000)
        if edition==1059 and i==256:
            assert rc==0 and m.call("nes_return_failed")
            print("1059 reproduced terminal at record 256")
            return
        assert rc==1,(edition,i,rc)
    assert m.call("f_open",fil,name("/sd2snes/nes-progress-debug1060.txt"),1)==0
    for seq in (512,513,518,519,264,511):
        assert m.call("f_lseek",fil,(seq%256)*512)==0
        assert m.call("f_read",fil,buf,512,n)==0 and int.from_bytes(u.mem_read(n,4),"little")==512
        assert f"seq={seq} ".encode() in bytes(u.mem_read(buf,512))
    assert m.call("f_close",fil)==0
    m.rom(crc);u.mem_write(m.sym["nes_board_id"],b"\x84")
    u.mem_write(m.sym["nes_cart_bytes"],struct.pack("<I",0x100000))
    m.state=bytearray(22280)
    for slot,expected in enumerate(supplied):
        u.mem_write(m.sym["ff3_next_slot"],bytes([slot]))
        assert m.call("nes_restore_boot_battery",instructions=180000000)==1 and m.flags==0
        assert (m.state if slot else m.battery)==expected and m.writes==0
    print("1060 bounded ring and physical DQ4 SRAM/quick slot PASS")


if __name__=="__main__":
    run(PRIOR/"vrc/debug/link/src",1059)
    run(OUT/"debug/link/src",1060)
