"""Reconcile measured master-clock deadlines with the 657 loader, CPU and placement artifacts."""
import argparse,csv,json
from pathlib import Path
from analyze_nes_sender652 import budget
from check_nes_fault641 import digest,evidence
from test_nes_service509_schedule import Calendar

MASTER=21477272

def read(path):return json.loads(path.read_bytes())
def csv_rows(path):
    with path.open(newline="") as fp:return list(csv.DictReader(fp))

def timeline(d,ref,base,chr_rom,cal):
    check_error=d/"callback-error.txt"
    if check_error.exists():
        assert "DMA endpoint outside VBlank" in check_error.read_text(),d
    ev=read(d/"events.json");cpu=csv_rows(d/"window.csv")
    decoded={int(r["g"]):r for r in cpu if r["event"]=="reveal"}
    get_clock=lambda g:int(decoded[g]["clock"])
    seals=[r["start"] for r in ev if r.get("generation")==954 and r.get("packet_opcode")==3]
    assert len(seals)==1
    result=dict(revealed_through=max(decoded),intervals={str(g):int(decoded[g]["frame"])-int(decoded[g-1]["frame"])
        for g in (951,952,953,954,955,957) if g in decoded},line951=int(decoded[951]["line"]),
        SEAL954_from_953_ms=(seals[0]-get_clock(953))*1000/MASTER,
        margin954_ms=ref["SEAL_from_953_ms"]-(seals[0]-get_clock(953))*1000/MASTER,
        absolute_margin954_ms=(ref["SEAL_start"]-seals[0])*1000/MASTER,
        events=digest(d/"events.json"),window=digest(d/"window.csv"))
    if check_error.exists():
        assert not (d/"joint.json").exists()
        result["VBlank_rejection"]=dict(error="DMA endpoint outside VBlank",last_event=cpu[-1],log=digest(check_error))
    data=d/"bus659.csv"
    if data.exists():
        bursts=[];entry=None
        for row in csv_rows(data):
            g=int(row["g"]);t=int(row["clock"]);addr=int(row["address"]);v=int(row["value"])
            if row["event"]=="prime":
                entry=dict(g=g,address=addr,prime=t,prime_line=int(row["line"]),valid=0,reads=0);bursts.append(entry)
            if row["event"]=="read":
                assert addr==entry["address"]+entry["reads"]
                if int(row["consumed"])>entry["valid"]:
                    assert int(row["consumed"])==entry["valid"]+1
                    assert v==chr_rom[(addr&~15)+(addr&1)*8+(addr%16)//2]
                    entry["valid"]+=1
                if not entry["reads"]:entry.update(first=t,first_line=int(row["line"]))
                entry["reads"]+=1;entry["last"]=t;entry["last_line"]=int(row["line"])
        result["direct"]=dict(initiated=len(bursts),completed=sum(b["valid"]==16 for b in bursts),
            reads=sum(b["reads"] for b in bursts),valid=sum(b["valid"] for b in bursts),trace=digest(data))
        if bursts:
            first=bursts[0]
            result["direct"]["first_prime_to_read_us"]=(first["first"]-first["prime"])*1e6/MASTER if "first" in first else None
            result["direct"]["last_burst"]=bursts[-1]
        rejection=d/"reject659.txt"
        if rejection.exists():
            g,clock,w,n=map(int,rejection.read_text().split())
            assert g>max(decoded) and not (d/"joint.json").exists()
            result["reject"]=dict(g=g,clock=clock,words=w,consumed=n,
                cause=next((r["value"] for r in reversed(csv_rows(data)) if r["event"]=="reject"),None))
            if bursts and bursts[-1]["reads"]==16:
                b=bursts[-1];start=b["first"];end=b["last"]
                # Even granting the full 4 B before the first byte, each
                # later completed slot can provide only another 2 B.
                grants=0;at=start
                while True:
                    begin,reply=cal.select(at)
                    if reply>end:break
                    grants+=1;at=begin+1
                result["reject"]["new_grants_during_DMA"]=grants
                result["reject"]["optimistic_available_B"]=min(16,4+2*grants) # ready and outstanding together occupy at most two words
    if (d/"joint.json").exists():
        j=read(d/"joint.json");assert j["passed"] and j["commits"]==53
        ack=j["frames"][-1]["ACK_masterclock"];result["ACK957"]=ack
        result["ACK957_delta657_ms"]=(ack-base["last_ACK"])*1000/MASTER
        result["joint"]=digest(d/"joint.json")
        if d.name.endswith(("live","control")):
            assert j["client_SHA256"]==digest(d/"client.sfc")
        result["dense_ms"]=(get_clock(955)-get_clock(950))*200/MASTER
    return result

def run(a):
    t=a.traces;phases={}
    baseline=evidence("record657-verification.json");fw=baseline["firmware"]
    assert digest(a.arm/"src/obj-nes-100/firmware.stm")==fw
    baseboard=t/"nes-record657-board-port";linked=t/"nes-bg659-board-linked02"
    costs={m:budget(t/("nes-bg659-board-"+m)) for m in ("layout03","direct03","jobs02","linked02")}
    assert all(not x["STA"] and not x["SOF"] and x["LAB_error"] for x in costs.values())
    full=t/"nes-bg659-rtl-linked";jobs=t/"nes-bg659-jobrtl02"
    for name in ("nes_rom_loader.sv","nes_rom_physical.sv","nes_rom_boot.sv","nes_bg_window659.sv","nes_sink_bus165.sv","sink-program.hex"):
        assert digest(full/name)==digest(linked/name)
    assert digest(jobs/"nes_tile205.sv")==digest(linked/"nes_tile205.sv")
    assert "PASS659" in (full/"vsim.log").read_text() and "PASS659" in (jobs/"vsim.log").read_text()
    ids=read(jobs/"jobs.json");assert len(ids)==268
    bound=t/"nes-bg659-bound01"
    assert digest(bound/"window.sv")==digest(linked/"nes_bg_window659.sv")
    assert "PASS659" in (bound/"vsim.log").read_text()
    bounds=[list(map(int,row.split())) for row in (bound/"bounds.txt").read_text().splitlines()]
    assert len(bounds)==4 and all(row[3]==4 for row in bounds)
    assert digest(linked/"sink-program.hex")==digest(a.probe/"client01/sink-program.hex")
    guards={}
    for k in ("none","program","done","busy","token"):
        r=a.probe/f"base-{k}/result.json";v=read(r);assert v["passed"] and v["firmware_sha256"]==fw
        guards[k]=digest(r)
    v=read(a.probe/"menu.json");assert v["firmware"]==fw and v["rows"]["normal"]["released"]==1
    guards["menu"]=digest(a.probe/"menu.json")
    for k,want in (("good","return 16"),("inverse","reject 0"),("generation","reject 0"),("slot","reject 0"),("stop","reject 16")):
        f=t/"nes-bg659-cpuguard"/k/"result.txt";assert f.read_text()==want;guards["CPU_"+k]=digest(f)
    cal=Calendar(t/"nes-service509-rom03");game=a.game.read_bytes();assert digest(a.game)==evidence("mmc480-verification.json")["live_functional"]["rom_sha256"]
    for n in ("1","2"):
        ref=evidence("geometry650-verification.json")["phases"][n]["cases"]["base"]["cost"]
        base=baseline["schedules"]["staged2"][n]
        cases={"657":dict(intervals=base["intervals"],margin954_ms=base["margin954_ms"],ACK957=base["last_ACK"])}
        for label,mode,tag in (("no_contention_fixture","open","fixed"),("calendar_fixture","calendar","pair"),("calendar_955_fixture","calendar","only955"),
                               ("linked_control","open","control"),("linked_no_contention","open","live"),("linked_calendar","calendar","live"),
                               ("linked_955_calendar","calendar","live955")):
            d=t/f"nes-bg659-{mode}{n}{tag}"
            v=timeline(d,ref,base,game[-131072:],cal);cases[label]=v
            if tag.startswith("live"):
                desc_count={}
                for row in (d/"packets.jsonl").read_text().splitlines():
                    _,_,packet,bulk=json.loads(row);b=bytes.fromhex(packet)
                    if b[:2]!=b"\x07\x00":continue
                    g=int.from_bytes(b[8:10],"little");s=int.from_bytes(b[10:12],"little")//16
                    if g not in ((955,) if tag=="live955" else (954,955)):continue
                    data=bytes.fromhex(bulk)
                    for j in range(0,len(data),16):
                        key=f"{g}/{s+j//16}"
                        if key not in ids:
                            assert s+j//16==0 and data[j:j+16]==bytes(16)
                        else:
                            assert data[j:j+16].hex()==ids[key];desc_count[g]=desc_count.get(g,0)+1
                assert desc_count.get(954 if tag=="live" else 955)==(10 if tag=="live" else 9)
                v["published_BG_jobs"]=desc_count
        phases[n]=cases
    return dict(firmware=fw,base_fit=budget(baseboard),costs=costs,phases=phases,guards=guards,
        client=read(a.probe/"client01/build.json"),client_sha256=digest(a.probe/"client01/sink165.sfc"),
        jobs=digest(jobs/"jobs.json"),PSRAM_log=digest(full/"vsim.log"),job_log=digest(jobs/"vsim.log"),
        calendar=cal.summary,burst_RTL_grant_replay=bounds,burst_RTL_log=digest(bound/"vsim.log"),scope="Timed linked CPU replay with real RTL descriptor bytes and measured slot calendar. Separate pin-level RTL test. No physical candidate.")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("traces","arm","probe","game","out"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(run(a),indent=2)+"\n",newline="\n")
