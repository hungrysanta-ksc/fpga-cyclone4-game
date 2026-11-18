"""Interrupt the linked ARM after its final checked map submission, before SEAL."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch
from replay_nes_output822 import MirrorLink, WORK, main
from replay_nes_tile821 import joint
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from analyze_nes_output822 import sha


def check(a):
    fired=[]
    class FaultLink(MirrorLink):
        armed=False
        injected=False
        def accept(self, tx, at):
            now=super().accept(tx,at)
            target_section, target_offset = (5,1121) if a.section5 else (2,3392)
            if (a.generation==909 and tx[0]==0xe1 and (a.section5 or tx[1]==2) and tx[2]==target_section
                    and int.from_bytes(tx[9:11],"little")==909
                    and int.from_bytes(tx[11:13],"little")==target_offset):
                self.armed=True
            return now

        def response(self, tx):
            answer=super().response(tx)
            if self.armed and not self.injected and a.fault in ("crc","identity") and tx[0]==0xe0:
                if a.fault=="identity" and answer[3:5]!=answer[5:7]:
                    return answer
                self.injected=True
                fired.append(a.fault)
                self.packet_log.flush()
                if a.fault=="identity":
                    damaged=bytearray(answer)
                    damaged[9]^=1  # sequence byte of the latest retired head
                    damaged[19]=joint.crc(damaged[1:19],8,7,0)
                    return bytes(damaged)
                return answer[:-1]+bytes([answer[-1]^1])
            return answer

    hook=joint.Runtime.hook
    def stop(machine,u,at,size,user):
        if (machine.live and a.generation==910 and machine.generation==910 and
                at==machine.syms["nes_window184_drain"] and not machine.link.armed):
            caller=u.reg_read(UC_ARM_REG_LR)&~1
            owner=machine.syms["nes_sink212_seal"]
            end=min(address for address in machine.syms.values() if address>owner)
            base=machine.rt+machine.layout["nes_native_runtime165"]["plan"]
            if owner<=caller<end and u.mem_read(base+machine.layout["nes_plan200"]["finished"],1)[0]:
                machine.link.armed=True
        if machine.live and at==machine.syms.get("nes_cf86_check094") and machine.link.armed and a.fault=="stop":
            machine.link.injected=True
            fired.append("stop")
            machine.link.packet_log.flush()
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        return hook(machine,u,at,size,user)

    tag="823"+a.variant+"-"+a.fault+("-fence" if a.generation==910 else "")
    if a.section5:
        assert a.generation==909
        tag+="-section5"
    out=a.temp/f"nes-tile821-demoB-jointmirror-p1-{tag}"
    arm=WORK.parent/"nes-output823"/("link-"+a.variant)/"src"
    with patch.object(sys,"argv",["check","","","","","",tag,str(a.budget)]), patch.object(joint.Runtime,"hook",stop):
        try:
            main(WORK.parent/"nes-tile821/demo-extra01","demoB","jointmirror",1,a.temp,arm=arm,link_class=FaultLink)
        except AssertionError as exc:
            reason=exc.args[0]
            assert reason[:2]==("runtime fault",a.generation),reason
        else:
            raise AssertionError("fault did not stop the candidate")
    detail=json.loads((out/"fault.json").read_text())
    transport=detail["transport"]
    error=bytes.fromhex(transport["bytes"])[transport["layout"]["error"]]
    assert fired==[a.fault],fired
    if a.fault in ("crc","identity"):
        assert error=={"crc":4,"identity":8}[a.fault] and reason[2]==5, (reason,error)
    else:
        assert reason[2]==2,reason
    packets=[bytes.fromhex(json.loads(line)[2]) for line in (out/"packets.jsonl").read_text().splitlines()]
    current=[p for p in packets if int.from_bytes(p[8:10],"little")==a.generation]
    assert any(p[1]==2 and p[10:12]==(3392).to_bytes(2,"little") for p in current)
    if a.section5:
        assert any(p[1]==5 and int.from_bytes(p[10:12],"little")==1121 for p in current)
    seal_submitted=any(p[0]==3 for p in current)
    if a.section5 and a.fault=="identity":
        # A full-queue identity is checked on the first all-retired response.
        # With ordered section 5 this may be the final display ACK itself.
        assert not any(e.get("opcode")=="0xea" and e["generation"]==a.generation
                       for e in json.loads((out/"events.json").read_bytes()))
    else:
        assert not seal_submitted
    if a.generation==910:
        assert current[-1][:2]==bytes([7,1]) and not any(p[1] in (3,4,5) for p in current)
    result=dict(arm=sha(arm/"obj-nes-100/firmware.stm"),case=a.fault,generation=a.generation,
                runtime_error=reason[2],window_error=error,seal_submitted=seal_submitted)
    (out/"rejection.json").write_text(json.dumps(result)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("variant")
    p.add_argument("fault",choices=("stop","crc","identity"))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--generation",choices=(909,910),type=int,default=909)
    p.add_argument("--section5",action="store_true")
    check(p.parse_args())
