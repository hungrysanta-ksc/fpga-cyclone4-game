"""Replay real ARM input, planner admission and negative terminal responses."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_game478 import (Machine, crc, encode, sha, UC_ARM_REG_LR, UC_ARM_REG_PC,
                               UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)


def packets(generation, count, spread=False, split=False):
    geometry = bytearray(5741)
    geometry[2112:2336] = bytes(range(8)) * 28
    for i in range(count):
        top = 72 if spread and i == count - 1 else 64
        mask = (1 << (i // 8)) | ((1 << (4 + i // 8)) if split else 0)
        word = (top << 13) | ((8 * (i % 32)) << 22) | (mask << 38) | ((i % 8) << 46)
        struct.pack_into("<Q", geometry, 2336 + 8 * i, word)
    for y in range(224):
        epoch = int(split and y >= 68)
        struct.pack_into("<Q", geometry, 3872 + 8*y, (0x1e << 36) | (epoch << 44))
    struct.pack_into("<6H", geometry, 5728, 33, 224, count, 0, 224, 64 if split else 32)
    blocks = encode(geometry, b"", generation)[0]
    assert blocks[0][4:6] == bytes.fromhex("2232")
    blocks[0] = blocks[0][:4] + bytes.fromhex("2233") + blocks[0][6:]
    return blocks


class Receiver(Machine):
    def hook(self, u, at, size, user):
        if at in (0x0807ffa0,0x0807ff90):
            u.reg_write(UC_ARM_REG_R0, 1 if at==0x0807ffa0 else int(not self.stop))
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            return
        if at == self.spi:
            tx = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), u.reg_read(UC_ARM_REG_R3)))
            self.ops.append(tx[0])
            if tx==b"\xe0"+bytes(19):
                reply=b"\xf7"+bytes(17)
                u.mem_write(u.reg_read(UC_ARM_REG_R2),b"\x00"+reply+bytes([crc(reply,8,7,0)]))
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                return
            if tx[0]==0xd1 and getattr(self,"bad_crc",False):
                b=self.packets[self.index]
                checksum=crc(b,16,0x1021,65535)^1
                u.mem_write(u.reg_read(UC_ARM_REG_R2), b"\x00"+b+checksum.to_bytes(2,"big"))
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                return
            if tx[0] == 0xd3:
                assert tx[1:4] == bytes([0]) + self.gen.to_bytes(2, "big")
                assert tx[5:] == bytes([tx[4] ^ 255, crc(tx[:6],8,7,0), 0xa5])
                self.decision = tx[4]
                u.mem_write(u.reg_read(UC_ARM_REG_R2), self.status())
                if not self.decision:
                    self.packets[-1] = struct.pack(">HHQ",0xe002,self.gen,6)
                self.prepared = True
                u.reg_write(UC_ARM_REG_R0, 1)
                u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
                return
        super().hook(u,at,size,user)

    def stage(self, gen, count, spread=False, split=False, runtime=None):
        self.gen, self.prepared, self.index = gen, False, 0
        self.packets, self.ops, self.spi_calls = packets(gen,count,spread,split), [], 0
        self.start_token, self.decision = self.token, None
        while self.index < len(self.packets)-1:
            assert self.poll() == 1
        assert self.state_value() == 2
        if runtime is None:
            assert self.call("nes_native165_prepare", [self.state,1,self.spi|1,0]) == 1
        else:
            assert self.call("nes_runtime165_step", [runtime]) == 1
        return self.decision

    def poll(self):
        return self.call("nes_native165_poll", [self.state,self.spi|1,0])

    def protected(self):
        return tuple(bytes(self.u.mem_read(at,self.layout[key]["size"])) for at,key in
                     ((self.video,"nes_native_video165"),(self.resident,"nes_resident211")))


def check(src, *, limit=None):
    m = Receiver(src, bytes(128))
    m.token = 65520
    accepted = 0
    cases = []
    for idx,(count,spread,split,admit) in enumerate([
        (32,False,False,1),(33,False,False,0),(33,False,False,0),
        (33,True,False,1),(17,False,True,0),(16,False,True,1)]):
        gen = (65533+idx)&65535
        before = m.protected()
        assert m.stage(gen,count,spread,split) == admit
        assert m.poll() == 1 and m.index == len(m.packets)
        assert m.ops[-3:] == [0xd1,0xd2,0xd0] and m.protected() == before
        m.token = (m.start_token+m.index)&65535
        if admit:
            assert m.state_value() == 4
            assert m.call("nes_resident211_begin",[m.resident,1,1,gen,m.writer|1,0]) == 1
            assert m.call("nes_native_video211_plan",[m.state,m.lut,m.video,m.resident]) == 1
            bank = m.u.mem_read(m.resident+m.layout["nes_resident211"]["target"],1)[0]
            accepted += 1
            assert m.call("nes_resident211_commit",[m.resident,accepted,gen,bank,1]) == 1
            m.call("nes_native165_consumed",[m.state])
        assert m.state_value() == 0
        cases.append(dict(generation=gen,count=count,spread=spread,split=split,accepted=bool(admit)))
    guards=[]
    for fault in ("COMMIT","generation","reason","extra","CRC","token"):
        m = Receiver(src,bytes(128))
        assert m.stage(7,33) == 0
        b = m.packets[-1]
        mutations={"COMMIT":struct.pack(">HHQ",0xe003,7,0),"generation":struct.pack(">HHQ",0xe002,6,6),
                   "reason":b[:-1]+b"\x01","extra":b+b,"token":b,"CRC":b}
        m.packets[-1]=mutations[fault]
        if fault=="token":m.start_token+=1
        m.bad_crc = fault=="CRC"
        assert m.poll()==0 and m.state_value()==5, fault
        guards.append(fault)
    m = Receiver(src, bytes(128))
    m.stop = False
    m.ops = []
    m.u.mem_map(0xe0001000,0x1000)
    runtime = 0x20013000
    if limit is None:
        limit = 0 if b"mmc808.txt" in (src/"obj-nes-100/firmware.stm").read_bytes() else 6000
    assert m.call("nes_runtime165_begin",[runtime,m.state,m.video,m.lut,m.spi|1,0x0807ffa1,
                  0x0807ff91,0,limit,m.resident,1,1])==1
    before = m.protected()
    for gen in (10,11,12):
        assert m.stage(gen,33,runtime=runtime)==0 and m.state_value()==6
        m.stop = gen==12
        assert m.call("nes_runtime165_step",[runtime])==int(not m.stop)
        assert set(m.ops)<={0xd0,0xd1,0xd2,0xd3} and not m.plans
        if not m.stop:
            assert m.state_value()==0 and before==m.protected()
        else:
            assert m.state_value()==6 and m.ops[-1]==0xd0
        m.token = (m.start_token+m.index)&65535
    return dict(firmware=sha(src/"obj-nes-100/firmware.stm"),bytes=(src/"obj-nes-100/firmware.stm").stat().st_size,
                cases=cases,guards=guards,runtime_consecutive_skips=2,service_stop_pending=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--limit",type=int,choices=(0,6000),help="Runtime tick limit from the selected edition")
    a=p.parse_args()
    a.output.write_text(json.dumps(check(a.src,limit=a.limit),indent=2)+"\n",newline="\n")
