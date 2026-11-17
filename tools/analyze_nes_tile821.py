"""Join MMC820 captured demo work, producer tokens, SPI replies and PPU DMA clocks."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from test_nes_obj609 import lanes

MASTER = 21_477_272


def ms(clocks):
    return round(clocks * 1000 / MASTER, 4)


def read_json(path):
    return json.loads(path.read_text())


def json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def physical(folder):
    paths = {k: folder / f"nes-{k}-mmc820.txt" for k in ("progress", "game-last", "budget")}
    fields = dict(line.split("=", 1) for line in paths["budget"].read_text().splitlines() if "=" in line)
    cols = fields["columns"].split(",")
    bins = [dict(zip(cols, (int(v, 16) for v in fields[f"b{i:02}"].split(",")), strict=True)) for i in range(12)]
    calls, _, hi, lo, _ = map(int, fields["cost_op_06"].split(","))
    poll_ms = (hi * 2**32 + lo) * 1000 / int(fields["cost_clock_hz"]) / calls
    result = {}
    for a, b in ((2, 3), (4, 5), (1, 8), (8, 11)):
        sums = {k: sum(row[k] for row in bins[a:b]) for k in cols}
        n = sums["frames"]
        result[f"{a*5}-{b*5}"] = dict(start_frames=n,
            e8_per_frame=round(sums["e8"]/20/n, 3), tile_B_per_frame=round(sums["out"]/n, 3),
            resident_hits_per_frame=round(sums["slot_hits"]/n, 3),
            plans_per_frame=round(sums["plans"]/n, 3), output_ms=round(10*sums["seal"]/n, 3),
            estimated_all_e8_ms_per_frame=round(sums["e8"]/20/n*poll_ms, 3))
    for k,d,n in zip(("5-40","40-55"),(35,15),map(int,fields["display_5_40_55"].split(",")),strict=True):
        result[k].update(displayed=n, fps=round(n/d,4))
    result["log_sha256"]={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()}
    return result


def rows(folder, name):
    with (folder / name).open() as file:
        return [{k: (v if k == "event" else int(v)) for k,v in row.items()} for row in csv.DictReader(file)]


def warm_work(data):
    work = read_json(data/"work.json")
    captured = read_json(data/"cache.json")
    folded = read_json(data/"folded.json")
    for r in work[2:]:
        g = r["g"]
        hits = misses = alias = short = cold = fold_misses = 0
        for _,q in read_json(data/f"frame{g}/plans.json"):
            plan=bytes.fromhex(q)
            if plan[6]!=1:
                continue
            for _,addr in lanes(plan):
                tag=addr//16
                line=captured[str(g)].get(str(tag%128))
                other=folded[str(g)].get(str((tag^(tag>>7))&127))
                if not other or other[0]!=tag or str(addr%16) not in other[1]:
                    fold_misses+=1
                if line and line[0]==tag and str(addr%16) in line[1]:
                    hits+=1
                else:
                    misses+=1
                    if not line:
                        cold+=1
                    elif line[0]!=tag:
                        alias+=1
                    else:
                        short+=1
        r.update(obj_lane_hits=hits,obj_lane_misses=misses,alias=alias,missing_lane=short,
                 empty_slot=cold,folded_misses=fold_misses)
    return work[2:]


def replay(folder):
    run=read_json(folder/"joint.json")
    assert run["passed"] and run["firmware_SHA256"]=="47fd371a31eb78e0dd079c86347dbff483303bcb31c7a5dec55bfcc0863e2ea5"
    bus=read_json(folder/"events.json")
    win=rows(folder,"window.csv")
    loads={r["index"]:r for r in win if r["event"]=="load" and r["op"]==7}
    accepts={r["index"]:r for r in win if r["event"]=="ack" and r["op"]==7 and r["value"]==0}
    final={r["g"]:r for r in win if r["event"]=="ack" and r["op"]==3 and r["value"]==1}
    dmas=[(r["g"],r["dst"],r["bytes"],r["clock"]) for r in rows(folder,"seal528.csv")
          if r["event"]=="dma" and r["port"]==24]
    dmas.extend((r["g"],r["dst"],r["n"],r["clock"]) for r in rows(folder,"tile532.csv") if r["event"]=="tile")
    ready={d["token"]:d for d in json_lines(folder/"producer.jsonl")}
    e8={}
    for e in bus:
        if e.get("opcode")=="0xe8":
            rx=bytes.fromhex(e["reply"])
            if rx[6]:
                e8.setdefault(int.from_bytes(rx[14:18],"little"),e)
    tokens=[]
    for index,(_,issued,hx,_) in enumerate(json_lines(folder/"packets.jsonl"),1):
        p=bytes.fromhex(hx)
        g=int.from_bytes(p[8:10],"little")
        if p[0]!=7 or g<907:
            continue
        token=int.from_bytes(p[16:20],"little")
        offset=int.from_bytes(p[10:12],"little")
        n=int.from_bytes(p[14:16],"little")
        kind=p[1]
        bank=(g-905)%2
        dst=((0xc000 if bank else 0) if kind==0 else (0x8000 if bank else 0x4000))+offset
        clocks=[r[3] for r in dmas if r[0]==g and r[1]<=dst and dst+n<=r[1]+r[2] and r[3]>accepts[index]["clock"]]
        assert clocks,(folder,g,token,dst,n)
        times=[ready[token]["producer"],e8[token]["clock"],issued,loads[index]["clock"],accepts[index]["clock"],min(clocks),final[g]["clock"]]
        assert times==sorted(times),(folder,g,token,times)
        tokens.append(dict(g=g,token=token,kind=kind,bytes=n,clocks=[round(t,2) for t in times],
                           adjacent_ms=[ms(b-a) for a,b in zip(times,times[1:])]))
    frames=[]
    for g in range(907,911):
        ack=final[g]
        previous=final[g-1]
        final_token=[t for t in tokens if t["g"]==g][-1]
        plan=next(e["clock"] for e in bus if e["generation"]==g and e.get("opcode")=="0xe9")
        queries=[e for e in bus if e["generation"]==g and e.get("opcode")=="0xe8"]
        waiting=[e for e in queries if plan<=e["start"] and e["clock"]<=final_token["clocks"][0]
                 and bytes.fromhex(e["reply"])[6]==0]
        seal=next(r for r in win if r["g"]==g and r["op"]==3 and r["event"]=="load")
        frames.append(dict(g=g,vblanks=ack["frame"]-previous["frame"],ack_clock=ack["clock"],
            seal_load_clock=seal["clock"],last_bulk_ack_to_seal_ms=ms(seal["clock"]-final_token["clocks"][4]),
            seal_to_last_tile_dma_ms=ms(final_token["clocks"][5]-seal["clock"]),
            e8_count=len(queries),short_e8_count=sum(e["clock"]-e["start"]<1000 for e in queries),
            descriptor_free_e8_before_last_ready=len(waiting),
            descriptor_free_e8_before_last_ready_ms=ms(sum(e["clock"]-e["start"] for e in waiting)),
            e8_ms=ms(sum(e["clock"]-e["start"] for e in queries)),
            first_plan_to_last_ready_ms=ms(final_token["clocks"][0]-plan),last_token=final_token))
    return dict(warm_vblanks=sum(r["vblanks"] for r in frames),warm_ms=ms(final[910]["clock"]-final[906]["clock"]),
                final_clock=final[910]["clock"],frames=frames)


def main():
    p=argparse.ArgumentParser()
    for key in ("probes","traces","downloads","out"):
        p.add_argument("--"+key,required=True,type=Path)
    p.add_argument("--run",default="04")
    a=p.parse_args()
    out=dict(physical=physical(a.downloads),clock_hz=MASTER,
        physical_tile_timestamps=False,arm_cpi=2,spi_hz=2625000,
        model="Real no-input geometry on MMC820 collector, real linked ARM and SNES client. Two cold pictures then four scored pictures, stride four NES frames. ROM grants replay service509 eight-frame contention. No physical generation or absolute capture phase from 5-second logs.",
        clock_order=["producer_ready_model","first_valid_E8_return","E1_queued","65816_load","65816_bulk_ACK","VRAM_DMA_start","display_ACK"],
        clips={})
    boundary=a.traces/"nes-tile821-boundary01/result.log"
    lines=boundary.read_text(errors="replace").splitlines()
    assert any("PASS TILE821 SPLIT END HEAD STOP" in s for s in lines)
    out["bulk206_RTL_ns"]={k:float(next(s for s in lines if k in s).split("=")[-1])
                           for k in ("split_to_ready_ns","to sealed_ns")}
    reference=read_json(a.traces/f"nes-tile821-early-base-p1-{a.run}/joint.json")
    out["identities"]={k:reference[k] for k in ("firmware_SHA256","client_SHA256")}
    for group in ("early","earlyB","late","lateB","demo","demoA","demoB","demoC","demoD"):
        root="data02" if group in ("early","late") else "extra01" if group in ("demo","earlyB","lateB") else "demo-extra01"
        data=a.probes/root/group
        result=dict(work=warm_work(data),runs={})
        modes=["base","poll","supply"] if group in ("early","earlyB","late","demo","demoB") else []
        if group=="demoD":modes.append("base")
        if group in ("early","earlyB","demoB","demoD"):modes.append("fold")
        for mode in modes:
            for phase in (1,2):
                folder=a.traces/f"nes-tile821-{group}-{mode}-p{phase}-{a.run}"
                result["runs"][f"{mode}{phase}"]=replay(folder)
        out["clips"][group]=result
    for k in ("bg_new","obj_new","resident_hits","mapdirty","tile_bytes","obj_lane_hits","obj_lane_misses"):
        early=out["clips"]["early"]["work"]
        late=out["clips"]["late"]["work"]
        assert early[2][k]==late[1][k] and early[0][k]+5*early[2][k]==6*late[0][k],k
    out["matching"]=dict(exact=[676,1332],weighted_early={"668":1,"676":5},weight_sum=6,late=1328,
                         fields=["bg_new","obj_new","resident_hits","mapdirty","tile_bytes","obj_lane_hits","obj_lane_misses"],
                         mandatory_zero_BG_bytes=16)
    a.out.write_text(json.dumps(out,indent=2)+"\n",encoding="utf8")


if __name__=="__main__":
    main()
