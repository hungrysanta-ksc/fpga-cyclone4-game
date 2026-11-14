"""Compare linked ARM quiet polling with unchanged A and B at identical phase and workload."""
import argparse
import json
from pathlib import Path
from analyze_nes_output768 import timeline, one, csv_groups, read, sha, ms


def run(temp):
    result = {}
    for ph in (1,2):
        result[ph]={}
        reference=temp/f"nes-cost768-763-p{ph}-ext"
        for mode,folder in (("763",reference),("767",temp/f"nes-cost768-767-p{ph}-ext"),
                            ("769",temp/f"nes-cost769-p{ph}")):
            joint=read(folder/"joint.json")
            assert joint["parameters"]["start"]==7288416+(ph-1)*178684
            assert joint["passed"] and joint["commits"]==joint["map_WRAM_VRAM_verified"]==66
            for g in range(905,971):
                for pat in ("frame-{}.rgb","map-{}.bin","expected-{}.bin"):
                    assert (folder/pat.format(g)).read_bytes()==(reference/pat.format(g)).read_bytes()
            events=read(folder/"events.json"); cpu=csv_groups(folder/"window.csv")
            packets=[json.loads(line) for line in (folder/"packets.jsonl").read_text().splitlines()]
            t=timeline(folder,969,cpu,events,packets)
            ev=[e for e in events if e["generation"]==969]
            begin=one(ev,"output_enter531")["clock"]
            seal=next(e["start"] for e in ev if e.get("opcode")=="0xe1" and e.get("packet_opcode")==3)
            previous=None
            calls=quiet=0
            for e in events:
                if e.get("opcode")!="0xe0":continue
                b=bytes.fromhex(e["reply"])
                status=(b[5:7],b[2]&8)
                if begin<=e["start"]<seal:
                    calls+=1;quiet+=previous==status
                previous=status
            def reveal(g):
                return one([r for r in cpu[g] if r["op"]==3],"reveal")
            row={k:t[k] for k in ("work","output_ms","display_interval_VB","dma_bytes_output_entry_to_SEAL_load","post_SEAL_DMA_bytes","final_ACK","final_waits")}
            row.update(E0_before_SEAL=calls,E0_quiet_before_SEAL=quiet,final970=joint["frames"][-1]["ACK_masterclock"],
                       dense952_957_ms=ms(reveal(957)["clock"]-reveal(951)["clock"])/6,
                       ACK957=one([r for r in cpu[957] if r["op"]==3],"ack")["clock"],
                       firmware=joint["firmware_SHA256"],joint=sha(folder/"joint.json"))
            result[ph][mode]=row
        a,b,c=result[ph].values()
        assert a["work"]==b["work"]==c["work"] and b["dma_bytes_output_entry_to_SEAL_load"]==c["dma_bytes_output_entry_to_SEAL_load"]==496
        assert b["display_interval_VB"]==c["display_interval_VB"]==3 and c["E0_quiet_before_SEAL"]<b["E0_quiet_before_SEAL"]
    return dict(scope="timing-model replay, linked CPU bytes, 969 work proxy, physical followup pending",phases=result)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(run(a.temp),indent=2)+"\n")
