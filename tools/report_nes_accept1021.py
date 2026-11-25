"""Reconcile SEAL service, queue delays and publication on a single clock."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_tail1013 import collect
from check_nes_menu533 import check as menu_check
from nes_accept1021 import OUT, PACKED, ROOT, sha
from nes_tail1013 import BASE
from report_nes_split1020 import frame908


def read(path):
    return json.loads(path.read_bytes())


def measure(path):
    with (path/"window.csv").open() as stream:
        all_rows=[r for r in csv.DictReader(stream) if r["g"]=="908"]
    rows=[r for r in all_rows if r["op"]=="3"]
    def clock(name):
        return next(int(r["clock"]) for r in rows if r["event"]==name)
    fast=any(r["event"]=="verify1021" for r in rows)
    names=["load","seal","layout1021" if fast else "compact489",
           "semantics1021" if fast else "validate181","coverage212","map_coverage212",
           "local165_entry","upload165_entry"]
    marks=[clock(n) for n in names]
    stages=["header","manifest","compact_layout","HDMA_semantics","tile_coverage","map_coverage","local_ready"]
    spans=dict(zip(stages,[b-a for a,b in zip(marks,marks[1:])],strict=True))
    assert sum(spans.values())==marks[-1]-marks[0]
    def point(r):
        return [int(r[k]) for k in ("clock","frame","line")]
    return dict(stages=spans,service=sum(spans.values()),seal_load=marks[0],upload=marks[-1],
                residual_last=point(next(r for r in reversed(rows) if r["event"]=="ppu_last")),
                reveal=point(next(r for r in rows if r["event"]=="reveal")),
                ack=point(next(r for r in rows if r["event"]=="ack")))


def report(temp):
    build=read(OUT/"build.json")
    result=dict(arm=sha(BASE/"link/src/obj-nes-100/firmware.stm"),parent=sha(PACKED/"sink165.sfc"),
                client=sha(OUT/"sink165.sfc"),rom_bytes=build["loader_B"]+build["encoded_B"]+64,
                board_capacity=5120,extra_WRAM_bytes=90,phases={})
    ref=read(ROOT/"analysis/trial1012-package.json")
    assert result["parent"]==ref["client"] and result["arm"]==ref["firmware"]
    for i in (1,2):
        prefix=f"nes-tile821-late-jointmirror-p{i}-"
        folder=temp/"nes-accept1021-fixed"
        old=temp/(prefix+"1018wire-control")
        new=temp/(prefix+"1021-accept")
        a,model=collect(old); b,test=collect(new)
        assert model["firmware_SHA256"]==test["firmware_SHA256"]==result["arm"]
        assert test["client_SHA256"]==result["client"] and test["passed"] and test["commits"]==8
        for g in range(905,913):
            for k in ("packet_digest","work","map","rgb"):
                assert a[g][k]==b[g][k],(i,g,k)
        assert model["ROM_read_allocations"]==test["ROM_read_allocations"]
        control=frame908(old,a)
        actual=frame908(new,b,control["vblank225"])
        for r in (control,actual):
            assert any(d["source"]==65536+768 and d["length"]==192 and d["start"][1]==38 for d in r["preseal_dma"])
        profile=measure(folder/f"p{i}-profile")
        changed=measure(new)
        assert profile["ack"]==control["ack"]
        trigger=read(folder/f"p{i}-trigger/checks1021.json")
        ref_trigger=read(ROOT/"analysis/split1020-results.json")["dma_start_triggered_replay"][str(i)]
        result["phases"][i]=dict(control=profile,joint=changed,fixed=measure(folder/f"p{i}-fixed"),
            previous_trigger_service=ref_trigger["timing"]["upload165_entry"][0]-ref_trigger["timing"]["load"][0],
            trigger=measure(folder/f"p{i}-trigger"),trigger_preseal_map=trigger["map_DMA"],
            last_clock_before_line247=control["line247"]-1,
            control_table=control["table"],joint_table=actual["table"],early_dma=actual["preseal_dma"],
            late_seal_clocks=changed["seal_load"]-profile["seal_load"],same_cache_reads=test["ROM_read_allocations"],
            final_generation_ACK=[a[912]["ack"],b[912]["ack"]])
    result["faults"]={m:read(temp/f"nes-accept1021-fixed/p1-{m}/checks1021.json")
                      for m in ("bad_seal","coverage","late_damage","stop_after")}
    for v in result["faults"].values(): assert v["previous_screen_retained"] and v["commits"]==3
    menu=menu_check(BASE/"link/src","1012")
    result["menu"]=menu["rows"]["normal"]
    assert menu["firmware"]==result["arm"] and result["menu"]["released"]==1
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("temp",type=Path)
    (ROOT/"analysis/accept1021-results.json").write_text(json.dumps(report(p.parse_args().temp),indent=2)+"\n",newline="\n")
