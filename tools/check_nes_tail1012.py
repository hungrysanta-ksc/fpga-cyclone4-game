"""Check the final M4 trace, timer, SRAM D0, loader and guarded return to base."""
import argparse
import struct
import tempfile
from pathlib import Path

from check_nes_display1010_arm import check_header
from check_nes_frame862_arm import TimedProbe, timer_cases
from check_nes_frame900_arm import verify
from check_nes_game478 import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_HOOK_CODE
from check_nes_menu533 import check
from check_nes_sram897 import check_game_path
from nes_order938 import empty_next_offer
from package_nes_trial704 import checked, save
from package_nes_trial855 import loader
from prepare_nes_tail1012 import WORK
from read_nes_tail1012 import HEADER, OFFSET, ROW, SIZE, STRIDE, decode


def trace_test(src,edition=1012):
    m=TimedProbe(src)
    m.call("nes_budget210_reset",[])
    cache=m.data["ptrcache"]
    packet=0x20012000
    current=0xffffe000

    def tick():
        nonlocal current
        current=(current+1024)&0xffffffff
        m.u.mem_write(0xe0001004,struct.pack("<I",current))

    response=bytearray(32)
    def spi(cpu,pc,size,user):
        assert cpu.reg_read(UC_ARM_REG_R3)==32
        assert cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),1)==b"\x78"
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(response))
        m.ret(cpu,1)
    pc=m.syms["nes_native165_bulk"]
    m.u.hook_add(UC_HOOK_CODE,spi,None,begin=pc,end=pc)
    cases=((532,5517,3,2,1,64),(529,5604,1,1,0,16))
    if edition==1025:
        cases=((645,5517,9,3,1,32),(644,5821,4,2,0,48))
    for idx,(bg,scene,tiles,chunks,kind,length) in enumerate(cases):
        gen=100+idx
        m.call("nes_budget210_frame",[scene])
        # The window owner publishes frame_start once per completed frame.
        m.put(m.data["nes_budget210"],"nes_budget210","frame_start",scene,4)
        for seq,(op,section,offset,n) in enumerate(((1,0,0,8),(7,kind,0,4),(2,5,192,240),(3,0,0,24))):
            head=struct.pack("<BBHIHHHH",op,section,seq,9,gen,offset,n,0)
            m.u.mem_write(packet,head);tick();m.call("ready1012",[packet])
            tick();m.call("issue1012",[(65534+seq)&65535])
            tick();m.call("sent1012",[])
            if seq!=1:
                tick();m.call("credit1012",[(65535+seq)&65535])
        tick();m.call("e0900",[gen,idx])
        at=cache+HEADER.size+idx*ROW.size
        desc=struct.pack("<BBHHHI",1,kind,length,0,gen,34)
        obj,dirty=(10,3) if edition==1025 else (18,23)
        row=ROW.pack(scene,gen,bg,100,2,1,obj,dirty,3,idx,bytes(32),desc)
        m.u.mem_write(at,row)
        response[:]=struct.pack("<BBHBB3HI5H",0,0xa1,gen,tiles,chunks,20,99,24,34,10,40,90,91,91)+bytes(4)+bytes((15,0xa5))
        # A stale header must not promote the trace. An accepted header is immutable.
        response[2]^=1
        assert not m.call("header950",[at])
        assert m.u.mem_read(cache+OFFSET+idx*STRIDE+6,2)==bytes(2)
        response[2]^=1
        m.u.mem_write(m.data["pending950"],struct.pack("<I",at))
        m.u.mem_write(m.data["start950"],struct.pack("<I",current))
        m.call("finish_header950",[])
        m.u.mem_write(cache+6,struct.pack("<H",idx+1))
        sample=decode(bytes(m.u.mem_read(cache,SIZE)),edition)["samples"]
        assert len(sample)==idx+1 and sample[-1]["packets"][1]["first_credit_observed"]==sample[-1]["packets"][2]["first_credit_observed"]
        assert [p["payload"] for p in sample[-1]["packets"]]==[8,4,240,24]
    # Scratch cannot promote a frame after a reset.
    m.call("nes_budget210_reset",[])
    assert not decode(bytes(m.u.mem_read(cache,SIZE)),edition)["samples"]
    return dict(workloads=2,grouped_credit=True,counter_wrap=True,reset=True)


def run(game,*,work=WORK,edition=1012):
    src=work/"link/src"
    out=work/"proof"
    out.mkdir(exist_ok=True)
    save(out/"trace.json",trace_test(src,edition))
    assert check_header(src)==11
    verify(edition,src,out,marker_values=(4,8,16,24))
    save(out/"timer.json",timer_cases(src))
    save(out/"menu.json",check(src,str(edition)))
    cases,ram,entry=check_game_path(src,order=empty_next_offer)
    save(out/"sram.json",dict(cases=cases,ram=ram,entry=entry))
    loader(game,src,edition,out)
    recovery=Path(tempfile.mkdtemp(prefix="recovery-",dir=out))/"base"
    checked("check_nes_transfer512_recovery.py",["--arm",src,"--trial",edition,"--fault","none","--out",recovery],out/"base.log")
    (out/"base-result.json").write_bytes((recovery/"result.json").read_bytes())
    print(f"PASS{edition} archive selection, guards, windows, timer, SRAM D0, game loader, STOP and menu")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("game",type=Path)
    run(p.parse_args().game)
