# SPDX-License-Identifier: MIT
"""Reconcile the 1100-byte fill with actual consumer ACKs, relative SEAL and display."""
import argparse
import json
from pathlib import Path
from analyze_nes_export636 import run as verify
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, ms, one, packets, read, sha


def padding(rows):
    rows=[r for r in rows if r["index"]==one(rows,"pad_header")["index"]]
    def time(event): return one(rows,event)["clock"]
    pieces={"load_and_header":time("pad_data")-time("load"),
            "section_checks_and_address":time("pad_generic548")-time("pad_data")}
    def clocks(event):return [r["clock"] for r in rows if r["event"]==event]
    chunk=clocks("zero_chunk516")
    if chunk:
        serviced=clocks("pad_post_service")
        launched=clocks("zero_dma")
        assert len(chunk)==len(serviced)==19 and len(launched)==18
        assert [r["value"] for r in rows if r["event"]=="zero_dma"]==[64]*17+[12]
        pieces.update(setup=chunk[0]-time("pad_generic548"),
            service=sum(y-x for x,y in zip(chunk,serviced,strict=True)),
            chunk_control=sum(y-x for x,y in zip(serviced[:-1],launched,strict=True)),
            DMA_and_loop_return=sum(y-x for x,y in zip(launched,chunk[1:],strict=True)),
            exit=time("pad_fill_receipt548")-serviced[-1])
    else:
        pieces.update(history_checks=time("pad_hit")-time("pad_generic548"),
                      hit_service_and_exit=time("pad_fill_receipt548")-time("pad_hit"))
        assert time("pad_hit")<time("fill_service545")<time("pad_fill_receipt548")
    pieces.update(receipt_to_accepted=time("pad_accepted")-time("pad_fill_receipt548"),
                  accepted_to_ACK=time("ack")-time("pad_accepted"))
    total=time("ack")-time("load")
    assert sum(pieces.values())==total and min(pieces.values())>=0
    return dict(total_ms=ms(total),parts_ms={k:ms(v) for k,v in pieces.items()},
                STOP_polls=len(clocks("fill_service545")),DMA_bytes=sum(r["value"] for r in rows if r["event"]=="zero_dma"),
                load=time("load"),ack=time("ack"))


def measure(folder,golden,mode):
    verified=verify(folder,golden)
    records=verified["rows"]
    cpu=csv_groups(folder/"window.csv")
    commands=packets(folder)
    originals=packets(golden)
    assert work(folder)==work(golden)
    assert commands.keys()==originals.keys()
    reordered=[]
    for g,cmds in commands.items():
        # Credit can reorder independent map, section and bulk packets. Only
        # the sequential head ordinal is rebound; keep bank, serial and token.
        trial,reference=([(h[:2]+h[4:],b) for h,b,t in q] for q in (cmds,originals[g]))
        assert sorted(trial)==sorted(reference)
        if trial!=reference:
            reordered.append(g)
    hits=[g for g in range(905,958) if any(r["event"]=="reuse647" for r in cpu[g])]
    assert hits==(list(range(907,958)) if mode=="reuse" else [])
    frames={}
    for g in (954,955):
        seal=[r for r in cpu[g] if r["op"]==3]
        previous=one([r for r in cpu[g-1] if r["op"]==3],"reveal")["clock"]
        r=records[g]
        fill=padding(cpu[g])
        # Split the interval after the padding ACK at actual head ownership
        # boundaries. A PUSH before the preceding ACK costs no extra idle time.
        after=[]
        previous_ack=fill["ack"]
        heads=[r for r in cpu[g] if r["event"]=="load"]
        for (h,_,push),head in zip(commands[g],heads,strict=True):
            if head["clock"]<=fill["ack"]:
                continue
            ack=one([r for r in cpu[g] if r["index"]==head["index"]],"ack")["clock"]
            assert previous_ack<=head["clock"] and push<=head["clock"]+1
            idle=max(0,push-previous_ack)
            after.append(dict(op=h[0],section=h[1],offset=int.from_bytes(h[10:12],"little"),
                wire_payload_B=len(h)-16,await_push_ms=ms(idle),
                head_poll_ms=ms(head["clock"]-previous_ack-idle),
                service_ms=ms(ack-head["clock"]) if h[0]!=3 else 0))
            previous_ack=ack
        assert after[-1]["op"]==3
        assert abs(sum(x[k] for x in after for k in ("await_push_ms","head_poll_ms","service_ms"))
                   -ms(one(seal,"load")["clock"]-fill["ack"]))<1e-8
        wake=one(seal,"wait_return_2999")
        wait=one([r for r in seal if r["clock"]<wake["clock"]],"wait169")
        assert wake["line"]==225
        frames[g]=dict(fill=fill,interval_VB=r["interval_VB"],interval_ms=r["interval_ms"],
            relative_SEAL_load_ms=ms(one(seal,"load")["clock"]-previous),
            relative_SEAL_push_ms=ms(commands[g][-1][2]-previous),
            relative_pad_load_ms=ms(fill["load"]-previous),
            pad_ACK_to_SEAL_load_ms=ms(one(seal,"load")["clock"]-fill["ack"]),
            after_pad=after,
            missed_upload_line225_ms=[ms(period-(wake["clock"]-wait["clock"])) for period in (262*1364-4,262*1364)],
            display_frame=one(seal,"reveal")["frame"],display_line=r["line"],final_waits=r["final_waits"])
    return dict(frames=frames, dense_ms=verified["dense_mean_ms"],dense_VB=verified["dense_VB"],
        intervals=[records[g]["interval_VB"] for g in range(951,956)],last_ACK=records[957]["ACK"],
        reordered_generations=reordered,
        wait957=records[957]["final_waits"],line951=records[951]["line"],bulk_slots=verified["measured"]["max_bulk_banks"],
        boot_ready=read(folder/"joint.json")["first_packet_poll_masterclock"],
        rendezvous_start=int((folder/"startup-clock.txt").read_text().split()[0]),warm_hits=len(hits),
        measured=verified["measured"],pins={n:sha(folder/n) for n in ("window.csv","events.json","packets.jsonl","joint.json","seal528.csv")})


def analyze(a):
    phases={}
    pkg=read(ROOT/"analysis/reject643-package.json")
    for n in (1,2):
        golden=a.traces/f"nes-front638-both{n}h"
        cases={m:measure(a.traces/f"nes-pad647-{m}{n}",golden,m) for m in ("base","reuse")}
        b,c=cases["base"],cases["reuse"]
        old=read(ROOT/"analysis/tail646-verification.json")["phases"][str(n)]["base"]
        assert b["last_ACK"]==old["last_ACK"] and b["intervals"]==old["dense_intervals"]
        assert b["measured"]["parameters"]==c["measured"]["parameters"]
        assert max(b["boot_ready"],c["boot_ready"])<=c["measured"]["parameters"]["start"]
        assert b["measured"]["client_SHA256"]==pkg["ROM_read"]["client"] and c["measured"]["client_SHA256"]==sha(a.client/"sink165.sfc")
        assert b["measured"]["firmware_SHA256"]==c["measured"]["firmware_SHA256"]==pkg["firmware_SHA256"]
        bc=b["frames"][955];cc=c["frames"][955]
        gates=dict(SEAL=cc["relative_SEAL_load_ms"]<bc["relative_SEAL_load_ms"],
            display_955=cc["interval_VB"]==3 and cc["display_frame"]<bc["display_frame"],
            control_954=c["frames"][954]["interval_VB"]<=b["frames"][954]["interval_VB"],
            dense=c["dense_VB"]<b["dense_VB"] and c["dense_ms"]<b["dense_ms"],
            last_ACK=c["last_ACK"]<b["last_ACK"],protected=c["line951"]<=246 and c["intervals"][1]<=4 and c["wait957"]==0)
        phases[n]=dict(**cases,gates=gates,passed=all(gates.values()),last_ACK_delta_ms=ms(c["last_ACK"]-b["last_ACK"]))
    recovery=read(a.recovery/"result.json")
    assert recovery["SOF"]==pkg["board"]["SHA"]["board.sof"] and recovery["healthy_release_and_STOP"]==[32,97]
    assert all(sha(a.board/n)==h for n,h in recovery["rtl"].items())
    assert all(sha(a.recovery/(n+".log"))==h for n,h in recovery["logs"].items())
    menu=read(a.checks/"menu.json")
    assert menu["firmware"]==pkg["firmware_SHA256"] and menu["rows"]["normal"]["released"]==1
    for fault in ("none","program","done","busy","token"):
        result=read(a.checks/f"base-{fault}/result.json")
        assert result["passed"] and result["firmware_sha256"]==pkg["firmware_SHA256"]
        assert result["safe_return"]==result["base_restored"]==int(fault=="none")
    return dict(phases=phases,guards=read(a.guards/"guards.json"),ROM=read(a.client/"build.json"),
        extra_history_WRAM_B=10,unchanged_ARM_Flash_B=pkg["Flash_B"],
        reused_empty_capture_proof=sha(a.recovery/"result.json"),reused_menu_proof=sha(a.checks/"menu.json"),
        scope="Two post-boot starts in linked ARM (CPI2)/Mesen with modeled shared SPI/ROM and two staging slots. Independent 53-frame byte/image/receipt checks. Separate injected CPU STOP and cold restart; previously exercised identical FPGA capture RTL and ARM menu/base paths. No physical candidate run.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("traces","client","recovery","board","checks","guards","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
