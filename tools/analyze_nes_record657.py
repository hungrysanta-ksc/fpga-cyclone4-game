"""Reconcile the full-board 657 record trials and the cycle-identified replays."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from analyze_nes_credit654 import measure
from analyze_nes_direct653 import inputs
from analyze_nes_output615 import read
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest, evidence

MODES = ("field", "staged2", "split", "count", "direct", "lanes", "port")
NODES = ("nes_native_export203:native_export", "nes_native_mailbox165:native_records",
         "nes_native_spi165:native_spi")
RTL = ("nes_native_spi165.sv", "nes_native_export203.sv", "nes_native_mailbox165.sv",
       "nes_geometry_sender653.sv")


def area(board):
    mapping = (board/"output_files/board.map.rpt").read_text()
    report = (board/"output_files/board.fit.rpt").read_text()
    boundary = {}
    for node in NODES:
        row = re.search(r"\|"+node+r"\|\s*;\s*(\d+) \((\d+)\)\s*;\s*(\d+) \((\d+)\)",mapping)
        assert row, node
        boundary[node] = dict(local_LUT=int(row[2]),local_FF=int(row[4]))
    blocks=[r.split(";") for r in report.splitlines() if NODES[-1]+"|" in r and "|ALTSYNCRAM " in r]
    assert len(blocks)==1
    return dict(whole=budget(board),boundary=boundary,RAM=[x.strip() for x in blocks[0][2:9]])


def bundle_constraints(board, width, direct):
    active=[board/p for p in ("cdc181.sdc","cdc576.sdc","cdc611.sdc")]
    constraints="\n".join(p.read_text() for p in active)
    delays={}
    for prefix in ("set_max_delay","set_false_path -hold"):
        pairs=set()
        for line in constraints.splitlines():
            if line.startswith(prefix) and "native_records|received[" in line:
                found=re.search(r"(native_records\|held|native_export\|held_data)\[(\d+)\].*native_records\|received\[(\d+)\]",line)
                assert found and found[2]==found[3],line
                bit=int(found[2])
                assert (found[1]=="native_export|held_data")==bool(direct and bit<64)
                if prefix=="set_max_delay":
                    delay=float(line.split()[1])
                    assert delay in (11.904,23.808)
                    delays[bit]=delay
                pairs.add(bit)
        assert pairs==set(range(width)),(board,prefix,pairs)
    return dict(paired_lanes=width,payload_from_exporter_FF=64 if direct else 0,
                max_delay_ns_lane_counts=dict(Counter(delays.values())),post_FIT_timing=False)


def record_counts(folder):
    def trace(name):
        return [(int(t),int(v,16)) for t,v in (row.split() for row in (folder/name).read_text().splitlines())]
    sent=trace("launch.txt"); taken=trace("accept.txt")
    # The last directed STOP is at generation 958 with a single source word
    # in flight. No host handshake or credit is expected for that word.
    assert len(sent)==len(taken)+1 and (sent[-1][1]>>77)&65535==958
    assert [v for _,v in sent[:-1]]==[v for _,v in taken]
    assert all(a<=b for (a,_),(b,_) in zip(sent[:-1],taken,strict=True))
    counts=Counter();gens=set();writes=Counter()
    for _,word in sent:
        if (word>>77)&65535==958:continue
        kind=word>>93
        index=(word>>64)&8191
        gens.add((word>>77)&65535)
        label="map_cell" if kind==0 else ("header" if kind==7 and index==0 else "ordinary_or_control")
        counts[label]+=1
        writes[(word>>77)&65535]+=4 if kind==0 else 12
    assert gens==set(range(905,958))
    return dict(records=sum(counts.values()),parts=dict(counts),hypothetical_scratch_writes_4B_cell_12B_other=dict(total=sum(writes.values()),peak=max(writes.values()),generation954=writes[954],generation955=writes[955]),stop958=dict(launched=len(sent)-sum(counts.values()),accepted=len(taken)-sum(counts.values()),cancelled_pending=1),launch=digest(folder/"launch.txt"),
                accept=digest(folder/"accept.txt"))


def run(a):
    t=a.traces
    old=evidence("stream656-verification.json")
    fw=old["firmware"]
    assert fw==digest(a.arm/"src/obj-nes-100/firmware.stm")
    base=t/"nes-stream656-board-ingress";old_blocks=read(t/"nes-stream656-rtl-ingress/sender.json")
    assert digest(base/"output_files/board.fit.rpt")==old["modes"]["ingress"]["fit"]["fit_report"]
    results={};schedules={}
    for mode in MODES:
        board=t/f"nes-record657-board-{mode}";rtl=t/f"nes-record657-rtl-{mode}"
        guard=t/f"nes-record657-{'guard2' if mode=='split' else 'guard'}-{mode}"
        for name in RTL:
            assert digest(board/name)==digest(rtl/name)==digest(guard/name)
        for folder in (rtl,guard):
            assert "PASS652" in (folder/"vsim.log").read_text()
        width=42 if mode=="split" else 80 if mode in ("direct","field","staged2") else 96
        assert f".WIDTH({width})" in (board/"nes_live_joint.sv").read_text()
        pins={f:digest(board/f) for f in evidence("trial613-package.json")["inputs"] if digest(base/f)!=digest(board/f)}
        blocks=read(rtl/"sender.json"); assert old_blocks.keys()==blocks.keys()
        for g in blocks: assert [r["wire"] for r in blocks[g]]==[r["wire"] for r in old_blocks[g]]
        assert digest(guard/"blocks.txt")==digest(t/"nes-stream656-directed-ingress/blocks.txt")
        arm_guard=a.probe/f"raw-{mode}.json"
        assert read(arm_guard)["firmware"]==fw and read(arm_guard)["raw_cold_cells"]==99
        # Identical full inputs (bytes AND all 901 readiness/codec clocks) feed
        # exactly the same deterministic replay, not an interpolation.
        replay=mode if mode in ("direct","split") else "staged2"
        assert digest(rtl/"sender.json")==digest(t/f"nes-record657-rtl-{replay}/sender.json")
        if replay not in schedules:
            phases={}
            for n in ("1","2"):
                v=measure(t/f"nes-record657-{replay}{n}",t/f"nes-direct653-owner{n}",t/f"nes-front638-both{n}h",blocks,n,fw)
                del v["end"]
                v["ACK_delta_656_clocks"]=v["last_ACK"]-old["modes"]["ingress"]["phases"][n]["last_ACK"]
                phases[n]=v
            schedules[replay]=phases
        results[mode]=dict(area=area(board),constraints=bundle_constraints(board,width,mode=="direct"),
            input=inputs(blocks),replay=replay,ready=digest(rtl/"sender.json"),RTL_changes=pins,
            guard=digest(guard/"vsim.log"),ARM_raw=digest(arm_guard))
    audit=record_counts(t/"nes-record657-audit-base")
    for m in ("lanes","port"):
        assert record_counts(t/f"nes-record657-audit-{m}")==audit
    assert digest(t/"nes-record657-audit-lanes/sender.json")==results["lanes"]["ready"]
    limit=t/"nes-record657-limits2"
    assert "PASS657 limits, 4 ENDs, 2 ABORTs" in (limit/"vsim.log").read_text()
    assert digest(limit/"bench.sv")==digest(Path(__file__).with_name("nes_record657_tb.sv"))
    for name,b in (("reference",base),("candidate",t/"nes-record657-board-port")):
        source=(b/"nes_native_export203.sv").read_text()
        assert source.replace("module nes_native_export203","module "+name,1)==(limit/(name+".sv")).read_text()
    return dict(firmware=fw,baseline=area(base),records=audit,modes=results,schedules=schedules,
                max_count_rtl=dict(bench=digest(limit/"bench.sv"),log=digest(limit/"vsim.log"),accepted_END=4,ABORT=2),
                scope="Actual RTL D1 bytes and ready clocks, linked 654 ARM/65816, two starts, modeled IRQ/SPI/ROM. No placed timing or board trial.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("traces","arm","probe","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a),indent=2)+"\n",newline="\n")
