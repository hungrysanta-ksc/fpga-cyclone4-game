"""Reconcile wall time, individual consumer heads and the ARM's actual E0 target."""
import argparse
import json
from collections import Counter
from csv import DictReader
from pathlib import Path

from analyze_nes_map830 import packets, window
from analyze_nes_output822 import CLK_MS
from analyze_nes_repeat833 import inspect
from analyze_nes_seal831 import measure
from nes_tail834 import OUT, PROBES
from nes_raw506 import sha
from replay_nes_repeat833 import verify_rejection


def audit(folder,ref):
    row=measure(folder,ref)
    baseline=measure(ref,ref)
    assert inspect(folder)[0]==inspect(ref)[0]
    data=packets(folder)
    wire=json.loads((folder/"events.json").read_bytes())
    transfers=[e for e in wire if e.get("opcode")=="0xe1"]
    assert len(data)==len(transfers)
    rows=[e for e in window(folder) if e["g"]==909]
    obj=row["milestones"]["OBJ_return"][0]
    end=row["milestones"]["SEAL_accept"][0]
    busy=0
    critical=[]
    heads={}
    for e in rows:
        if e["event"] in ("load","ack"):
            heads.setdefault(e["index"],{})[e["event"]]=e["clock"]
    ordinary={}
    for section in (3,4):
        selected=[i for i in heads if data[i-1][1]==section]
        if selected:
            i=selected[-1]
            ordinary[section]=dict(index=i,wire_end=round(transfers[i-1]["clock"]),**heads[i])
    for i,h in heads.items():
        a,b=h["load"],h["ack"]
        overlap=min(b,end)-max(a,obj)
        if overlap<=0:
            continue
        p=data[i-1]
        busy+=overlap
        critical.append(dict(index=i,op=p[0],section=p[1],offset=int.from_bytes(p[10:12],"little"),
                             E1_end=round(transfers[i-1]["clock"]),load=a,ACK=b,in_interval=overlap))
    seal_index=next(i for i,h in heads.items() if h["load"]==end)
    sent=transfers[seal_index-1]["clock"]
    status=[e for e in wire if e.get("opcode")=="0xe0" and e["generation"]==909]
    stamps=(folder/"credit833.txt").read_text().splitlines()
    regs=(folder/"window834.txt").read_text().splitlines()
    ledger=[]
    for e,stamp,reg in zip(status,stamps,regs,strict=True):
        t,caller=stamp.split()
        t2,issued,before,through=reg.split()
        assert t==t2 and float(t)<=e["start"]
        rx=bytes.fromhex(e["reply"])
        accepted=int.from_bytes(rx[3:5],"big")
        retired=int.from_bytes(rx[5:7],"big")
        assert int(issued)==accepted and int(before)<=retired<=accepted
        if not obj<=e["start"]<end:
            continue
        assert caller in ("send","nes_window184_through")
        target=accepted-3 if caller=="send" else int(through)
        ledger.append(dict(start=round(e["start"]),end=round(e["clock"]),why=caller,
                           accepted=accepted,target=target,before=int(before),retired=retired,
                           active=next((i for i,h in heads.items() if h["load"]<=e["start"]<h["ack"]),None)))
    with (folder/"seal528.csv").open() as f:
        detail=list(DictReader(f))
        raw=[(int(e["dst"]),int(e["bytes"])) for e in detail if e["g"]=="909" and
             e["event"]=="dma" and e["port"]=="24" and 0x5000<=int(e["dst"])<0x5100]
    assert raw==[(0x5000,64),(0x5002,64),(0x5020,64)]
    fixed="fixed" in folder.name
    if fixed:
        assert row["reveals"][:4]==baseline["reveals"][:4] and row["ACK2572"]==baseline["ACK2572"]
    ranges=[(r[0],r[2]) for r in row["map2580"]]
    map_edges=[[e[k] for k in ("index","event","clock","frame","line")] for e in window(folder)
               if e["g"]==910 and e["section"]==2 and e["event"] in ("load","ack")]
    delta=row["last_ACK"]-baseline["last_ACK"]
    waits=[[e["clock"],e["frame"],e["line"]] for e in rows if e["event"]=="wait169" and e["clock"]>=end]
    groups=[e for e in rows if e["event"]=="ppu_dma" and e["clock"]>=end]
    assert groups
    budget=None
    # Only extrapolate within a known VBlank. Line 240 can be four master
    # clocks short on NTSC, so use a beam sample strictly later than that.
    for latch in detail:
        if latch["g"]!="909" or latch["event"]!="latch":
            continue
        clk,line,h=(int(latch[k]) for k in ("clock","line","h"))
        if not (240<line<=261 and waits and waits[0][1]==48 and clk<=waits[0][0] and waits[0][0]-clk<1364*16):
            continue
        blank_end=clk-h+(262-line)*1364
        following=next((e for e in groups if e["clock"]>=waits[0][0]),None)
        if not (waits[0][0]<blank_end and following and following["frame"]==49):
            continue
        span=row["OAM_complete"][0]-following["clock"]
        budget={"remaining_at_wait":blank_end-waits[0][0],"following_PPU_span":span,
                "shortfall_at_observed_span":span-(blank_end-waits[0][0])}
    repairs=folder/"repairs834.txt"
    repair_rows=[int(s.split()[1]) for s in repairs.read_text().splitlines() if s.startswith("909 ")] if repairs.exists() else None
    return dict(ARM=row["ARM"],boot_ROM=row["boot_ROM"],delta2572=row["reveals"][3][0]-baseline["reveals"][3][0],
                milestones=row["milestones"],OBJ_to_SEAL_clocks=end-obj,OBJ_to_wire_end=round(sent-obj),
                wire_end_to_SEAL=round(end-sent),busy_clocks=busy,between_heads=end-obj-busy,
                heads=critical,E0=ledger,polls=dict(Counter(r["why"] for r in ledger)),last_ordinary=ordinary,
                palette=row["palette_complete"],OAM=row["OAM_complete"],tile48=row["tile_B_in_VB48"],
                intervals=row["intervals"],map2580=ranges,map2580_heads=map_edges,last_ACK=row["last_ACK"],delta_ACK=delta,waits=waits,
                WRAM_repaired_rows=repair_rows,blank48_budget=budget,
                passed_gate=row["all_DMA_by_VB48"] and row["reveals"][3][0]==baseline["reveals"][3][0]
                and sum(row["intervals"])<16 and ranges==[(768,51),(704,52)] and delta<0)


def safety(temp):
    meta={}
    for mode in ("stock","palette","oam","bg","bgidle","bgpre","bgdirty"):
        version=("833" if mode=="stock" else "834")+mode
        fw=PROBES/f"nes-output823/link-{version}/src/obj-nes-100/firmware.stm"
        menu=json.loads((OUT/f"menu-{mode}.json").read_bytes())
        base=json.loads((OUT/f"base-{mode}/result.json").read_bytes())
        assert menu["firmware"]==base["firmware_sha256"]==sha(fw)
        assert base["safe_return"] and base["base_restored"] and menu["rows"]["normal"]["released"]
        meta[mode]={"Flash_B":fw.stat().st_size,"menu_and_base":True,"ARM":sha(fw)}
    for kind in ("checked","wide","inspect"):
        rom=OUT/("client-"+kind)
        build=json.loads((rom/"build.json").read_bytes())
        meta[kind]={"ROM":sha(rom/"sink165.sfc"),"size":build["physical_ROM_B"],"free":build["physical_free_B"]}
    for mode in ("stock","bgdirty"):
        prefix=f"nes-tile821-demoB-jointmirror-p1-834{mode}inspectfixed"
        for fault in ("stop","damage"):
            folder=temp/(prefix+fault)
            verify_rejection(folder,fault)
            meta[mode+"_"+fault]=228 if fault=="stop" else 224
    prefix="nes-tile821-demoB-jointmirror-p1-834stockinspectfixed"
    repaired=temp/(prefix+"repair")
    assert (repaired/"repairs834.txt").read_text().splitlines().count("909 1")==1
    assert measure(repaired,temp/"nes-tile821-demoB-jointmirror-p1-832base")["last_ACK"]>0
    meta["repaired_corrupted_row"]=1
    for phase in (1,2):
        pfx=f"nes-tile821-demoB-jointmirror-p{phase}-834"
        cold=(temp/(pfx+"stockinspect")/"repairs834.txt").read_text().splitlines()
        assert all(f"{g} {r}" in cold for g in (905,906) for r in range(6))
        fault=json.loads((temp/(pfx+"bginspectfixed")/"fault.json").read_bytes())
        def field(owner,name):
            node=fault[owner]
            return bytes.fromhex(node["bytes"])[node["layout"][name]]
        assert [field("plan",k) for k in ("started","ending","sent","bulk_pending")]==[1,0,0,0]
        assert field("sink","error")==5 and field("transport","error")==0
    meta["cold_repair_each_bank"]=6
    meta["rejected_early_ordinary"]={"started":1,"ending":0,"sent":0,"sink_error":5}
    return meta


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("tags",nargs="+")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    result={}
    for phase in (1,2):
        result[phase]={}
        prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
        for tag in a.tags:
            r=audit(a.temp/(prefix+"834"+tag),a.temp/(prefix+"832base"))
            result[phase][tag]=r
            print(phase,tag,r["intervals"],r["delta2572"],r["map2580"],r["delta_ACK"],r["OAM"][1:],
                  round(r["OBJ_to_SEAL_clocks"]/CLK_MS,3),r["polls"])
    if a.out:
        lines=["{",'  "checks": '+json.dumps(safety(a.temp))+","]
        for phase,runs in result.items():
            lines.append(f'  "{phase}": {{')
            lines.append(",\n".join("    "+json.dumps(k)+": "+json.dumps(v) for k,v in runs.items()))
            lines.append("  }"+("," if phase==1 else ""))
        a.out.write_text("\n".join(lines+["}",""]),newline="\n")
