"""Match ready bytes, returned credits and actual E1 times to 954/955 scanout."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path
from analyze_nes_export636 import run as verify
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, ms, one, packets, read, sha


def measure(folder,golden,mode):
    proof=verify(folder,golden)
    assert work(folder)==work(golden)
    events=read(folder/"events.json")
    cpu=csv_groups(folder/"window.csv")
    commands=packets(folder)
    all_acks=sorted([r for rows in cpu.values() for r in rows if r["event"]=="ack"],key=lambda r:r["index"])
    assert [r["index"] for r in all_acks]==list(range(1,len(all_acks)+1))
    status=[(int.from_bytes(bytes.fromhex(e["reply"])[5:7],"big"),e["clock"]) for e in events if e.get("opcode")=="0xe0"]
    assert status==sorted(status)
    frames={}
    for g in (954,955):
        owner=[e for e in events if e["generation"]==g]
        done=one(owner,"last_writes646")
        table_bytes=max(e["clock"] for e in owner if e["event"]=="table_store648" and e["clock"]<=done["clock"])
        assert table_bytes<=done["writes"]["tables"]<=done["writes"]["valid"]<=done["clock"]
        output=one(owner,"output_enter531")["clock"]
        e1s=[e for e in owner if e.get("opcode")=="0xe1"]
        heads=[r for r in cpu[g] if r["event"]=="load"]
        previous=one(cpu[g-1],"reveal")["clock"]
        def elapsed(t):return ms(t-previous)
        costs={}
        for position,((h,_,push),spi,load) in enumerate(zip(commands[g],e1s,heads,strict=True)):
            assert abs(spi["clock"]-push)<=1 and h[0]==load["op"]
            off=int.from_bytes(h[10:12],"little")
            seal=h[0]==3
            if not (seal or (h[1]==5 and off==1505)):continue
            ready,=[e for e in owner if e["event"]=="wire_ready648" and e["offset"]==off and e["op"]==h[0] and e["section"]==h[1]]
            seq=int.from_bytes(h[2:4],"little")
            head,=[e for e in owner if e["event"]=="wire_head648" and e["seq"]==seq]
            data=ready["last_descriptor_store"] if seal else table_bytes
            assert data<=ready["clock"]<=head["clock"]<=spi["start"]<push<=load["clock"]+1
            if not seal:
                assert not any(e["event"]=="table_store648" and table_bytes<e["clock"]<=push for e in owner)
            idx=load["index"]
            assert head["sent"]==idx-1
            # Four packet slots. In MMC643 SEAL separately waits for all the
            # earlier packets to retire. Report both predicates on both images.
            credit={}
            for label,needed in (("one_room",idx-4),("all_prior",idx-1)):
                actual=all_acks[needed-1]["clock"]
                record=status[bisect_left(status,(needed,0))][1]
                obs=next((e["clock"] for e in owner if e["event"]=="credit_observed648" and e["new_retired"]>=needed),None)
                assert actual<=record+1
                credit[label]=dict(cpu_ACK=elapsed(actual),E0_reply=elapsed(record),
                    ARM_counter=elapsed(obs) if obs is not None else None)
            required=credit["all_prior" if seal and mode=="base" else "one_room"]
            assert required["E0_reply"]<=elapsed(spi["start"])+0.001
            costs["seal" if seal else "table"]=dict(ready_data=elapsed(data),wire_request=elapsed(ready["clock"]),
                prior_E1_end_to_wire_request_ms=ms(ready["clock"]-commands[g][position-1][2]),
                transport_entry=elapsed(head["clock"]),credit=credit,cached_outstanding=head["sent"]-head["retired"],
                prior_unconsumed_at_SPI=sum(r["clock"]>spi["start"] for r in all_acks[:idx-1]),
                SPI_start=elapsed(spi["start"]),SPI_complete=elapsed(push),CPU_load=elapsed(load["clock"]),
                bytes=spi["bytes"],seq=seq)
        assert set(costs)=={"table","seal"}
        row=proof["rows"][g]
        incoming=[e for e in events if e.get("input_generation")==g]
        input_marks=dict(capture_ready=one(owner,"source_begin")["capture_ready"],
            first_D1=next(e["start"] for e in incoming if e.get("opcode")=="0xd1"),
            D3=next(e["clock"] for e in incoming if e.get("opcode")=="0xd3"),
            planner=one(owner,"planner_enter")["clock"])
        seal_rows=[r for r in cpu[g] if r["op"]==3]
        upload=one(seal_rows,"upload165_entry")
        first_wait=next((r for r in seal_rows if r["event"]=="wait169"),None)
        frames[g]=dict(events_ms_from_previous_display=costs,valid_plan_ms=elapsed(done["writes"]["valid"]),
            prepared_output_entry_ms=elapsed(output),interval_VB=row["interval_VB"],
            input_ms={k:elapsed(t) for k,t in input_marks.items()},input_pops_before_prior_ACK=row["pops_before_old_ACK"],
            SEAL_line=one(seal_rows,"load")["line"],upload_line=upload["line"],upload_start_ms=elapsed(upload["clock"]),
            first_wait_line=first_wait["line"] if first_wait else None,
            interval_ms=row["interval_ms"],display_frame=one(cpu[g],"reveal")["frame"],
            final_waits=row["final_waits"],line=row["line"])
    return dict(frames=frames,intervals=[proof["rows"][g]["interval_VB"] for g in range(951,956)],
        dense_VB=proof["dense_VB"],dense_ms=proof["dense_mean_ms"],last_ACK=proof["last_ACK"],
        line951=proof["rows"][951]["line"],wait957=proof["rows"][957]["final_waits"],
        measured=proof["measured"],pins={n:sha(folder/n) for n in ("events.json","joint.json","packets.jsonl","window.csv","seal528.csv")})


def analyze(a):
    phases={}
    for n in (1,2):
        golden=a.traces/f"nes-front638-both{n}h"
        b=measure(a.traces/f"nes-tail648-base{n}a",golden,"base")
        c=measure(a.traces/f"nes-tail648-packed{n}",golden,"packed")
        old=read(ROOT/"analysis/pad647-verification.json")["phases"][str(n)]["base"]
        assert b["last_ACK"]==old["last_ACK"] and b["intervals"]==old["intervals"]
        for key in ("parameters","client_SHA256"):
            assert b["measured"][key]==c["measured"][key]
        assert c["measured"]["firmware_SHA256"]==sha(a.build/"packed/src/obj-nes-100/firmware.stm")
        gates=dict(display955=c["frames"][955]["interval_VB"]==3 and c["frames"][955]["display_frame"]<b["frames"][955]["display_frame"],
            dense=c["dense_VB"]<b["dense_VB"] and c["dense_ms"]<b["dense_ms"],ACK=c["last_ACK"]<b["last_ACK"],
            control954=c["frames"][954]["interval_VB"]<=b["frames"][954]["interval_VB"],
            protected=c["line951"]<=246 and c["wait957"]==0 and c["intervals"][1]<=4)
        phases[n]=dict(base=b,candidate=c,gates=gates,passed=all(gates.values()),ACK_delta_ms=ms(c["last_ACK"]-b["last_ACK"]))
    guards={}
    fw=c["measured"]["firmware_SHA256"]
    for name in ("menu","overlap","seal","queue"):
        path=a.build/(name+".json")
        assert read(path)["firmware"]==fw
        guards[name]=sha(path)
    for fault in ("none","program","done","busy","token"):
        path=a.build/f"base-{fault}/result.json"
        v=read(path)
        assert v["passed"] and v["firmware_sha256"]==fw and v["safe_return"]==v["base_restored"]==int(fault=="none")
        guards["base_"+fault]=sha(path)
    return dict(phases=phases,guards=guards,board_test=read(a.rtl/"result.json"),
        flash_B=(a.build/"packed/src/obj-nes-100/firmware.stm").stat().st_size,
        scope="53 accepted inputs, linked ARM with CPI2 and modeled driver/SPI/ROM schedule, two post-boot start phases, real 65816 in Mesen. CPU doorbell is the logical credit boundary; E0 reply and ARM counter store are observed separately. Separate fitted RTL sources for queued SEAL/STOP. No physical trial.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("traces","build","rtl","out"):p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
