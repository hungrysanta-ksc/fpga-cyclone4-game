# SPDX-License-Identifier: MIT
"""Measure exact target-bank reuse and conservative literal trims on MMC509 packets."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from check_nes_game478 import Machine, sha
from analyze_nes_transfer512 import logical_packets

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (8, 16, 32)


def expand(packet):
    start = int.from_bytes(packet[10:12], "little")
    span = int.from_bytes(packet[14:16], "little")
    body = packet[16:]
    assert packet[1] == 2 and len(body) == int.from_bytes(packet[12:14], "little")
    if packet[0] == 4:
        assert len(body) == 2 and 0 < span <= 192 and span % 64 == 0
        body *= span // 2
    else:
        assert packet[0] == 2 and span == 0
    assert start % 64 == 0 and len(body) in (64, 128, 192) and start+len(body) <= 4096
    return start, body


class History:
    """Only final ACK publishes the staged target. STOP invalidates the two proofs."""
    def __init__(self):
        self.banks = [None, None]
        self.pending = None

    def stage(self, identity, image):
        assert self.pending is None
        self.pending = (identity, image)

    def ack(self, identity):
        if not self.pending or self.pending[0] != identity:
            return False
        self.banks[identity[2]] = self.pending[1]
        self.pending = None
        return True

    def stop(self):
        self.pending = None
        self.banks = [None, None]


def guards():
    h = History()
    key = (1, 905, 0)
    h.stage(key, bytes(4096))
    assert h.banks[0] is None
    assert not h.ack((1, 905, 1)) and not h.ack((2, 905, 0))
    assert h.ack(key) and not h.ack(key)
    h.stage((2, 906, 1), b"x"*4096)
    h.stop()
    assert not h.ack((2, 906, 1)) and h.banks == [None, None]
    h.stage((3, 907, 0), bytes(4096))
    assert h.banks[0] is None and h.ack((3, 907, 0))
    # A word changed and reverted between bank uses remains conservatively dirty.
    first, middle = b"aabbccdd", b"aa11ccdd"
    changes = sum(1 << (i//2) for i in range(0,8,2) if first[i:i+2] != middle[i:i+2])
    assert trim(first, 0, changes, 2) == (2,b"bb")
    return ["cold unknown", "before ACK", "wrong bank/serial", "double ACK",
            "STOP discards tentative and both histories", "late ACK", "cold restart"]


def trim(body, start, word_mask, unit):
    # Examine only the pre-existing packet interval. Preserve the one-packet bound.
    dirty = []
    for offset in range(start, start+len(body), unit):
        words = (1 << (unit//2))-1
        if (word_mask >> (offset//2)) & words:
            dirty.append(offset)
    if not dirty:
        return start, b""
    first, end = dirty[0], dirty[-1]+unit
    return first, body[first-start:end-start]


def wire(data):
    if not data:
        return 0
    return 19 + (2 if len(data)>=4 and data == data[:2]*(len(data)//2) else len(data))


class ARMCompare:
    def __init__(self, arm):
        self.m = Machine(arm, bytes(128))

    def run(self, previous, current):
        # Separate, aligned target SRAM locations. Count the actual linked routines.
        m = self.m
        x, y = 0x20013000, 0x20013100
        m.u.mem_write(y, current)
        compares = examined = 0
        if previous is not None:
            m.u.mem_write(x, previous)
            before = m.instructions
            result = m.call("memcmp", [x, y, 64])
            assert (result == 0) == (previous == current)
            compares = m.instructions-before
            examined = next((i+1 for i,(a,b) in enumerate(zip(previous,current)) if a!=b),64)
        before = m.instructions
        m.call("memcpy",[x,y,64])
        assert bytes(m.u.mem_read(x,64)) == current
        return compares, m.instructions-before, examined



def resident_guards(m):
    """Execute the selected image's resident state owner, independently of the oracle."""
    ptr = m.resident
    layout = m.layout["nes_resident211"]
    def field(name, width=1):
        return int.from_bytes(m.u.mem_read(ptr+layout[name],width),"little")
    def begin(g):
        return m.call("nes_resident211_begin",[ptr,1,1,g,m.writer|1,0])
    def prepare(mask):
        # AAPCS aligns the uint64_t argument to r2:r3.
        return m.call("nes_resident211_prepare",[ptr,0,mask & 0xffffffff,mask>>32])
    def commit(serial,g,bank,displayed):
        return m.call("nes_resident211_commit",[ptr,serial,g,bank,displayed])
    cases=[]
    for mode in ("wrong_serial","wrong_generation","wrong_bank","no_display_ACK","stop"):
        m.call("nes_resident211_reset",[ptr])
        assert begin(905) and prepare(0)
        assert field("map_upload",8)==2**64-1 and field("displayed")==0
        assert commit(1,905,0,1) and field("active")==0 and field("map_stale",8)==0
        assert begin(906) and prepare(1<<42)
        assert field("map_stale",8)==1<<42 and field("active")==0
        if mode=="stop":
            m.call("nes_resident211_abort",[ptr])
        else:
            args={"wrong_serial":(3,906,1,1),"wrong_generation":(2,905,1,1),
                  "wrong_bank":(2,906,0,1),"no_display_ACK":(2,906,1,0)}[mode]
            assert not commit(*args)
        assert field("active")==0 and field("fault")==1 and field("map_stale",16)==2**128-1
        assert not commit(2,906,1,1) and not begin(907)
        cases.append(mode)
    m.call("nes_resident211_reset",[ptr])
    assert begin(907) and prepare(0) and field("map_upload",8)==2**64-1
    return cases+["late_commit_blocked","reset_forces_cold"]


def analyze(a):
    captures = json.loads((a.capture/"captures.json").read_text())
    selected = json.loads((ROOT/"analysis/transfer512-verification.json").read_text())["variants"]["original"]
    assert sha(a.joint/"joint.json")==selected["joint_SHA256"] and sha(a.joint/"events.json")==selected["events_SHA256"]
    assert sha(a.arm/"obj-nes-100/firmware.stm")==selected["firmware_SHA256"]
    joint = json.loads((a.joint/"joint.json").read_text())
    packets = logical_packets(a.joint)
    compare = ARMCompare(a.arm)
    history = History()
    # Word writes accumulate, including temporary changes that the planner reverses.
    all_dirty = (1 << 2048)-1
    stale = [all_dirty, all_dirty]
    totals = {name:collections.Counter() for name in ("cold2", "matched_later10", "later69")}
    frames = []
    assert [f["generation"] for f in captures]==list(range(905,976))
    for f in captures:
        g, bank = f["generation"], f["bank"]
        key = (f["serial"], g, bank)
        image = (a.capture/f"frame{g}/expected-map.bin").read_bytes()
        assert len(image)==4096 and hashlib.sha256(image).hexdigest()==f["image_sha256"]
        encoded = [bytes.fromhex(s) for s in f["map_packets"]]
        if g<=916:
            actual = [p for p,_ in packets if p[1]==2 and int.from_bytes(p[8:10],"little")==g]
            assert [(int.from_bytes(p[10:12],"little"),p[16:]) for p in actual] == [expand(p) for p in encoded]
            begin = next(p for p,_ in packets if p[0]==1 and int.from_bytes(p[8:10],"little")==g)
            assert int.from_bytes(begin[18:20],"little")==bank and joint["frames"][g-905]["ACK_masterclock"]>0
        previous = history.banks[bank]
        word_mask = int(f["touched_words_hex"],16)
        for side in (0,1):
            stale[side] |= word_mask
        written = 0
        trial = {unit:bytearray(previous if previous is not None else b"\xa5"*4096) for unit in WIDTHS}
        raw_dest = bytearray(previous if previous is not None else b"\xa5"*4096)
        values = collections.Counter()
        for p in encoded:
            at, body = expand(p)
            assert body==image[at:at+len(body)] and wire(body)==len(p)+3
            raw_dest[at:at+len(body)] = body
            values.update(packets=1, payload=len(p)-16, wire=len(p)+3)
            for offset in range(at,at+len(body),64):
                bit=1<<(offset//64)
                assert not written & bit
                written |= bit
                old=None if previous is None else previous[offset:offset+64]
                row=image[offset:offset+64]
                compares, copies, examined = compare.run(old,row)
                values.update(rows=1, equal_rows=int(old==row), compare_instructions=compares,
                              copy_instructions=copies, compared_prefix_bytes=examined)
                if old is not None:
                    values["equal_words"]+=sum(old[i:i+2]==row[i:i+2] for i in range(0,64,2))
            for unit in WIDTHS:
                left, data = trim(body,at,stale[bank],unit)
                assert data, "Measured trim would change packet count"
                # Select legacy encoding in a tie: no change of semantics unless bytes decrease.
                if wire(data) >= wire(body):
                    left, data = at, body
                trial[unit][left:left+len(data)] = data
                values[f"trim{unit}_saved_wire"] += wire(body)-wire(data)
                values[f"trim{unit}_shorter_packets"] += int(len(data)<len(body))
        row_mask = sum(1<<i for i in range(64) if stale[bank]>>(i*32)&0xffffffff)
        assert written==row_mask and raw_dest==image and all(dest==image for dest in trial.values())
        if previous is None:
            assert written==(1<<64)-1
        history.stage(key,image)
        assert history.banks[bank]==previous and history.ack(key)
        stale[bank]=0
        totals["cold2" if g<907 else "later69"].update(values)
        if 907<=g<=916:
            totals["matched_later10"].update(values)
        frames.append(dict(generation=g,bank=bank,**values))
    measured = json.loads((a.kernel/"result.json").read_text())
    assert measured["capture_SHA256"]==sha(a.capture/"captures.json")
    assert measured["firmware_SHA256"]==selected["firmware_SHA256"]
    assert measured["source_SHA256"]==sha(ROOT/"tools/nes_map513_mask.c")
    kernels = {}
    for r in measured["kernels"]:
        n = r["unit"]
        assert [f["generation"] for f in r["per_frame"]]==[f["generation"] for f in frames]
        item = {k:v for k,v in r.items() if k!="per_frame"}
        for label,start,end in [("matched_later10",2,12),("later69",2,71)]:
            counts = collections.Counter()
            for f in r["per_frame"][start:end]:
                counts.update(f["instructions"])
            total=sum(counts.values())
            saved=totals[label][f"trim{n}_saved_wire"]/(end-start)
            item[label]=dict(instruction_counts=counts, instructions_per_frame=total/(end-start),
                             CPI2_ms_per_frame=total/(end-start)*2/84000,
                             saved_B_per_frame=saved, wire_ms_per_frame=saved*8/2625)
        kernels[n]=item
    assert set(kernels)==set(WIDTHS)
    return dict(experiment=513,kernels=kernels,source_kernel_sha256=measured["source_SHA256"],firmware_SHA256=selected["firmware_SHA256"],original_joint_SHA256=selected["joint_SHA256"],
                captures_SHA256=sha(a.capture/"captures.json"),guards=guards(),totals=totals,frames=frames,
                full_history_bytes=2*4096,known_rows_bitmap_bytes=16,observed_ARM_gap_B=selected["ARM_observed_stack_gap_B"],
                linked_MMC509_resident_guards=resident_guards(compare.m),
                supplemental_mask_bytes={str(n):3*(4096//n//8) for n in WIDTHS},
                scope="First 12 map ranges/bytes and bank match original512 joint execution. All 71 use MMC509's linked receiver, planner and serializer with modeled final ACK. No new VBlank/IRQ/ROM/board timing.",
                cost_scope="ARM memcmp/memcpy instruction counts for 64-byte aligned rows. Excludes caller/bookkeeping/IRQ; not hardware time. Sub-row trims model bytes and packet count, not a new ABI implementation.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("capture","arm","joint","kernel","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    report=analyze(a)
    with a.out.open("x",encoding="utf8",newline="\n") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print(json.dumps(report["totals"],indent=2))
