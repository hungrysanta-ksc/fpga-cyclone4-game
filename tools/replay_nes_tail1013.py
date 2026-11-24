"""Run the MMC1012 ARM and PPU client on the same late-demo source and ROM calendar."""
import argparse
import csv
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch

from compare_nes_latency898 import CLIPS, MirrorLink, gates, joint, main, seed_slots
from nes_blank960 import PACKED
from nes_tail1013 import BASE, ROOT, VARIANTS, WORK
from nes_raw506 import sha
from test_nes_receive649 import admission
from test_nes_banks557 import crc
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR


def run(temp, phase, mode):
    clip = "late"
    corpus = temp/"nes-latency898"
    source = json.loads((corpus/"sender-late/sender.json").read_bytes())
    ref = json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    assert sha(PACKED/"sink165.sfc") == ref["client"]
    tag = "1013c-" + mode
    out = temp/f"nes-tile821-late-jointmirror-p{phase}-{tag}"
    template = temp/f"nes-tile821-obj-jointmirror-p{phase}-978returned-cold-pair/capture.lua"
    firmware = (BASE if mode=="control" else WORK/mode)/"link/src"
    calibration = json.loads((template.parent/"joint.json").read_bytes())["parameters"]["driver_extra_us"]
    workload = []
    original = joint.Runtime.__init__

    class Link(MirrorLink):
        def accept(self, tx, t):
            if tx[0] == 0xeb:
                assert len(tx)==7 and int.from_bytes(tx[1:3],"little")==self.generation
                assert tx[5]==crc(tx[:5],8,7,0) and tx[6]==0xa5
                # This clip uses the recorded cache-hit lookup. No speculative
                # hit or extra grant is credited to the page hint.
                return t
            return super().accept(tx,t)

    def setup(cpu,args,link):
        original(cpu,args,link)
        cpu.driver_extra[0xeb]=calibration["0xeb"]*joint.MASTER/1e6
        seed_slots(cpu,json.loads((corpus/"late-slots.json").read_bytes()))

        def sample(u,*_):
            address = u.reg_read(UC_ARM_REG_R1)
            def read(key,size):
                return int.from_bytes(u.mem_read(address+cpu.layout["nes_native_video165"][key],size),"little")
            workload.append([read("bg_count",2),read("obj_count",2),read("map_dirty",8).bit_count()])

        def tick(u,*_):
            if cpu.generation>=907:
                u.reg_write(UC_ARM_REG_R0,5500+cpu.generation-907)

        def query(u,*_):
            if u.mem_read(u.reg_read(UC_ARM_REG_R1),1)!=b"\x78":
                return
            assert u.reg_read(UC_ARM_REG_R3)==32
            ack=bytes.fromhex(next(e["reply"] for e in reversed(cpu.events) if e.get("opcode")=="0xe0"))
            gen=int.from_bytes(ack[15:17],"little")
            assert ack[7:9]==b"\x01\x03"
            jobs=[j for j in map(json.loads,(out/"producer.jsonl").read_text().splitlines()) if j["generation"]==gen]
            # The observer does not drive scheduling. Return its checked identity
            # and charge the 32-byte wire; measured event clocks come from Mesen.
            h=bytearray(32)
            struct.pack_into("<BHB",h,1,0xa1,gen,sum(j["bytes"]//(16<<j["kind"]) for j in jobs))
            h[5]=len(jobs)
            if jobs:
                struct.pack_into("<I",h,12,jobs[-1]["token"])
            def stamp(t):
                return int(t*84000000/joint.MASTER/32768)
            first=next((e["start"] for e in cpu.events if e.get("generation")==gen and e.get("opcode")=="0xe9"),cpu.clock)
            struct.pack_into("<3H",h,6,stamp(first)%1024,stamp(cpu.clock+8*joint.MASTER/2625000)%1024,
                             stamp(jobs[-1]["producer"] if jobs else first)%1024)
            with (out/"window.csv").open() as log:
                events=list(csv.DictReader(log))
            def latest(g,event,op=None):
                return next(int(r["clock"]) for r in reversed(events) if int(r["g"])==g and r["event"]==event
                            and (op is None or int(r["op"])==op))
            marks=[latest(gen-1,"reveal"),latest(gen,"load",3),latest(gen,"ppu_last"),
                   latest(gen,"reveal"),latest(gen,"ack",3)]
            struct.pack_into("<5H",h,16,*(stamp(t)%65536 for t in marks))
            h[30:]=bytes((15,165))
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(h))
            cpu.clock+=32*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

        for name,fn in (("nes_budget210_display",sample),("nes_budget210_frame",tick),("nes_native165_bulk",query)):
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)

    argv=["replay","","","","","",tag]
    with patch.object(sys,"argv",argv), patch.object(Link,"lookup_file",corpus/"hits/hits.json"), \
         patch.object(joint.Runtime,"offer_input",admission(joint.Runtime.offer_input)), \
         patch.object(joint.Runtime,"__init__",setup), gates(source,True):
        main(corpus/"late-high",clip,"jointmirror",phase,temp,arm=firmware,client=PACKED,
             client_hash=ref["client"],link_class=Link,packet_source=source,driver_extra_us=calibration,
             adapt_template=lambda s:template.read_text())
    assert len(workload)==len(CLIPS[clip])
    (out/"loads898.json").write_text(json.dumps(workload))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("control",*VARIANTS))
    a=p.parse_args()
    run(a.temp,a.phase,a.mode)
