# SPDX-License-Identifier: MIT
"""Join real production, shared-bus, receipt and VRAM events to the preceding display ACK."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_first780 import linked
from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms


def measure(folder, reference):
    result=linked(folder,reference)
    w=csv_groups(folder/"window.csv")
    def display(g,mark):
        return one([r for r in w[g] if r["op"]==3],mark)
    origin=display(968,"ack")["clock"]
    def since(clock):
        return ms(clock-origin)
    events=read(folder/"events.json")
    ev=[e for e in events if e.get("generation")==969]
    begin=one(ev,"planner_enter")["clock"]
    finish=one(ev,"prepare_enter")["clock"]
    # Reconstruct the actual stores against the previous displayed map.
    lo,hi=1216,1408
    image=bytearray((folder/"map-968.bin").read_bytes())
    ticks={}
    for e in ev:
        if e["event"]!="map_store757" or not begin<=e["clock"]<=finish:
            continue
        at=e["offset"]
        data=bytes.fromhex(e["new"])
        assert bytes(image[at:at+len(data)])==bytes.fromhex(e["old"])
        image[at:at+len(data)]=data
        for j in range(max(lo,at),min(hi,at+len(data))):
            ticks[j]=e["clock"]
    assert image[lo:hi]==(folder/"map-969.bin").read_bytes()[lo:hi]
    issue=[e for e in ev if e.get("opcode")=="0xe1"]
    loads=[r for r in w[969] if r["event"]=="load"]
    rows=[json.loads(line) for line in (folder/"packets.jsonl").read_text().splitlines()]
    heads=[]
    for s,r in zip(issue,loads,strict=True):
        _,end,h,_=rows[r["index"]-1]
        h=bytes.fromhex(h)
        assert h[8:10]==(969).to_bytes(2,"little") and abs(end-s["clock"])<=1
        ack=one([v for v in w[969] if v["index"]==r["index"]],"ack")["clock"]
        heads.append(dict(op=h[0],section=h[1],offset=int.from_bytes(h[10:12],"little"),
                          wire=since(s["start"]),push=since(end),load=since(r["clock"]),ACK=since(ack)))
    map_head,=[h for h in heads if h["section"]==2 and h["offset"]==lo]
    last_store=max(ticks.values())
    map_start=one([e for e in ev if e.get("offset")==lo],"map_packet_enter")["clock"]
    queued=one([e for e in ev if e.get("offset")==lo],"map_enqueue")["clock"]
    map_wire=next(s for s,r in zip(issue,heads,strict=True) if r==map_head)
    # Count bus occupancy once; CPU may execute simultaneously.
    wire_after_store=Counter()
    for e in ev:
        if e.get("event")=="SPI" and "start" in e:
            wire_after_store[e["opcode"]]+=max(0,min(map_wire["start"],e["clock"])-max(last_store,e["start"]))

    assert last_store<=map_start<=queued<=map_wire["start"]
    tiles=[h for h in heads if h["op"]==7]
    assert [(h["section"],h["offset"]) for h in tiles]==[(0,0),(1,64),(1,128),(1,256)]
    phases=read(folder/"obj-phases.json")["969"]
    trace=read(folder/"joint.json")
    input_head=one(ev,"source_begin")["clock"]
    input_packets=[e for e in events if e.get("opcode")=="0xd1" and input_head<=e["clock"]<=begin]
    target=display(968,"reveal")["frame"]+1
    anchor=next(r for r in csv_groups(folder/"seal528.csv")[969] if r["event"]=="dma" and r["port"]==4)
    actual=display(969,"reveal")["frame"]
    assert any(r["event"]=="ppu_dma" and r["clock"]==anchor["clock"] and r["frame"]==actual for r in w[969])
    # The NTSC short line depends on the frame parity; retain sub-line phase.
    close=anchor["clock"]+(247-anchor["line"])*1364-anchor["h"]+4*(actual%2==0 and anchor["line"]>240)-4*(target%2==0)
    for n in range(target,actual):
        close-=262*1364-4*(n%2==0)
    first_end=close+15*1364
    # A first-blank grant counts only when its checked DMA completes in that blank.
    ends=[r for r in w[969] if r["event"]=="ppu_last" and r["clock"]<one([e for e in w[969] if e["op"]==3],"load")["clock"]]
    assert len(ends)==len(result["transfers"])
    for tr,last in zip(result["transfers"],ends,strict=True):
        assert last["frame"]==target+1+tr[4] and 225<=last["line"]<=261

    offset_by_index={r["index"]:h["offset"] for r,h in zip(loads,heads,strict=True)}
    w_first=[dict(event=r["event"],line=r["line"],index=r["index"],value=r["value"],
                  offset=offset_by_index[r["index"]] if r["event"] in ("load","ack") else None)
             for r in w[969] if r["frame"]==target and r["line"]>=224
             and r["event"] in ("load","ack","idle524","ppu_dma","ppu_last")]
    first_heads=[map_head,tiles[0],next(h for h in heads if h["section"]==2 and h["offset"]==2304),
                 tiles[1],next(h for h in heads if h["section"]==2 and h["offset"]==2496)]
    # An optimistic E1-only bound once map 1216 and both tile plans are
    # available. Per-head receipt latency is kept in the actual measurements.
    selected_wire=sum(h["push"]-h["wire"] for h in first_heads)
    after_ack=Counter()
    for e in events:
        if e.get("event")=="SPI" and "start" in e:
            after_ack[e["opcode"]]+=max(0,min(begin,e["clock"])-max(origin,e["start"]))
    assert sum(after_ack.values())<=begin-origin
    dense=[display(g,"reveal") for g in range(951,958)]
    result.update(first_blank_events=w_first,dense_VBlanks=[b["frame"]-a["frame"] for a,b in zip(dense,dense[1:])],
                  first_five_E1_wire_ms=round(selected_wire,6),
                  map1216_packet=since(map_start),map1216_enqueue=since(queued),
                  input_after_ACK_SPI_ms={op:ms(v) for op,v in after_ack.items() if v},
                  input_after_ACK_other_ms=ms(begin-origin-sum(after_ack.values())),
                  first_head_acks_vs_blank_end_ms=[round(h["ACK"]-since(first_end),6) for h in first_heads],
                  ACK968_to_970=ms(result["final970"]-origin),
                  reveal_line=display(969,"reveal")["line"],ACK968=origin,first246=since(close),map1216_last_store=since(last_store),
                  first_blank_end=since(first_end),map1216_vs_first246=ms(last_store-close),
                  rows_last_store=[since(max(t for i,t in ticks.items() if at<=i<at+64)) for at in range(lo,hi,64)],
                  map1216_wire_after_store_ms={op:ms(v) for op,v in wire_after_store.items() if v},
                  map1216_gap_after_store_ms=ms(map_wire["start"]-last_store-sum(wire_after_store.values())),
                  planner=since(begin),first_D1=since(input_packets[0]["start"]),
                  D3_start=since(one([r for r in ev if r.get("opcode")=="0xd3"],"SPI")["start"]),
                  map_offers=[dict(clock=since(e["clock"]),next=e["map_next"],final=e["final"])
                              for e in ev if e["event"]=="bg684_enter"],
                  D1_before_ACK=sum(e["clock"]<=origin for e in input_packets),D1_total=len(input_packets),
                  first_dma_ends=[since(e["clock"]) for tr,e in zip(result["transfers"],ends,strict=True) if tr[4]==-1],
                  first_map_offer_frozen=since(one(ev,"bg_map_frozen")["clock"]),prepared=since(finish),
                  D3=since(one([r for r in ev if r.get("opcode")=="0xd3"],"SPI")["clock"]),
                  e9=[dict(count=q["count"],seal=since(q["seal"])) for q in phases["banks557"]],
                  tile_heads=tiles,map_heads=[r for r in heads if r["section"]==2],
                  SEAL_head=heads[-1],stack_low=trace["observed_stack_low"],workspace_end=trace["workspace_end"],
                  tile_END=since(phases["end_accepted"]),
                  first_ROM=since(phases["first_obj_rom_request"]),last_ROM=since(phases["last_obj_rom_response"]),
                  ROM_sources=sorted({x[-1] for x in phases["cache611"] if x[0]==1}))
    plan_for_tile={(1,q["slot"]*32):q["accepted_clock"] for q in phases["obj_plans"]}
    plan_for_tile[0,0]=phases["banks557"][0]["seal"]
    result["tile_timing_from_968_ACK_ms"]=[
        dict(section=h["section"],offset=h["offset"],plan=since(plan_for_tile[h["section"],h["offset"]]),
             wire=h["wire"],load=h["load"],retire=h["ACK"]) for h in tiles]
    return result


def analyze(temp, probe):
    output={}
    for p in (1,2):
        ref=temp/f"nes-range778-763-p{p}"
        phase=output[p]={}
        for name in ("763","slots","obj","refill"):
            label={"obj":"obj3","refill":"refill3"}.get(name,name)
            d=ref if name=="763" else temp/f"nes-supply781-{label}-p{p}"
            r=phase[name]=measure(d,ref)
            base=phase["763"]
            r["final970_delta_ms"]=ms(r["final970"]-base["final970"])
            r["ACK968_to_970_delta_ms"]=round(r["ACK968_to_970"]-base["ACK968_to_970"],6)
            r["dense_delta_ms"]=round(r["dense_ms"]-base["dense_ms"],6)
            r["last_OBJ_wire_gain_ms"]=[round(b["wire"]-a["wire"],6)
                                      for a,b in zip(r["tile_heads"][-2:],base["tile_heads"][-2:])]
            r["shortfall_last_OBJ_ms"]=[round(11.178-gain,6) for gain in r["last_OBJ_wire_gain_ms"]]
            r["both_OBJ_11ms"]=all(g>=11.178 for g in r["last_OBJ_wire_gain_ms"])
            r["first_496"]=sum(r["first"])==496
            r["deadline_pass"]=r["first_496"] and r["intervals"][969]==2
            r["schedule_pass"]=(r["deadline_pass"] and r["dense_delta_ms"]<0 and
                                r["final970_delta_ms"]<0 and all(r["intervals"][g]<=base["intervals"][g] for g in (909,960)))
    builds={}
    for i,name in ((1,"slots"),(4,"obj"),(5,"refill")):
        a=probe/f"arm0{i}"
        fw=a/"src/obj-nes-100/firmware.stm"
        guards=read(probe/f"guards{i}.json")
        assert sha(fw)==guards["firmware"]==output[1][name]["firmware"]==output[2][name]["firmware"]
        builds[name]=dict(flash=fw.stat().st_size,excess_B=fw.stat().st_size-212992,elf=sha(fw.parent/"sd2snes.elf"),guards=guards)
    failed=[]
    for mode in ("obj","refill"):
        for p in (1,2):
            evpath=temp/f"nes-supply781-{mode}-p{p}/events.json"
            if not evpath.exists():
                continue
            ev=[e for e in read(evpath) if e.get("generation")==946]
            end=one(ev,"end_enter")["clock"]
            assert not any(e["event"]=="prepare_enter" for e in ev)
            lost=[e for e in ev if e["event"]=="input682_poll_return" and
                  e["clock"]>=end and e["receiver_state"]==0]
            assert lost
            failed.append(dict(mode=mode,phase=p,generation=946,event_sha256=sha(evpath),
                               end_to_early_release_ms=ms(lost[0]["clock"]-end)))
    stops={}
    for name, variant in (("slots","slots"),("refill","refill3")):
        proof=read(temp/f"nes-supply781-stop-{name}/proof.json")
        assert proof["commits"]==64 and proof["blanks_after_STOP"]>=3
        assert proof["retained"]==sha(temp/f"nes-supply781-{variant}-p1/frame-968.rgb")
        stops[name]=proof
    return dict(phases=output,builds=builds,receiver_STOP=stops,early_release_failures=failed, ranges=["map1216/192","BG0/16","map2304/192","OBJ64/32","map2496/64"],
                timing="Linked ARM and 65816 on modeled common SPI/IRQ/ROM schedule; no new board run. "
                       "Head times are ms from the same run's 968 final ACK. Dense averages 951 through 957. "
                       "Fields OBJ_load, OBJ_return, SEAL, upload are relative to second end of line 246.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","probe","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",newline="\n")
