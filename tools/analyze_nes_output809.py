"""Match physical workloads before comparing fixed-input output schedules."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from analyze_nes_hardware663 import work
from analyze_nes_output768 import PROBES, ROOT, csv_groups, fields, one, read, sha, timeline, waits
from check_nes_game478 import Machine
from test_nes_raw506_joint import MASTER


def close_enough(observed, reference):
    return abs(observed-reference) <= 0.2*reference


def timed_bins(edition, archive, pins):
    with ZipFile(archive) as z:
        name=f"nes-budget-mmc{edition}.txt"
        raw=z.read(name)
        assert hashlib.sha256(raw).hexdigest()==pins[name]
    budget = fields(raw.decode("utf-8-sig"))
    assert budget["tick_ms"] == "10"
    rows = work(budget)[0]
    result={}
    for i in range(1,11):
        row=rows[i]
        n=row["frames"]
        result[5*i]=dict(frames=n,output_ms=row["seal"]*10/n,
                         **{k:row[k]/n for k in ("mapdirty","obj","bg","e0","e8","e1")})
    return result


def match():
    old=timed_bins(805,PROBES/"nes-trial805/hardware805-806.zip",
                   read(ROOT/"analysis/hardware806-results.json")["MMC805"]["hashes"])
    new=timed_bins(807,PROBES/"nes-obj807/hardware807-808.zip",
                   read(ROOT/"analysis/hardware808-results.json")["MMC807"]["hashes"])
    capture=PROBES/"nes-output489/audit01"
    layout=Machine(PROBES/"nes-output489/ARM01/src",bytes(128)).layout["nes_native_video165"]
    matches={}
    for t,row in new.items():
        if not all(close_enough(row[k],old[t][k]) for k in ("mapdirty","obj","bg")):
            continue
        candidates={}
        for g in range(907,971):
            data=(capture/f"frame{g}/video-before.bin").read_bytes()
            def field(k,n):
                return int.from_bytes(data[layout[k]:layout[k]+n],"little")
            capture_row=dict(mapdirty=field("map_dirty",8).bit_count(),
                             obj=field("obj_count",2),bg=field("bg_count",2))
            if all(close_enough(capture_row[k],row[k]) for k in ("mapdirty","obj")):
                candidates[g]=capture_row
        matches[t]=dict(mmc805=old[t],mmc807=row,captures=candidates)
    return matches


def schedule(folder, target):
    joint=read(folder/"joint.json")
    assert joint["passed"] and joint["commits"]==joint["map_WRAM_VRAM_verified"]==66
    cpu=csv_groups(folder/"window.csv")
    with (folder/"seal528.csv").open() as f:
        seal_dma=[r for r in csv.DictReader(f) if r["event"]=="dma"]
    events=read(folder/"events.json")
    packets=[json.loads(line) for line in (folder/"packets.jsonl").read_text().splitlines()]
    rows={}
    for g in target:
        r=timeline(folder,g,cpu,events,packets)
        rows[g]={k:r[k] for k in ("work","output_ms","before_SEAL_ms","non_SPI_before_SEAL_ms",
                                   "wire_before_SEAL_ms","terms_ms","display_interval_VB","final_waits",
                                   "post_SEAL_DMA_bytes","post_SEAL_load_line","reveal_line","final_ACK_line")}
        seal=[v for v in cpu[g] if v["op"]==3]
        rows[g]["wait_lines"]=[v["line"] for v in seal if v["event"]=="wait169"]
        # The fixed section-5 table is the penultimate section-5 packet. Count
        # only transferable payload time; encoding, decoding and issue overhead
        # cannot be inferred from the zero-byte count.
        if g==959:
            table,tail=[v for v in cpu[g] if v["event"]=="load" and v["section"]==5][-2:]
            payload=bytes.fromhex(packets[table["index"]-1][2])[16:]
            assert table["op"]==2 and len(payload)==240 and tail["index"]==table["index"]+1
            zeros=payload.count(0)
            rows[g]["table_wire"]=dict(bytes=len(payload),zeros=zeros,
                                        zero_payload_ms=zeros*8*1000/2625000,
                                        entire_payload_ms=len(payload)*8*1000/2625000)
        objs=[i for i,p in enumerate(r["packets"]) if (p["op"],p["section"])==(7,1)]
        if objs:
            obj=r["packets"][objs[-1]]
            tail=r["packets"][objs[-1]+1:-1]
            rows[g]["after_last_OBJ"]=dict(
                retire_to_SEAL_issue_ms=r["before_SEAL_ms"]-obj["retire_ms"],
                packets=len(tail),wire_bytes=sum(p["bytes"] for p in tail))
    reveals={g:one([r for r in cpu[g] if r["op"]==3],"reveal") for g in range(905,971)}
    intervals={g:reveals[g]["frame"]-reveals[g-1]["frame"] for g in range(906,971)}
    seal951=one([r for r in cpu[951] if r["op"]==3],"load")["clock"]
    rows[951]["after_SEAL_transfers"]=[
        {k:int(r[k]) for k in ("line","bank","port","dst","bytes")}
        for r in seal_dma if int(r["g"])==951 and int(r["clock"])>=seal951]
    assert sum(r["bytes"] for r in rows[951]["after_SEAL_transfers"])==rows[951]["post_SEAL_DMA_bytes"]
    rows[951]["preceding_VBlank"]=[
        {k:r[k] for k in ("event","line","op","section","value")}
        for r in cpu[951] if r["frame"]==reveals[951]["frame"]-1 and r["line"]>=225
        and r["event"] in ("load","ppu_dma")]
    upload_late={}
    for g in range(952,971):
        seal=[r for r in cpu[g] if r["op"]==3]
        requests=[r for r in seal if r["event"]=="wait169"]
        # A single upload wait entered in the visible period misses the preceding
        # blank by at least the completed lines. Exclude the current horizontal
        # position, DMA setup, transfer, display checks and an earlier safe cutoff.
        final=one(seal,"final212")["clock"]
        if len(requests)==1 and requests[0]["clock"]<final and 0<=requests[0]["line"]<225:
            line=requests[0]["line"]
            (_,resume),=waits(seal)
            assert resume<=final
            # Translate the observed post-wait work to the previous blank.
            # Line 246 inclusive is an optimistic limit for the final check.
            to_check=final-resume
            upload_late[g]=dict(line=line,minimum_advance_ms=line*1360*1000/MASTER,
                                post_wait_to_final_check_ms=to_check*1000/MASTER,
                                prior_line246_advance_ms=((262-247+line)*1360+to_check)*1000/MASTER)
    last=joint["frames"][-1]
    assert last["generation"]==970
    last_dma={}
    for g in (957,969):
        seal=[r for r in cpu[g] if r["op"]==3]
        load=one(seal,"load")["clock"]
        pre={}
        for r in cpu[g]:
            if r["event"]=="ppu_dma" and r["clock"]<load:
                vb=r["frame"]-reveals[g-1]["frame"]
                pre[vb]=pre.get(vb,0)+r["value"]
        last_dma[g]=pre
    return dict(firmware=joint["firmware_SHA256"],client=joint["client_SHA256"],
                start=joint["parameters"]["start"],parameters=joint["parameters"],terms=rows,intervals=intervals,
                dense_ms=(reveals[970]["clock"]-reveals[951]["clock"])*1000/MASTER,
                dense_vblank=sum(intervals[g] for g in range(952,971)),
                last_ACK=last["ACK_masterclock"],pre_SEAL_DMA_by_relative_frame=last_dma,
                line951=reveals[951]["line"],frames=joint["commits"],
                evidence={name:sha(folder/name) for name in ("joint.json","window.csv","seal528.csv","events.json","packets.jsonl")},
                upload_late=upload_late,instructions=joint["ARM_instructions"],wire_bytes=joint["wire_B"],
                rom_read_allocations=joint["ROM_read_allocations"],vram_dma_bytes=joint["vram_DMA_B"])


def analyze(temp):
    matches=match()
    target=sorted({g for m in matches.values() for g in m["captures"]} | {951,957,959,969})
    result=dict(physical_matches=matches,phases={},guards={},
                scope="MMC805/807 physical bins matched within 20% of MMC805 on map, OBJ and BG. Replay captures match MMC807 on map and OBJ only. Same-input timed ARM/65816 comparison under modeled SPI, ROM and IRQ timing.",
                physical_sources={n:sha(PROBES/p) for n,p in
                                  ((805,"nes-trial805/hardware805-806.zip"),(807,"nes-obj807/hardware807-808.zip"))})
    for n in (807,808):
        c=read(PROBES/f"nes-output809/check{n}.json")
        result["guards"][n]=dict(parent=c["parent"],candidate=c["candidate"],
                                  crc_instructions=c["arm_instructions"],tested_inputs=c["linked_crc_inputs"],
                                  ACK=c["guards"]["ACK"],menu=c["guards"]["menu"],
                                  input_checks=c["guards"]["input"],object_recovery=c["object_recovery"])
    for phase in (1,2):
        folders=[temp/f"nes-output809-{label}-p{phase}" for label in ("base","fold")]
        base,fold=[schedule(d,target) for d in folders]
        assert base["start"]==fold["start"]==7288416+(phase-1)*178684
        assert base["client"]==fold["client"]
        assert base["parameters"]==fold["parameters"]
        assert base["firmware"]==result["guards"][807]["parent"]["firmware"]
        assert fold["firmware"]==result["guards"][807]["candidate"]["firmware"]
        for m in matches.values():
            for g,counts in m["captures"].items():
                assert base["terms"][g]["work"]==fold["terms"][g]["work"]
                assert counts["obj"]==base["terms"][g]["work"]["obj"]
                assert counts["mapdirty"]==base["terms"][g]["work"]["map_groups"]
        for g in range(905,971):
            for pattern in ("map-{}.bin","frame-{}.rgb","expected-{}.bin"):
                a,b=[(d/pattern.format(g)).read_bytes() for d in folders]
                assert a==b, (phase,g,pattern)
        result["phases"][phase]=dict(base=base,fold=fold,identical_map_expected_RGB_frames=66,
                                     changed_VBlank_intervals={g:[n,fold["intervals"][g]] for g,n in base["intervals"].items()
                                                               if n!=fold["intervals"][g]},
                                     delta_dense_ms=fold["dense_ms"]-base["dense_ms"],
                                     delta_last_ACK_ms=(fold["last_ACK"]-base["last_ACK"])*1000/MASTER)
    for mode in ("base","fold"):
        phases=[p[mode] for p in result["phases"].values()]
        common=set(phases[0]["upload_late"]) & set(phases[1]["upload_late"])
        result.setdefault("prior_blank_candidates",{})[mode]=sorted(
            (dict(generation=g,bound_ms=[p["upload_late"][g]["prior_line246_advance_ms"] for p in phases],
                  interval=[p["intervals"][g] for p in phases]) for g in common
             if all(p["intervals"][g]>=3 for p in phases)),key=lambda r:(max(r["bound_ms"]),r["generation"]))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8",newline="\n")
