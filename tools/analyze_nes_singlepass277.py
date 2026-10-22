# SPDX-License-Identifier: MIT
"""Offline payload/port/ownership audit against immutable NES276 evidence.

No generated RTL, new CPU execution, retimed schedule or area estimate.
Harness images and mutation snapshots below are NOT proposed FPGA RAM.
"""
from pathlib import Path
import argparse, binascii, collections, csv, hashlib, json, math, re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent


def u16(p, i):
    return int.from_bytes(p[i:i+2], "little")


def crc(p, seed=65535):
    return binascii.crc_hqx(bytes(p), seed)


class Once:
    """Queue payload reads, in monotonically increasing address order."""
    def __init__(self, packet):
        self.packet, self.at, self.reads = packet, 16, []

    def take(self):
        assert self.at < len(self.packet), "truncated payload"
        value = self.packet[self.at]
        self.reads.append(self.at)
        self.at += 1
        return value

    def rest(self):
        while self.at < len(self.packet):
            yield self.take()

    def finish(self):
        assert self.reads == list(range(16, len(self.packet)))


def expand_once(p):
    """Literal streams immediately; repeat2/4 holds only its pattern."""
    op = p[0]
    source = Once(p)
    if op == 2:
        output = list(source.rest())
    else:
        assert op in (4, 5, 8)
        pattern = bytes(source.rest())
        assert len(pattern) == (4 if op == 8 else 2)
        count = u16(p, 14)
        assert count and count % len(pattern) == 0
        output = [pattern[i % len(pattern)] for i in range(count)]
    source.finish()
    return bytes(output), len(source.reads)


class Completion:
    """Abstract commit guard, not a hardware emulator or CDC proof."""
    def __init__(self, length=4, identity=(1, 2, 3), token=17):
        self.length, self.identity, self.token = length, identity, token
        self.reads = 0
        self.content = False
        self.committed = False
        self.stopped = False
        self.view = 0
        self.sealed = False
        self.retired = False
        self.memory = bytearray(16)

    def live(self):
        assert not self.stopped, "STOP"

    def read(self, at):
        self.live()
        assert at == self.reads and at < self.length, "coverage"
        self.reads += 1

    def ack(self, identity, token, dma_done):
        self.live()
        assert identity == self.identity and token == self.token, "identity/token"
        assert self.reads == self.length and self.content and dma_done, "completion"
        assert not self.committed, "duplicate ACK"
        self.committed = True
        self.memory[0] = 1

    def seal(self, manifest, certificate, drained):
        self.live()
        assert self.committed and manifest and certificate and drained, "SEAL"
        self.sealed = True

    def display(self, i):
        self.live()
        assert self.sealed and i == self.view and i < 12, "display coverage"
        self.view += 1

    def final(self, token, vblank):
        self.live()
        assert self.sealed and self.view == 12 and token == self.token and vblank, "final ACK"
        assert not self.retired, "duplicate final"
        self.retired = True

    def stop(self):
        self.stopped = True
        self.sealed = False


class PortOwner:
    """Fixed clocks; a grant is an acknowledged lease, never a clock mux."""
    def __init__(self):
        self.phase, self.pending, self.epoch = "source", False, 1
        self.memory = bytearray(1024)

    def handoff(self, source_committed, source_empty, query_pending):
        assert self.phase == "source"
        assert source_committed and source_empty and not query_pending and not self.pending
        self.phase = "grant_pending"

    def grant(self, epoch):
        assert self.phase == "grant_pending" and epoch == self.epoch
        self.phase = "output"

    def write(self, port, epoch, address, value):
        assert epoch == self.epoch
        assert (port, self.phase) in (("NES_A", "source"), ("HOST_B", "output"))
        assert 0 <= address < 1024
        if port == "NES_A": assert address >= 512
        self.memory[address] = value

    def release(self, final_ack, drained):
        assert self.phase == "output" and final_ack and drained
        self.phase = "source"; self.epoch += 1

    def stop(self):
        self.phase = "stopped"


def guard_models():
    passed = []

    def ready():
        x = Completion()
        for i in range(4):
            x.read(i)
        x.content = True
        return x

    def sealed():
        x = ready()
        x.ack(x.identity, x.token, True)
        x.seal(True, True, True)
        return x

    def reject(name, action):
        try:
            action()
        except AssertionError:
            passed.append(name)
        else:
            raise AssertionError("accepted negative: " + name)

    reject("read_gap", lambda: Completion().read(1))
    x = Completion(); x.read(0)
    reject("read_duplicate", lambda: x.read(0))
    x = ready()
    reject("read_overrun", lambda: x.read(4))
    for name, ident, token, dma in [
        ("wrong_epoch", (0, 2, 3), 17, True),
        ("wrong_generation", (1, 0, 3), 17, True),
        ("wrong_bank_sequence", (1, 2, 0), 17, True),
        ("stale_token", (1, 2, 3), 16, True),
        ("read_without_DMA_done", (1, 2, 3), 17, False),
    ]:
        reject(name, lambda: ready().ack(ident, token, dma))
    x = Completion(); x.content = True
    reject("ingress_CRC_without_reads", lambda: x.ack(x.identity, x.token, True))
    x = ready(); x.content = False
    reject("unchecked_content", lambda: x.ack(x.identity, x.token, True))
    x = ready(); x.ack(x.identity, x.token, True)
    reject("duplicate_ACK", lambda: x.ack(x.identity, x.token, True))
    for name, fields in [("missing_manifest", (False, True, True)),
                         ("bad_certificate", (True, False, True)),
                         ("not_drained", (True, True, False))]:
        reject(name, lambda: x.seal(*fields))
    reject("display_before_seal", lambda: ready().display(0))
    reject("display_skip", lambda: sealed().display(1))
    reject("final_before_view", lambda: sealed().final(17, True))
    x = sealed()
    for i in range(12): x.display(i)
    reject("stale_final_token", lambda: x.final(16, True))
    reject("final_before_VBlank", lambda: x.final(17, False))
    x.final(17, True)
    reject("duplicate_final", lambda: x.final(17, True))
    # STOP before/after source data, payload, CRC, commit, SEAL and view.
    for cut in range(9):
        x = Completion()
        if cut >= 1: x.read(0)
        if cut >= 2:
            for i in range(1, 4): x.read(i)
        if cut >= 3: x.content = True
        if cut >= 4: x.ack(x.identity, x.token, True)
        if cut >= 5: x.seal(True, True, True)
        if cut >= 6: x.display(0)
        if cut >= 7:
            for i in range(1, 12): x.display(i)
        if cut >= 8: x.final(17, True)
        x.stop()
        before = bytes(x.memory)
        for action in [lambda: x.read(x.reads),
                       lambda: x.ack(x.identity, x.token, True),
                       lambda: x.seal(True, True, True),
                       lambda: x.final(17, True)]:
            reject(f"STOP{cut}_{len(passed)}", action)
        assert bytes(x.memory) == before
    owner = PortOwner()
    reject("host_during_source", lambda: owner.write("HOST_B",1,396,1))
    reject("source_persistent_overlap", lambda: owner.write("NES_A",1,332,1))
    reject("source_uncommitted", lambda: owner.handoff(False,True,False))
    reject("source_transport_not_empty", lambda: owner.handoff(True,False,False))
    reject("query_pending", lambda: owner.handoff(True,True,True))
    owner.pending = True
    reject("deferred_mask_pending", lambda: owner.handoff(True,True,False))
    owner.pending = False
    owner.handoff(True,True,False)
    reject("host_before_grant", lambda: owner.write("HOST_B",1,396,1))
    reject("stale_grant", lambda: owner.grant(0))
    owner.grant(1)
    reject("source_during_output", lambda: owner.write("NES_A",1,512,1))
    reject("old_epoch_write", lambda: owner.write("HOST_B",0,396,1))
    reject("release_without_finalACK", lambda: owner.release(False,True))
    reject("release_pending_write", lambda: owner.release(True,False))
    owner.write("HOST_B",1,396,1)
    owner.release(True,True)
    reject("late_output_after_release", lambda: owner.write("HOST_B",1,396,2))
    owner.stop(); before=bytes(owner.memory)
    reject("STOP_source_port", lambda: owner.write("NES_A",2,512,2))
    reject("STOP_output_port", lambda: owner.write("HOST_B",2,396,2))
    assert bytes(owner.memory)==before
    return passed


def source_port_model():
    """Deferred mask write occupies FETCH/BLOCKEND, never another FSTORE.

    Existing source has no use of b_q. A pending 9-bit address +8-bit data
    +valid is charged (18 bits); this model does not synthesize that cost.
    """
    sizes = [66]*32 + [64]*35 + [46]
    assert sum(sizes) == 4398
    writes = 0
    for mode in ("unchanged", "changed", "alternating"):
        old, new = bytearray(512), bytearray(512)
        for block, size in enumerate(sizes):
            diff = mask = 0
            for i in range(size):
                changed = mode == "changed" or mode == "alternating" and i % 2 == 0
                value = (block * 17 + i) & 255
                if changed:
                    old[diff] = new[diff] = value
                    diff += 1
                    mask |= 1 << (i % 8)
                if i % 8 == 7 or i+1 == size:
                    addr = 384 + i//8
                    old[addr] = mask  # simultaneous port B in FSTORE
                    pending = (addr, mask)
                    # Following FETCH/BLOCKEND is scratch-write-free.
                    new[pending[0]] = pending[1]
                    writes += 1
                if i % 8 == 7: mask = 0
            assert old == new
    return dict(vectors=3, blocks=68, bytes_per_vector=4398,
                deferred_mask_writes_per_frame=writes//3,
                proposed_pending_bits=18,
                modeled_extra_cycles=0,
                fallback_stall_cycles=writes//3,
                fallback_ms=(writes//3)/22000,
                RTL_verified=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, default=BASE/"probes/nes-joint276")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    d = a.out.resolve()
    assert not d.exists()
    d.mkdir(parents=True)
    q = a.baseline.resolve()/"test03"
    pins = {}

    def read(p):
        data = p.read_bytes()
        pins[str(p)] = hashlib.sha256(data).hexdigest()
        return data.decode("utf-8-sig")

    def hx(p):
        return bytes.fromhex(read(p))

    prior = json.loads(read(ROOT/"analysis/joint276-verification.json"))
    costs = list(csv.DictReader(read(ROOT/"analysis/joint276-costs.csv").splitlines()))
    logs = list(csv.reader(read(q/"joint-events.csv").splitlines()))
    timing = list(csv.DictReader(read(q/"CPU-timing.csv").splitlines()))
    bus = list(csv.DictReader(read(q/"CPU-bus.csv").splitlines()))
    cpu_packets = [bytes.fromhex(x) for x in read(q/"CPU-packets.hex").splitlines()]
    cpu = {(int(t["serial"])+904, int(t["sequence"])): (p, t)
           for t, p in zip(timing, cpu_packets, strict=True)}
    cpu_bus = collections.defaultdict(list)
    for row in bus: cpu_bus[int(row["case"])].append({k:int(v) for k,v in row.items()})
    min_spacing = 1 << 60
    for case, (p, t) in enumerate(zip(cpu_packets, timing, strict=True), 1):
        reads = [r for r in cpu_bus[case] if not r["write"] and 0x400000 <= r["address"] <= 0x4000ff]
        assert [r["address"]-0x400000 for r in reads] == list(range(len(p)))
        assert bytes(r["value"] for r in reads) == p
        min_spacing = min(min_spacing, min(y["clock"]-x["clock"] for x,y in zip(reads, reads[1:])))
    expected_receipts = hx(q/"expected.hex")
    expected_hashes = hx(q/"hashes.hex")
    valid = [bytearray(166), bytearray(166)]
    hashes = [bytearray(32), bytearray(32)]
    meta = [bytearray(8570), bytearray(8570)]
    counts = collections.Counter()
    rows = []
    for baseline in costs:
        f = int(baseline["frame"])
        tx = json.loads(read(q/f"arm{f}.json"))["transfers"]
        packets = []
        for t in tx:
            wire = bytes.fromhex(t["tx"])
            if wire[0] == 225:
                assert crc(wire) == 0
                packets.append(wire[1:-2])
        scroll, raw = u16(packets[0], 30), packets[0][36]
        bank = (f-905) % 2
        if raw == 0:
            for v in valid: v[148:166] = bytes(18)
        received, maps = bytearray(166), bytearray(256)
        fresh_scroll = bytearray()
        requirement = manifest = b""
        readbytes = hashbytes = repeated = 0
        receipt_updates = 0
        def mark(first, count):
            nonlocal receipt_updates
            for bit in range(first, first+count):
                assert not received[bit//8] & (1 << (bit%8)), "duplicate granule"
                received[bit//8] |= 1 << (bit%8)
                valid[bank][bit//8] |= 1 << (bit%8)
            receipt_updates += (first%8 + count + 7)//8
        for seq, p in enumerate(packets):
            assert u16(p, 2) == seq and len(p) == 16+u16(p, 12) <= 256
            op, section, start = p[0], p[1], u16(p, 10)
            counts["packets"] += 1
            if op in (2,4,5,8):
                data, n = expand_once(p)
                assert cpu[(f,seq)][0] == p
                counts["CPU_trace_commands"] += 1
                readbytes += n
                base = {3:4096,4:4608,5:5152}[section]
                meta[bank][base+start:base+start+len(data)] = data
                counts["expanded_ordinary_bytes"] += len(data)
                repeated += max(0, len(data)-n)
                if section == 3:
                    assert start%16 == 0 and len(data)%16 == 0
                    mark(1152+start//16, len(data)//16)
                if section == 5:
                    end = start+len(data)
                    if start < scroll:
                        assert start == 0 and end >= scroll
                        fresh_scroll.extend(data[:scroll])
                        hashbytes += scroll
                    lo, hi = max(start,1121), min(end,3169)
                    if lo < hi:
                        assert (lo-1121)%16 == (hi-1121)%16 == 0
                        mark(1184+(lo-1121)//16, (hi-lo)//16)
                    if raw and end > 3169:
                        lo = max(start,3169)
                        assert (lo-3169)%16 == 0
                        while lo < end:
                            unit = (lo-3169)//16
                            size = 9 if unit == 15 else 16
                            chunk = data[lo-start:lo-start+size]
                            assert len(chunk) == size
                            hashes[bank][2*unit:2*unit+2] = crc(chunk).to_bytes(2,"little")
                            mark(1312+unit, 1)
                            hashbytes += size
                            lo += size
            else:
                stream = Once(p)
                body = bytes(stream.rest())
                stream.finish()
                readbytes += len(body)
                if op == 7:
                    unit = 32 if section else 16
                    mark((1024 if section else 0)+start//unit,u16(p,14)//unit)
                elif op in (12,14):
                    pos = 5 if op == 14 else 4
                    nrange = body[4] if op == 14 else 1
                    for _ in range(nrange):
                        if op == 14:
                            offset, size = u16(body,pos), body[pos+2];pos += 3
                        else:
                            offset, size = start*2, len(body)-4
                        data = body[pos:pos+size];pos += size
                        assert len(data)==size and offset%2==size%2==0
                        meta[bank][offset:offset+size] = data
                        for bit in range(offset//2,(offset+size)//2):
                            assert not maps[bit//8] & (1 << (bit%8))
                            maps[bit//8] |= 1 << (bit%8)
                        counts["map_ranges"] += 1
                        counts["map_bytes"] += size
                    assert pos == len(body)
                elif op == 15:
                    assert len(body)==190
                    requirement = body[24:]
                elif op == 10:
                    assert start == len(manifest)
                    manifest += body
                elif op == 11:
                    assert body[0]==3 and start==len(manifest)
                    pos=1
                    while pos<len(body):
                        tag=body[pos];pos+=1;n=(tag&127)+1
                        if tag&128: manifest += bytes(n)
                        else:
                            assert pos+n<=len(body)
                            manifest += body[pos:pos+n];pos+=n
                else: assert op in (1,3,13)
        assert len(fresh_scroll)==scroll
        assert bytes(meta[bank])==hx(q/f"meta{f}.hex"), f
        assert bytes(valid[0]+valid[1]+received+maps)==expected_receipts[(f-905)*754:(f-904)*754], f
        assert bytes(hashes[0]+hashes[1])==expected_hashes[(f-905)*64:(f-904)*64], f
        assert len(requirement)==166 and manifest==bytes(maps)
        h2=packets[0][16:]
        digest=crc(fresh_scroll)
        if raw: digest=crc(hashes[bank],digest)
        assert digest==u16(h2,22) and crc(h2[:30])==u16(h2,30)
        parser=[r for r in logs if r[0]=="parser" and int(r[1])==f]
        parser_ms=sum(int(r[3]) for r in parser)/1e9
        ordinary_ms=sum(int(r[3]) for r in parser if int(r[2]) in (2,4,5,7,8))/1e9
        total=float(baseline["diagnostic_serial_ms"])
        gap=total-1000/60
        fixed=total-parser_ms
        # Saved polling is a sensitivity, not predicted events. Do not include
        # ARM instructions before a poll as if they all belonged to that poll.
        poll_cost=9*8/2625+.008
        needed=max(0,math.ceil((fixed-1000/60)/poll_cost))
        rows.append(dict(frame=f,baseline_ms=total,parser_ms=parser_ms,
                         ordinary_parser_ms=ordinary_ms,
                         frozen_schedule_zero_parser_ms=fixed,
                         frozen_schedule_remaining_ms=fixed-1000/60,
                         E2_observed=int(baseline["E2_short"]),
                         E2_removal_sensitivity=needed,
                         payload_once_bytes=readbytes,canonical_CRC_bytes=hashbytes,
                         pattern_expansion_bytes=repeated,
                         serial_receipt_extra_host_cycles=2*receipt_updates,
                         serial_receipt_extra_ms=2*receipt_updates*11.904/1e6))
        counts["payload_once_bytes"] += readbytes
        counts["canonical_CRC_bytes"] += hashbytes
    # Concrete source topology, not an assumption of a spare RAM port.
    core=read(q/"nes_core257.sv");wrapper=read(q/"nes_joint257.sv")
    for text in ["a_we=changed", "b_we=row_i[2:0]==7||row_i+1==row_size",
                 "if(row_i+1==row_size)state<=BLOCKEND;else begin row_i<=row_i+1'b1;state<=FETCH;end"]:
        assert text in core
    assert len(re.findall(r"\bb_q\b", core))==1  # declaration only
    assert "always @(posedge clk)begin aq" in wrapper and "always @(posedge clk)begin bq" in wrapper
    for name in ("nes_mux260.sv","nes_queue260.sv","nes_bulk_aperture188.sv",
                 "nes_transport257.sv","nes_native_mailbox206.sv","joint266_tb.sv","CPU-capture.lua"):
        read(q/name)
    # Extract own costs of the two removable output byte/range/view mailboxes.
    # Never add an inclusive parent to its children.
    report=read(a.baseline/"board01/output_files/board.map.rpt")
    mailbox={}
    for line in report.splitlines():
        if "nes_output260:flow|nes_native_mailbox206:" in line and "; work " in line:
            fields=[s.strip() for s in line.split(";")]
            name=fields[1].strip("|").split(":")[-1]
            mailbox[name]={"comb":int(re.search(r"\((\d+)\)",fields[2])[1]),
                           "FF":int(re.search(r"\((\d+)\)",fields[3])[1])}
    assert set(mailbox)=={"admission","consumed","final_ack","receipt"}
    removed_mailbox_comb=sum(mailbox[n]["comb"] for n in ("consumed","receipt"))
    assert removed_mailbox_comb==34
    cases=guard_models()
    worst=max(rows[2:],key=lambda x:x["baseline_ms"])
    window=[]
    for item in prior["restricted_ROM"]:
        f=item["frame"]
        ev=list(csv.reader(read(a.baseline/"window01"/"joint-events.csv").splitlines()))
        pm=sum(int(r[3]) for r in ev if r[0]=="parser" and int(r[1])==f)/1e9
        window.append(dict(frame=f,baseline_ms=item["diagnostic_serial_ms"],
                           parser_ms=pm,frozen_schedule_zero_parser_ms=item["diagnostic_serial_ms"]-pm))
    result=dict(passed=True,stage="NES277",scope="offline original-payload and ownership/port review",
                counts=dict(counts),frames=71,CPU_trace_replayed_offline=544,
                min_observed_packet_read_master_clocks=min_spacing,
                min_observed_packet_read_host_cycles=min_spacing/21.477272727/(11.904/1000),
                single_pass_content_matches_metadata_receipt_CRC=True,
                new_guard_model_cases=len(cases),guard_model_cases=cases,
                source_port_model=source_port_model(),worst=worst,
                frozen_schedule_warm_over=sum(r["frozen_schedule_zero_parser_ms"]>1000/60 for r in rows[2:]),
                restricted_ROM=window,
                area=dict(baseline_comb=18245,device_comb=15408,deficit=2837,
                          core_host_queue_region=5527,retained_other=12718,
                          region_budget=2690,output_mailboxes=mailbox,
                          proposed_region_including_two_mailboxes=5527+removed_mailbox_comb,
                          proposed_region_budget=2690+removed_mailbox_comb,
                          proposed_mailbox_removal_comb=removed_mailbox_comb,
                          proved_reclaim=0,new_MAP=False),
                new_RTL=False,new_CPU=False,new_ARM=False,new_schedule=False,
                guard_models_are_not_RTL=True,full_path_ms=None,P2_selected=False,
                input_hashes=pins,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (d/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (d/"costs.csv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ("passed","counts","new_guard_model_cases","worst","source_port_model")},indent=2))


if __name__ == "__main__":
    main()
