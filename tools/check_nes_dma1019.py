"""Issue the section-5 pair on the first free SPI slot after the actual MDMAEN write."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_output970 import packet_path, replay
from nes_tail1013 import ROOT, once
from test_nes_raw506_joint import MASTER


def records(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def measure(temp, phase, fault=None, *, free_bus=False):
    trace = temp / f"nes-tile821-late-jointmirror-p{phase}-1018wire-control"
    out = temp / "nes-dma1019-gated" / f"p{phase}-{fault or ('free' if free_bus else 'normal')}"
    reference = records(trace / "window.csv")

    def find(events, name, value=None, op=None):
        return [r for r in events if r["g"] == "908" and r["event"] == name
                and (value is None or int(r["value"]) == value)
                and (op is None or int(r["op"]) == op)]

    trigger, = find(reference, "ppu_dma", 192)
    clock = int(trigger["clock"])
    shape = len(find(reference, "load")), len(find(reference, "load", op=7))
    commands, ledger = packet_path(trace, 908, expected_shape=shape)
    busy, = [p for p in ledger if p["issue"] <= clock < p["arrive"]]
    # A live E1 cannot be preempted. Its wire index is also the zero-based
    # offset of the first reorderable packet (the stream starts at index 1).
    cut = busy["index"]
    suffix = commands[cut:]
    def is_pair(p):
        return bytes.fromhex(p[3])[:2] == bytes((2, 5)) and len(bytes.fromhex(p[3]))-16 in (201, 240)
    pair = [p for p in suffix if is_pair(p)]
    assert [len(bytes.fromhex(p[3]))-16 for p in pair] == [201, 240]
    assert all(p[0] == 908 for p in suffix)
    first = next(i for i,p in enumerate(commands) if p[0]==908)
    order = commands[:cut]
    for g, op, arrival, wire, bulk, observed, duration in pair + [p for p in suffix if not is_pair(p)]:
        head = bytearray.fromhex(wire)
        head[2:4] = (len(order)-first).to_bytes(2,"little")
        order.append((g, op, arrival, head.hex(), bulk, observed, duration))

    def observe(lua):
        lua = once(lua, "local lastPush527=0", "local map_started=false\nlocal lastPush527=0")
        lua = once(lua, 'sample516("ppu_dma",dmaLength)', '''
  if pending526 and pending526.g==908 and pending526.off==768 and pending526.n==192 and dmaLength==192 then
   assert(not map_started and regs[0x4301]==0x18)
   map_started=true
  end
  sample516("ppu_dma",dmaLength)''')
        return once(lua, "if not inflight then", "if not inflight then\n    if not map_started then break end")

    clocks = replay(temp, trace, out, "map_start", order, 908, fault, observe=observe,
                    schedule_after=cut, reserved_spi=not free_bus)
    if fault:
        return clocks
    events = records(out / "window.csv")
    actual, = find(events, "ppu_dma",192)
    assert actual == trigger
    source, = find(events,"idle524",65536+768)
    assert int(source["clock"]) < clock
    wire = [list(map(int,row.split())) for row in (out/"starts.txt").read_text().splitlines()]
    assert wire[0][0]==cut+1 and busy["arrive"]<=wire[0][1] and wire[0][2]<=wire[1][1]
    assert [w[2]-w[1] for w in wire[:2]]==[p[-1] for p in pair]
    # Use the observed beam, including the horizontal position, for the
    # duration lower bound. At line 253 the deadline is already in the past.
    h_deadline_upper=clock-(int(actual["line"])-247)*1364
    progress=next(int(r["clock"]) for r in records(trace/"progress680.csv")
                  if int(r["clock"])>clock and int(r["retired"])==cut-1)
    def stamp(r):
        return [int(r[k]) for k in ("clock","frame","line")]
    def timeline(ev):
        return dict(seal=stamp(find(ev,"load",op=3)[0]),dma_end=stamp(find(ev,"ppu_last")[-1]),
                    show=stamp(find(ev,"reveal")[0]),ack=stamp(find(ev,"ack",op=3)[0]))
    base, changed = timeline(reference),timeline(events)
    assert changed["ack"]==clocks["ack"]
    return dict(map_offset=768,dma_start=stamp(actual),progress_write=progress,
                inflight_map_return_to_wire=busy["arrive"],section5_wire=wire[:2],
                section5_accept=[stamp(r) for r in find(events,"load") if int(r["index"]) in (cut+1,cut+2)],
                min_clocks_past_line246_after_pair=clock+sum(p[-1] for p in pair)-h_deadline_upper,
                base=base,changed=changed,
                advance_ms={k:round((base[k][0]-changed[k][0])*1000/MASTER,4) for k in base})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("phase",type=int,choices=(1,2))
    parser.add_argument("--fault",choices=("bad_seal","stop_decode"))
    parser.add_argument("--free-bus",action="store_true",help="Remove other SPI bookings after the in-flight map")
    args=parser.parse_args()
    result=measure(args.temp,args.phase,args.fault,free_bus=args.free_bus)
    dest=ROOT.parent/"probes/nes-dma1019"/f"p{args.phase}-{args.fault or ('free' if args.free_bus else 'normal')}"/"timing1019.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
