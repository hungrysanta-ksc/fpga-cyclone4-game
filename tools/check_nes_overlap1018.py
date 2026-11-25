"""Compare final-link schedules without adding field and replay deltas."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from check_nes_output970 import packet_path
from check_nes_tail1013 import collect, guards
from nes_overlap1018 import BASE, ROOT, WORK
from test_nes_raw506_joint import MASTER


def ms(clocks):
    return round(clocks*1000/MASTER,4)


def bound(temp):
    modes=("control","prefix","group","credit","maphead")
    result={}
    hashes={}
    for phase in (1,2):
        result[phase]={}
        for mode in modes:
            run=temp/f"nes-tile821-late-jointmirror-p{phase}-1018wire-{mode}"
            frames,meta=collect(run)
            if mode=="control":
                base=frames
                original,_=collect(temp/f"nes-tile821-late-jointmirror-p{phase}-1013c-control")
                assert all(frames[g]==original[g] for g in frames)
                reference_reads=meta["ROM_read_allocations"]
            fw=(BASE if mode=="control" else WORK/mode)/"link/src/obj-nes-100/firmware.stm"
            digest=hashlib.sha256(fw.read_bytes()).hexdigest()
            assert meta["firmware_SHA256"]==digest and fw.stat().st_size<=212992
            hashes[mode]=dict(firmware=digest,flash_B=fw.stat().st_size)
            assert meta["ROM_read_allocations"]==reference_reads
            for g,c in frames.items():
                for key in ("work","rgb","map","packet_digest"):
                    assert c[key]==base[g][key],(mode,phase,g,key)
            g=908
            events=list(csv.DictReader((run/"window.csv").open()))
            def marks(name):
                return [[int(x[k]) for k in ("clock","frame","line","value")] for x in events
                        if int(x["g"])==g and x["event"]==name]
            packets=frames[g]["order"]
            _,ledger=packet_path(run,g,expected_shape=(len(packets),sum(x[0]==7 for x in packets)))
            tail=[(p,q) for p,q in zip(packets,ledger,strict=True) if p in
                  ([2,5,1121,201],[2,5,1322,240],[9,4,0,116])]
            assert len(tail)==3
            ret=marks("return1018")[-1]
            jobs=[json.loads(line) for line in (run/"producer.jsonl").read_text().splitlines()]
            final=[x for x in jobs if x["generation"]==g][-1]
            assert final["kind"]==1 and final["token"]==ret[-1]
            arm=json.loads((run/"arm1018.json").read_bytes())
            build,=[x["clock"] for x in arm if x["event"]=="nes_sink212_seal" and x["g"]==g]
            tx=[]
            for (op,sec,offset,size),q in tail:
                ready,=[x["clock"] for x in arm if x["event"]=="ready1012" and
                       (x["g"],x["op"],x["section"],x["offset"])==(g,op,sec,offset)]
                assert build<=ready<=q["issue"]+1 and q["issue"]<=q["arrive"]<=q["load"]<=q["ack"]
                tx.append(dict(bytes=size,assembled_from_return_ms=ms(ready-ret[0]),
                               issued_from_return_ms=ms(q["issue"]-ret[0]),sent_from_return_ms=ms(q["arrive"]-ret[0]),
                               accepted_from_return_ms=ms(q["load"]-ret[0])))
            last=marks("ppu_last")[-1][:3]
            assert frames[g]["seal"][0]<last[0]<frames[g]["show"][0]<frames[g]["ack"][0]
            row=dict(work=frames[g]["work"],tiles=sum(x["bytes"]//(16<<x["kind"]) for x in jobs if x["generation"]==g),
                     bank_token=final["token"],return_clock_frame_line=ret[:3],planner_done_by_ms_before_return=ms(ret[0]-build),
                     tail=tx,preseal_DMA=frames[g]["dma_preseal"],seal=frames[g]["seal"],dma_end=last,show=frames[g]["show"],ack=frames[g]["ack"],
                     display_interval=frames[g]["show"][1]-frames[g-1]["show"][1],end_ack=frames[912]["ack"],
                     allocated_ROM_reads=reference_reads,checked_frames=len(frames),
                     all_23_row_frames={k:{field:v[field] for field in ("seal","show","ack","work")} for k,v in frames.items() if v["work"][2]==23})
            ref=row if mode=="control" else result[phase]["control"]
            row["advance_ms"]={k:ms(ref[k][0]-row[k][0]) for k in ("seal","dma_end","show","ack","end_ack")}
            result[phase][mode]=row
    return dict(baseline="MMC1012",scope="Linked M4 and 65816, fixed captures and ROM grant calendar. The field generations have no ARM packet trace.",
                prior_ROM_savings_added=False,firmware=hashes,phases=result,
                guards={m:guards(m,root=WORK/m) for m in modes if m!="control"})


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    a=p.parse_args()
    report=bound(a.temp)
    (ROOT/"analysis/overlap1018-results.json").write_text(json.dumps(report,indent=2)+"\n")
