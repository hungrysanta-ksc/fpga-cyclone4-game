"""Fault injection with a valid outer D1 CRC, mirrored against the original receiver."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import check_nes_overlap634_arm as overlap
from check_nes_game478 import Machine
from nes_geometry650 import encode,legacy,sha


def test(a):
    g=(a.data/"frame955.geometry").read_bytes();raw=(a.data/"frame955.raw").read_bytes()
    packets=encode(g,raw,955)[0];ref=legacy(g,raw,955)[0]
    m=Machine(a.arm,bytes(128))
    def put(token,block):
        addr=0x2001b000;m.u.mem_write(addr,bytes(block))
        return m.call("nes_native165_packet",[m.state,token,addr,len(block)])
    def reset():m.call("nes_native165_reset",[m.state])
    # Compare all canonical state (including tile requirement bits and counters)
    # after every one of the seven independently held/returned blocks.
    def states(p):
        reset();out=[]
        for idx,block in enumerate(p[:7]):
            assert put((65533+idx)&65535,block)
            out.append(bytes(m.u.mem_read(m.state,m.layout["nes_native165"]["size"])))
        return out
    assert states(packets)==states(ref)
    negative=[]
    for kind in ("generation","start","count","CRC","reference","literal_high","truncated","trailing","token","previous_block"):
        reset();second=kind in ("token","previous_block")
        if second:assert put(0,packets[0])
        block=bytearray(packets[int(second)])
        off=0 if second else 12
        if kind=="generation":block[off+3]^=1
        if kind=="start":block[off+5]^=1
        if kind=="count":block[off+6]=255
        if kind=="CRC":block[off+8]^=1
        if kind in ("reference","previous_block"):block[off+10]=128
        if kind=="literal_high":assert block[off+10]<128;block[off+12]|=128
        if kind=="truncated":block.pop()
        if kind=="trailing":block+=bytes((0,0,0))
        token=0 if kind=="token" else int(second)
        assert not put(token,block)
        assert not put(int(second),packets[int(second)])
        negative.append(kind)
    with patch.object(overlap,"encode",encode):
        faults=overlap.run(a.arm,a.data,True,True)
    return dict(firmware=sha(a.arm/"obj-nes-100/firmware.stm"),same_full_state_after_each_block=7,
                decoder_faults=negative,input_guards=faults["rows"])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("data","arm","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(test(a),indent=2)+"\n")
