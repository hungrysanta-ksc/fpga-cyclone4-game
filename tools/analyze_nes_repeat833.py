"""Compare exact raw payloads, E0 status call sites, physical DMA and final ACK."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, window
from analyze_nes_seal831 import measure
from analyze_nes_output822 import CLK_MS
from nes_repeat833 import OUT, PROBES, sha
from replay_nes_repeat833 import verify_rejection


def word(b,i):
    return int.from_bytes(b[i:i+2],"little")


def inspect(folder):
    e1=[e for e in json.loads((folder/"events.json").read_bytes()) if e.get("opcode")=="0xe1"]
    heads=packets(folder)
    commands=[]
    image=bytearray()
    for index,(b,e) in enumerate(zip(heads,e1,strict=True),1):
        if word(b,8)!=909 or b[1]!=5:continue
        at=word(b,10)
        assert at==len(image)
        p=b[16:]
        assert word(b,12)==len(p)
        if b[0]==9:
            assert at==1121 and len(p)==10 and word(b,14)==0
            data=b"".join(p[i*2:i*2+2]*(64 if i==0 else 32) for i in range(5))
        elif b[0] in (4,5):
            assert len(p)==2
            data=p*(word(b,14)//2)
        else:
            assert b[0]==2
            data=p
        image.extend(data)
        commands.append((at,b[0],len(b)+3,index))
    assert len(image)==1754
    return bytes(image),commands


def analyze(temp,phase,mode):
    prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
    ref=temp/(prefix+"832base")
    folder=temp/(prefix+"833"+mode)
    row=measure(folder,ref)
    b=measure(ref,ref)
    image,cmd=inspect(folder)
    assert image==inspect(ref)[0]
    raw=[c for c in cmd if 1121<=c[0]<1505]
    win=window(folder)
    service=0
    for _,_,_,index in raw:
        head={e["event"]:e["clock"] for e in win if e["index"]==index and e["event"] in ("load","ack")}
        service+=head["ack"]-head["load"]
    row["raw_load_to_ack_sum_clocks"]=service
    if mode!="base":
        assert len(raw)==1 and raw[0][1]==9
        assert any(l.startswith("909 6 ") for l in (folder/"bundle833.txt").read_text().splitlines())
    with (folder/"seal528.csv").open() as f:
        physical=[(int(e["dst"]),int(e["bytes"])) for e in csv.DictReader(f) if e["g"]=="909" and
                  e["event"]=="dma" and e["port"]=="24" and 0x5000<=int(e["dst"])<0x5100]
    assert physical==[(0x5000,64),(0x5002,64),(0x5020,64)],physical
    events=[e for e in json.loads((folder/"events.json").read_bytes()) if e.get("opcode")=="0xe0" and e["generation"]==909]
    row["credit_status_total"]=len(events)
    logfile=folder/"credit833.txt"
    if logfile.exists():
        calls=[l.split() for l in logfile.read_text().splitlines()]
        assert len(calls)==len(events)
        row["E0_callers"]=dict(Counter(name for t,name in calls))
        row["E0_after_SEAL_accept"]=sum(float(t)>=row["milestones"]["SEAL_accept"][0] for t,name in calls)
    row["raw_E1_wire_B"]=sum(c[2] for c in raw)
    row["section5_E1_wire_B"]=sum(c[2] for c in cmd)
    row["raw_packets"]=len(raw)
    row["raw_DMA"]=physical
    row["delta2572"]=row["reveals"][3][0]-b["reveals"][3][0]
    row["delta_ACK_ms"]=round((row["last_ACK"]-b["last_ACK"])/CLK_MS,6)
    row["map_preserved"]=[(v[0],v[2]) for v in row["map2580"]]==[(768,51),(704,52)]
    if mode.endswith(("fixed","trace")):
        assert row["reveals"][:4]==b["reveals"][:4] and row["ACK2572"]==b["ACK2572"]
    row["timing_pass"]=row["map_preserved"] and row["delta2572"]==0 and row["all_DMA_by_VB48"] and row["reveals"][4][1]<=48 and sum(row["intervals"])<16 and row["delta_ACK_ms"]<0
    return row


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("modes",nargs="+")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    record={}
    for phase in (1,2):
        record[phase]={}
        for mode in a.modes:
            r=analyze(a.temp,phase,mode)
            record[phase][mode]=r
            print(phase,mode,r["delta2572"],r["tile_B_in_VB48"],r["palette_complete"][1:],r["OAM_complete"][1:],
                  r["intervals"],r["delta_ACK_ms"],r["map_preserved"],r.get("E0_callers",r["credit_status_total"]))
    if a.out:
        meta={}
        for name in ("stock","early","first","mid","oam","front"):
            binary=PROBES/f"nes-output823/link-833{name}/src/obj-nes-100/firmware.stm"
            meta[name]={"Flash_B":binary.stat().st_size,"sha256":sha(binary)}
        client=json.loads((OUT/"client/build.json").read_bytes())
        meta["ROM"]={k:client[k] for k in ("body_bytes","physical_ROM_B","physical_free_B")}
        menu=json.loads((OUT/"menu-mid.json").read_bytes())
        base=json.loads((OUT/"base-mid/result.json").read_bytes())
        assert menu["firmware"]==base["firmware_sha256"]==meta["mid"]["sha256"]
        assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"]
        meta["menu_and_base_mid"]=True
        assert "PASS833" in (OUT/"queue/sim.log").read_text(errors="replace")
        meta["board_queue_heads_checked"]=12
        for fault in ("damage","stop","offset","length","reserved"):
            folder=a.temp/("nes-tile821-demoB-jointmirror-p1-833midfixed"+fault)
            verify_rejection(folder,fault)
            meta[fault]={"status":228 if fault=="stop" else 224,"retained_RGB":(folder/"retained.rgb").exists()}
        # One line per replay retains the absolute clocks without thousands of singleton lines.
        lines=["{", '  "build_and_guards": '+json.dumps(meta)+","]
        for phase,runs in record.items():
            lines.append(f'  "{phase}": {{')
            lines.append(",\n".join("    "+json.dumps(k)+": "+json.dumps(v) for k,v in runs.items()))
            lines.append("  }"+("," if phase==1 else ""))
        a.out.write_text("\n".join(lines+["}",""]),newline="\n")
