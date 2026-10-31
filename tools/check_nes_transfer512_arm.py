# SPDX-License-Identifier: MIT
"""Linked Cortex-M4 packet integrity, cancellation, CRC and log-format regressions."""
import argparse
import binascii
import json
import struct
from pathlib import Path
from check_nes_game478 import Machine, crc, sha
from check_nes_hardware510_termination import run as credit_case
from nes_transfer512 import input_packets

def check(a):
    tested = Machine(a.arm, bytes(128))
    base = Machine(a.base, bytes(128))
    address = 0x20013000
    cases = []
    for size in (0,1,2,7,18,63,192,240,255,256,257):
        data = bytes((i*71+size)&255 for i in range(size))
        if size:
            tested.u.mem_write(address,data)
        assert tested.call("nes_crc16_512",[address,size]) == binascii.crc_hqx(data,65535)
        assert tested.call("nes_crc8_512",[address,size]) == crc(data,8,7,0)
    blocks = input_packets((a.data/"frame905.geometry").read_bytes(),(a.data/"frame905.raw").read_bytes(),905)[0]
    def submit(block,token):
        tested.u.mem_write(address,block)
        return tested.call("nes_native165_packet",[tested.state,token,address,len(block)])
    def reset():
        tested.call("nes_native165_reset",[tested.state])
    for name,block,token in [("bad_format",b"\x52"+blocks[0][1:],0),("truncated",blocks[0][:5],0),
                             ("early_commit",blocks[-1],0),("combined_terminal",blocks[-1]+blocks[-1][3:],0)]:
        reset()
        assert submit(block,token)==0 and tested.state_value()!=4
        cases.append(name)
    for name,block,token in [("wrong_generation",blocks[1][:1]+b"\x12\x34"+blocks[1][3:],0),
                             ("wrong_token",blocks[1],1),("partial_record",blocks[1][:-1],0)]:
        reset()
        assert submit(blocks[0],65535)==1
        assert submit(block,token)==0 and tested.state_value()==5
        cases.append(name)
    reset()
    assert submit(blocks[0],65535)==1 and submit(b"\x51"+struct.pack(">HHQ",905,0xe002,0),0)==1
    assert tested.state_value()==0 and submit(blocks[0],1)==1
    cases.append("stop_then_new_begin_after_token_wrap")
    # Format every byte of the successful report. A short destination still fails.
    for size in (1,96,8192):
        for m in (base,tested):
            m.u.mem_write(address,b"\xa5"*size)
        old=base.call("nes_budget210_format",[address,size])
        new=tested.call("nes_budget210_format",[address,size])
        assert old==new
        if old < size:
            assert bytes(base.u.mem_read(address,old+1))==bytes(tested.u.mem_read(address,new+1))
        else:
            assert old==0xffffffff
    for size,expected in [(9,0xffffffff),(10,9),(14,9)]:
        tested.u.mem_write(address+128,b"\x00\x7f\xab\xff")
        assert tested.call("nes_hexline512",[address,size,0,address+128,4])==expected
        if expected==9:
            assert bytes(tested.u.mem_read(address,10))==b"007fabff\n\0"
    credits=[credit_case(a.arm,m) for m in ("normal","guard_deadline","deadline","IO_fault","bad_CRC")]
    return dict(passed=True,input_cases=cases,crc_lengths=11,report_capacities=[1,96,8192],credit_cases=credits,
                firmware_SHA256=sha(a.arm/"obj-nes-100/firmware.stm"))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("base","arm","data","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    report=check(a)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
    print("PASS linked receiver, CRC, reporting and credit/termination")
