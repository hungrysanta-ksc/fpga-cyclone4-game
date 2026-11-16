"""Replay a reachable four-credit history with the counters recorded on MMC811/812."""
import argparse
import json
import struct
from pathlib import Path

from check_nes_game478 import crc, sha
from check_nes_supply485_arm import ARM


def exercise(src, end, fixed, *, bad_status=False, end_plan=False):
    m = ARM(src, "normal")
    m.setup()
    p, w, s = "nes_plan200", "nes_sink_window184", "nes_native_sink165"
    initial = (end - 6) & 65535
    for name in ("sent", "retired"):
        m.put(m.w, w, name, initial, 2)
    m.put(m.w,w,"wait",0,4)
    m.put(m.s,s,"plan",m.p,4)
    m.put(m.p,p,"bank_history",2,1)
    generation = 258 if end == 2540 else 241
    m.endpoint.generation=generation
    m.put(m.s,s,"generation",generation,2)
    m.put(m.p,p,"generation",generation,2)
    m.put(m.p,p,"sent",3,2)
    m.put(m.p,p,"started",1,1)
    m.put(m.video,"nes_native_video165","hdma_size",21,2)
    m.put(m.video,"nes_native_video165","patch_count",1,1)
    m.u.mem_write(m.video+m.layout["nes_native_video165"]["hdma"], bytes(range(21)))
    heads, polls = [], []

    def exchange(tx, clock):
        if tx[0] == 0xe8:
            descriptor=struct.pack("<BBHHHI",1,0,16,16,generation,2)
            reply=bytes.fromhex("00d704010003")+descriptor+bytes(1)
            return reply+bytes([crc(reply[1:],8,7,0)])
        if tx[0] == 0xe9:
            assert tx[3] == 2 and tx[4] == 0x81 and tx[12] == 0x83 and tx[-1] == 0xa5
            assert tx[-2]==crc(tx[:-2],8,7,0)
            return bytes(len(tx))
        if tx[0] == 0xe1:
            assert int.from_bytes(tx[-2:],"big") == crc(tx[:-2],16,0x1021,0xffff)
            heads.append(tx[1:-2])
            return bytes(len(tx))
        assert tx == bytes([0xe0])+bytes(19) and len(heads) >= 4
        retired = (initial+3) & 65535  # FIFO consumed the tile and two of three map packets
        accepted = (initial+len(heads)) & 65535
        ack = bytes([0, heads[2][0]])+heads[2][2:10]+bytes.fromhex("659a")
        reported = (accepted+int(bad_status and bool(polls))) & 65535
        reply = bytes.fromhex("00f703")+struct.pack(">HH",reported,retired)+ack
        polls.append(reported)
        return reply+bytes([crc(reply[1:],8,7,0)])

    m.endpoint.exchange = exchange
    for i in range(4):
        op,section,n,expanded = (7,0,4,16) if i == 0 else (2,2,64,0)
        payload = struct.pack("<I",1) if not i else bytes(range(n))
        head = struct.pack("<BBHIHHHH",op,section,i,1,generation,max(i-1,0)*64,n,expanded)+payload
        m.u.mem_write(m.q,head)
        assert m.call("nes_window184_enqueue",[m.w,m.q,len(head)]) == 1
        if i == 0:
            m.put(m.p,p,"bulk_until",m.get(m.w,w,"sent",2),2)
            m.put(m.p,p,"bulk_pending",1,1)
            m.put(m.p,p,"bulk_valid",1,1)
            m.u.mem_write(m.p+m.layout[p]["bulk"],struct.pack("<BBHHHI",1,0,16,0,generation,1))
    m.put(m.s,s,"sequence",4,2)
    assert m.call("nes_window532_room",[m.w,m.q]) and m.u.mem_read(m.q,1) == b"\1"
    assert m.call("nes_scroll810",[m.s,m.video,0,0])
    issued = m.get(m.video,"nes_native_video165","scroll_issued")
    assert issued == int(not fixed)
    if end_plan:
        # Runtime enables quiet map service while END flushes the final OBJ.
        # A lone END can be deferred; exercise the actual nonempty batch here.
        assert m.emit(1,0,9)
        m.put(m.p,p,"quiet_map",m.syms["quiet528"]|1,4)
    ok = m.call("nes_plan200_end" if end_plan else "complete485",[m.p])
    result = dict(sent=m.get(m.w,w,"sent",2),retired=m.get(m.w,w,"retired",2),
                  flags=m.get(m.w,w,"status_flags"), window_error=m.get(m.w,w,"error"),
                  plan_error=m.get(m.p,p,"error"), plan_sent=m.get(m.p,p,"sent",2),
                  E0=len(polls), prefix=issued,
                  queued=[[h[0],h[1]] for h in heads])
    assert ok == int(fixed and not bad_status)
    assert m.get(m.p,p,"bulk_pending") == int(not ok or end_plan)
    assert result["window_error"] == result["plan_error"] == (0 if ok else 5)
    assert result["sent"] == ((end-2+int(end_plan and ok)) & 65535 if fixed else end)
    assert result["retired"] == (end-3)&65535
    assert result["plan_sent"] == 3+int(end_plan and ok)
    assert len(polls) == 1+int(fixed) and result["flags"] == 3
    if not fixed:
        assert heads[-2][0:2]==bytes((2,5)) and heads[-1][0:2]==bytes((5,5))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--fixed",action="store_true")
    args=p.parse_args()
    rows={str(n):exercise(args.src,n,args.fixed) for n in (2540,2284,2)}
    for n in (2540,2284):
        rows[f"end_{n}"]=exercise(args.src,n,args.fixed,end_plan=True)
    if args.fixed:
        rows["bad_status"]=exercise(args.src,2540,True,bad_status=True)
    args.output.write_text(json.dumps(dict(firmware=sha(args.src/"obj-nes-100/firmware.stm"),cases=rows),indent=2)+"\n")
