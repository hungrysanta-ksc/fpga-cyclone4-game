"""Account for self-contained board transactions, time on the shared bus, and actual reveals separately."""
from collections import defaultdict
import argparse
import json
import math
import struct
from pathlib import Path
from statistics import mean

from analyze_nes_map830 import packets, window
from analyze_nes_pr166_budget import budget
from check_nes_game478 import sha
from test_nes_raw506_joint import PERIOD

CLOCK_MS = 236250000 / 11 / 1000


def stats(values):
    ordered = sorted(values)
    return dict(mean=round(mean(ordered), 3), p95=round(ordered[math.ceil(.95*len(ordered))-1], 3),
                maximum=round(ordered[-1], 3))


def reuse_limits(data, sender, run, work, joint):
    """Gross payload ceilings. All existing CRC, command and credit overhead remains charged."""
    blocks=json.loads((sender/"sender.json").read_bytes())
    commands=defaultdict(list)
    for b in packets(run):
        commands[int.from_bytes(b[8:10],"little")].append(b)
    previous_cells=b""
    bank_maps={}
    ceilings={}
    for i,w in enumerate(work):
        g=w["g"]
        geometry=(data/f"frame{g}.geometry").read_bytes()
        count,=struct.unpack_from("<H",geometry,5728)
        cells=geometry[:count*2]
        start=0
        saved_input=0
        for record in blocks[str(g)]:
            if start==count:
                break
            end=min(count,start+(80 if start==0 else 84))
            if cells[2*start:2*end]==previous_cells[2*start:2*end]:
                saved_input+=len(bytes.fromhex(record["wire"]))-(12 if start==0 else 0)
            start=end
        assert start==count
        previous_cells=cells
        begin=[b for b in commands[g] if b[0]==1]
        assert len(begin)==1
        bank=begin[0][18]
        assert bank in (0,1) and joint["frames"][i]["generation"]==g
        current=(data/f"map-{g}.bin").read_bytes()
        previous=bank_maps.get(bank)
        saved_output=0
        for b in commands[g]:
            if b[:2]!=bytes((2,2)):
                continue
            offset,length=struct.unpack_from("<HH",b,10)
            payload=b[16:]
            assert payload==current[offset:offset+length] and len(payload)==length
            if previous is not None:
                for k in range(0,length-3,4):
                    if payload[k:k+4]==previous[offset+k:offset+k+4]:
                        saved_output+=4
        assert commands[g][-1][0]==3
        bank_maps[bank]=current
        ceilings[g]=(saved_input,saved_output)
    return ceilings


def calibration(temp):
    verified = json.loads((temp / "nes-input848-sender/verified.json").read_bytes())
    cases = {}
    for name, old, new in (("MMC826", "832base", "848compressed"),
                            ("837", "837client-stickypalette", "848reference")):
        cases[name] = []
        for phase in (1, 2):
            old_run, new_run=(temp/f"nes-tile821-demoB-jointmirror-p{phase}-{tag}" for tag in (old,new))
            pair = []
            for tag,run in ((old,old_run),(new,new_run)):
                j = json.loads((run/"joint.json").read_bytes())
                assert j["passed"] and j["commits"] == 6 and j["last_status"] == 1
                pair.append(dict(**budget(phase, tag, run=run), final_ACK=j["frames"][-1]["ACK_masterclock"],
                                 firmware=j["firmware_SHA256"], client=j["client_SHA256"]))
            assert pair[0]["firmware"] == pair[1]["firmware"] and pair[0]["client"] == pair[1]["client"]
            for g in range(905, 911):
                f = f"frame-{g}.rgb"
                assert (old_run/f).read_bytes() == (new_run/f).read_bytes()
            cases[name].append(dict(normalized=pair[0], board_input=pair[1]))
    return dict(input=verified, cases=cases)


def measure(run, work, replies, data, sender):
    joint = json.loads((run/"joint.json").read_bytes())
    assert joint["passed"] and joint["last_status"] == 1 and joint["commits"] == len(work)
    ceilings=reuse_limits(data,sender,run,work,joint)
    events = json.loads((run/"events.json").read_bytes())
    assert joint["parameters"]["driver503_SHA256"] is None
    transfers = []
    for e in events:
        if e["event"]=="SPI":
            transfers.append(e)
        elif e["event"]=="observer":
            # Joint506 charges 8 wire bytes here when no driver503 table is loaded.
            transfers.append(dict(e, start=e["clock"]-8*8*1000*CLOCK_MS/2625000, bytes=8))
    capture_ready={e["generation"]:e["capture_ready"] for e in events if e["event"]=="source_begin"}
    assert all(a["clock"] <= b["start"] + .01 for a,b in zip(transfers, transfers[1:]))
    trace = window(run)
    reveals = [r for r in trace if r["event"] == "reveal"]
    assert [r["g"] for r in reveals] == [w["g"] for w in work]
    frame_rows = []
    previous_rgb=sha(run/f"frame-{work[1]['g']}.rgb")
    busy = defaultdict(float)
    e0_total=e0_identical=0
    same_e0_ms=0.0
    last=None
    for e in transfers:
        if e["opcode"] != "0xe0":
            continue
        key=(e["generation"],e["reply"])
        if reveals[1]["clock"] <= e["start"] and e["clock"] <= reveals[-1]["clock"]:
            e0_total+=1
            if key==last:
                e0_identical+=1
                same_e0_ms+=(e["clock"]-e["start"])/CLOCK_MS
        last=key
    for i in range(2, len(work)):
        w, prev, shown = work[i], reveals[i-1], reveals[i]
        g, start, end = w["g"], prev["clock"], shown["clock"]
        def source_generation(e):
            return e.get("input_generation", e["generation"])
        costs = defaultdict(float)
        amount = defaultdict(int)
        for e in transfers:
            op = e["opcode"]
            generation = source_generation(e) if op.startswith("0xd") else e["generation"]
            if generation == g:
                amount[op] += e["bytes"]
            overlap = min(end,e["clock"]) - max(start,e["start"])
            if overlap > 0:
                costs[op] += overlap / CLOCK_MS
                busy[op] += overlap / CLOCK_MS
        assert amount["0xd1"] == replies[i]["board_D1_B"]
        phase = {r["event"]:r["clock"] for r in trace if r["g"] == g}
        stamps = [r for r in trace if r["g"] == g]
        wait_ticks=0
        for k,r in enumerate(stamps):
            if r["event"]=="wait169":
                resume=stamps[k+1]
                assert resume["event"] in ("wait_return_5781","wait_return_2999","final_upload212_same_blank212")
                wait_ticks+=resume["clock"]-r["clock"]
        f = joint["frames"][i]
        assert f["generation"] == g and f["ACK_masterclock"] >= end
        slots, remainder=divmod(capture_ready[g]-capture_ready[g-1],PERIOD)
        assert remainder==0 and slots>=1
        rgb=sha(run/f"frame-{g}.rgb")
        frame_rows.append(dict(source=w["source_frame"], g=g, vblanks=shown["frame"]-prev["frame"],
            output_RGB_changed=rgb!=previous_rgb,
            modeled_capture_ready=capture_ready[g], unused_capture_slots=int(slots)-1,
            reveal=end, final_ACK=f["ACK_masterclock"], interval_ms=(end-start)/CLOCK_MS,
            D1_B=amount["0xd1"], E1_B=amount["0xe1"], control_B=sum(amount.values())-amount["0xd1"]-amount["0xe1"],
            equal_map_input_payload_B=ceilings[g][0], equal_map_output_4B_payload_B=ceilings[g][1],
            SPI_ms=sum(costs.values()), validate_to_upload_ms=(phase["upload165_entry"]-phase["validate181"])/CLOCK_MS,
            wait169_to_resume_ms=wait_ticks/CLOCK_MS,
            PPU_DMA_started_B=sum(r["value"] for r in stamps if r["event"]=="ppu_dma"),
            receiver_instructions=replies[i]["receive_instructions"], planner_instructions=replies[i]["planner_instructions"]))
        previous_rgb=rgb
    elapsed=sum(r["interval_ms"] for r in frame_rows)
    target=len(frame_rows)*1000/60
    total=lambda k:sum(r[k] for r in frame_rows)
    d1_e1=total("D1_B")+total("E1_B")
    ceilings_B={"baseline":d1_e1,"input_only":d1_e1-total("equal_map_input_payload_B"),
                "output_only":d1_e1-total("equal_map_output_4B_payload_B"),
                "both":d1_e1-total("equal_map_input_payload_B")-total("equal_map_output_4B_payload_B")}
    return dict(measured=len(frame_rows), elapsed_ms=round(elapsed,3), target_ms=round(target,3),
        E0_whole_calls=e0_total, E0_same_generation_and_reply=e0_identical,
        identical_E0_occupied_ms=round(same_e0_ms,3),
        optimistic_D1_E1_B_without_reuse_commands_or_validation=ceilings_B,
        deadline_debt_ms=round(elapsed-target,3), per_opcode_occupied_ms={k:round(v,3) for k,v in sorted(busy.items())},
        unused_capture_slots=total("unused_capture_slots"),
        changed_output_RGB=total("output_RGB_changed"),
        total_vblanks=sum(r["vblanks"] for r in frame_rows), final_ACK=frame_rows[-1]["final_ACK"],
        stats={k:stats([r[k] for r in frame_rows]) for k in ("interval_ms","D1_B","E1_B","control_B","SPI_ms",
               "validate_to_upload_ms","wait169_to_resume_ms","PPU_DMA_started_B","receiver_instructions","planner_instructions")},
        frames=frame_rows)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--clips",nargs="+",default=[])
    a=p.parse_args()
    result=dict(calibration=calibration(a.temp), adjacent={})
    if a.clips:
        result["render_off_collector"]=json.loads((a.temp/"nes-blank848/blank.json").read_bytes())
    for clip in a.clips:
        base=a.temp/"nes-work848"
        work=json.loads((base/clip/clip/"work.json").read_bytes())
        replies=json.loads((base/("sender-"+clip)/"verified.json").read_bytes())["frames"]
        assert [(w["source_frame"],w["g"]) for w in work] == [(r["source"],r["generation"]) for r in replies]
        tag="848series02" if clip=="before_split" else "848series"
        runs=[a.temp/f"nes-tile821-{clip}-jointmirror-p{phase}-{tag}" for phase in (1,2)]
        result["adjacent"][clip]=[measure(run,work,replies,base/clip/clip,base/("sender-"+clip)) for run in runs]
        for w in work:
            name=f"frame-{w['g']}.rgb"
            assert sha(runs[0]/name)==sha(runs[1]/name)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
