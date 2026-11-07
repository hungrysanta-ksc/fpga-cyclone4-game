"""Cost seven blocks against the actual 648 SEAL start and final display ACK."""
import argparse
import json
import math
from hashlib import sha256
from pathlib import Path
from analyze_nes_export636 import run as verify
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, ms, one, read, sha
from nes_geometry650 import encode,legacy

MODES=("base","packed","sealed","once")


def split(folder,expected):
    events=read(folder/"events.json")
    window=csv_groups(folder/"window.csv")
    inputs=[e for e in events if e.get("input_generation")==955]
    d1=[e for e in inputs if e.get("opcode")=="0xd1"][:7]
    d2=[e for e in inputs if e.get("opcode")=="0xd2"][:7]
    setup=max((e for e in inputs if e.get("opcode")=="0xd0" and e["clock"]<=d1[0]["start"]),key=lambda e:e["clock"])
    blocks=[]
    for index,(r,p,payload) in enumerate(zip(d1,d2,expected[:7],strict=True)):
        confirm=next(e for e in inputs if e.get("opcode")=="0xd0" and e["start"]>=p["clock"])
        start=setup["start"] if index==0 else r["start"]
        end=confirm["clock"]
        marks={e["part"]:e for e in inputs if e["event"]=="block650" and e["index"]==index}
        crc,decode=marks["wire_crc"],marks["restore"]
        assert r["bytes"]==3+len(payload) and p["bytes"]==confirm["bytes"]==8
        assert start<=r["start"]<r["clock"]<=crc["start"]<crc["clock"]<=decode["start"]<decode["clock"]<=p["start"]<p["clock"]<=confirm["start"]<end
        envelope=[e for e in events if e["event"]=="SPI" and start<=e["start"]<end]
        assert envelope==([setup] if index==0 else [])+[r,p,confirm]
        parts={k:ms(x["clock"]-x["start"]) for k,x in (("D1",r),("D2",p),("confirm_D0",confirm),("wire_CRC",crc),("restore",decode))}
        parts["initial_D0"]=ms(setup["clock"]-setup["start"]) if index==0 else 0.
        parts["other_between"]=ms(end-start)-sum(parts.values())
        assert parts["other_between"]>=0
        blocks.append(dict(index=index,payload_B=len(payload),cost_ms=parts,envelope_ms=ms(end-start),
            wire_only_D1_ms=r["bytes"]*8000/2625000,restore_ops=decode["ops"],CRC_ops=crc["ops"],
            start=start,D1_start=r["start"],confirm=end))
    cpu=window[954]
    ack=one([r for r in cpu if r["op"]==3],"ack")["clock"]
    prev=one(window[953],"reveal")["clock"]
    owner=[e for e in events if e["generation"]==954]
    seal=next(e for e in owner if e.get("packet_opcode")==3)
    capture=one([e for e in events if e["generation"]==955],"source_begin")["capture_ready"]
    closed=next(e["clock"] for e in owner if e.get("opcode")=="0xe8" and bytes.fromhex(e["reply"])[3]&2)
    assert blocks[0]["start"]>=capture
    target=[r for r in window[955] if r["op"]==3]
    origin=one(window[954],"reveal")["clock"]
    marks={"D3":next(e["clock"] for e in inputs if e.get("opcode")=="0xd3"),
           "planner":one([e for e in events if e["generation"]==955],"planner_enter")["clock"],
           "SEAL_load":one(target,"load")["clock"],"upload":one(target,"upload165_entry")["clock"],
           "display":one(target,"reveal")["clock"]}
    return dict(blocks=blocks,parts_ms={k:sum(b["cost_ms"][k] for b in blocks) for k in blocks[0]["cost_ms"]},
        active_ms=sum(b["envelope_ms"] for b in blocks),elapsed_ms=ms(blocks[-1]["confirm"]-blocks[0]["start"]),
        D1_wire_only_ms=sum(b["wire_only_D1_ms"] for b in blocks),
        confirmed_pre_ACK=sum(b["confirm"]<=ack for b in blocks),confirmed_pre_SEAL=sum(b["confirm"]<=seal["start"] for b in blocks),
        SEAL_start=seal["start"],SEAL_end=seal["clock"],prior_display=prev,old_ACK=ack,ready=max(capture,closed),
        SEAL_from_953_ms=ms(seal["start"]-prev),wire_payload_B=sum(b["payload_B"] for b in blocks),
        frame955_from_954_display_ms={k:ms(t-origin) for k,t in marks.items()},
        frame955_beam={k:(one(target,k)["frame"],one(target,k)["line"]) for k in ("load","upload165_entry","reveal")})


def frozen(folder,cost):
    # Preserve all non-input SPI timestamps, including the entire SEAL. Every
    # open gap still contains real MCU work: using all of it is optimistic.
    tx=[e for e in read(folder/"events.json") if e["event"]=="SPI" and e["generation"]==954 and
        e["opcode"] not in ("0xd0","0xd1","0xd2","0xd3")]
    def gaps(lo,hi):
        free=[];at=lo
        for e in tx:
            start=max(e["start"],lo);end=min(e["clock"],hi)
            if end<=start:continue
            assert start>=at-1
            if at<start:free.append(ms(start-at))
            at=end
        if at<hi:free.append(ms(hi-at))
        return free
    return dict(pre=gaps(cost["ready"],cost["SEAL_start"]),post=gaps(cost["SEAL_end"],cost["old_ACK"]))


def fit(gaps,lengths,fixed=None):
    fixed=fixed if fixed is not None else [0.]*len(lengths)
    def capacity(scale):
        i=0
        for gap in gaps:
            while i<len(lengths) and fixed[i]+lengths[i]*scale<=gap+1e-12:
                gap-=fixed[i]+lengths[i]*scale;i+=1
        return i
    lo=0.;hi=1.
    for _ in range(48):
        mid=(lo+hi)/2
        if capacity(mid)==len(lengths):lo=mid
        else:hi=mid
    return dict(fit_count=capacity(1),zero_variable_cost_count=capacity(0),
                additional_uniform_reduction_pct=100*(1-lo) if capacity(0)==len(lengths) else None)


def analyze(a):
    geometry=(a.data/"frame955.geometry").read_bytes();raw=(a.data/"frame955.raw").read_bytes()
    pkts=[enc(geometry,raw,955)[0] for enc in (legacy,encode)]
    previous=read(ROOT/"analysis/receive649-verification.json")["phases"]
    phases={};guards={}
    for n in (1,2):
        golden=a.traces/f"nes-front638-both{n}h";cases={}
        base_folder=a.traces/f"nes-geometry650-base{n}"
        mmc=previous[str(n)]["MMC643"]
        for mode in MODES:
            folder=a.traces/(f"nes-geometry650-{mode}{n}"+("" if mode=="base" else "wire"))
            ver=verify(folder,golden)
            assert work(folder)==work(golden)
            reference=previous[str(n)]["648"]
            assert all(ver["measured"][k]==reference["schedule"][k] for k in ("parameters","client_SHA256"))
            v=split(folder,pkts[mode!="base"])
            count=read(a.build/f"count-{mode}.json")
            assert count["firmware"]==ver["measured"]["firmware_SHA256"]
            # These instructions execute outside each measured first-SPI to
            # confirm-D0 envelope. Charge the linked poll's work at CPI 2,
            # without inventing an overlapping IRQ or outer driver cost.
            ticks_per_op_ms=1000*ver["measured"]["parameters"]["CPI"]/84000000
            for block,edge in zip(v["blocks"],count["blocks"],strict=True):
                block["pre_poll_SPI_ms"]=edge["before_first_SPI_ops"]*ticks_per_op_ms
                block["post_D0_verify_ms"]=edge["after_confirm_D0_ops"]*ticks_per_op_ms
            v["pre_SPI_ms"]=sum(b["pre_poll_SPI_ms"] for b in v["blocks"])
            v["post_D0_verify_ms"]=sum(b["post_D0_verify_ms"] for b in v["blocks"])
            v["charged_ms"]=v["active_ms"]+v["pre_SPI_ms"]+v["post_D0_verify_ms"]
            v["seventh_D0_margin_to_ACK_ms"]=ms(v["old_ACK"]-v["blocks"][-1]["confirm"])
            if mode=="base":
                base=v
                assert ver["last_ACK"]==reference["last_ACK"] and ver["measured"]["firmware_SHA256"]==reference["schedule"]["firmware_SHA256"]
                gaps=frozen(folder,v)
            lengths=[b["envelope_ms"]+b["pre_poll_SPI_ms"]+b["post_D0_verify_ms"] for b in v["blocks"]]
            payload_ms=[b["payload_B"]*8000/2625000 for b in v["blocks"]]
            free=sum(gaps["pre"])+sum(gaps["post"])
            need=v["charged_ms"]-free
            r=ver["rows"];intervals=[r[g]["interval_VB"] for g in range(951,956)]
            gates=dict(SEAL_absolute=v["SEAL_start"]<=base["SEAL_start"],
                SEAL_relative=v["SEAL_from_953_ms"]<=base["SEAL_from_953_ms"],seven=v["confirmed_pre_ACK"]==7,
                display=intervals[3:]==[3,3],protected=r[951]["line"]<=246 and r[957]["final_waits"]==0,
                dense=ver["dense_VB"]<mmc["dense_VB"] and ver["dense_mean_ms"]<mmc["dense_ms"],last=ver["last_ACK"]<mmc["last_ACK"])
            control=None
            if mode!="base":
                # Same candidate binary, but fed the original packets by the
                # schedule's old default packetizer. Keep as a binary control.
                old=a.traces/f"nes-geometry650-{mode}{n}"
                checked=verify(old,golden)
                assert all(checked["measured"][k]==ver["measured"][k]
                           for k in ("firmware_SHA256","client_SHA256","parameters"))
                assert work(old)==work(folder)
                original=split(old,pkts[0])
                control=dict(intervals=[checked["rows"][g]["interval_VB"] for g in range(951,956)],
                    last=checked["last_ACK"],wire_payload_B=original["wire_payload_B"],
                    active_ms=original["active_ms"],pins=checked["pins"])
            cases[mode]=dict(cost=v,additional_active_reduction_ms=max(0,need),pooled_slack_ms=-need,
                pooled_byte_equivalent_if_only_payload_changes=math.ceil(max(0,need)*2625000/8000),
                fit_by_payload_only=fit(gaps["pre"]+gaps["post"],payload_ms,[a-b for a,b in zip(lengths,payload_ms,strict=True)]),
                fit_in_frozen_gaps=fit(gaps["pre"]+gaps["post"],lengths),
                pre_SEAL_only_reduction_ms=max(0,v["charged_ms"]-sum(gaps["pre"])),
                pre_SEAL_fit_count=fit(gaps["pre"],lengths)["fit_count"],
                minimum_pre_SEAL_polls=next(i for i in range(8) if sum(lengths[i:])<=sum(gaps["post"])),
                SEAL_relative_delta_ms=v["SEAL_from_953_ms"]-base["SEAL_from_953_ms"],
                SEAL_absolute_delta_ms=ms(v["SEAL_start"]-base["SEAL_start"]),intervals=intervals,line951=r[951]["line"],
                wait955=r[955]["final_waits"],wait957=r[957]["final_waits"],dense_VB=ver["dense_VB"],dense_ms=ver["dense_mean_ms"],last=ver["last_ACK"],
                last_vs_MMC643_ms=ms(ver["last_ACK"]-mmc["last_ACK"]),gates=gates,time_pass=all(gates.values()),
                firmware=ver["measured"]["firmware_SHA256"],same_binary_legacy_control=control,
                pins={k:sha(folder/k) for k in ("events.json","joint.json","window.csv","packets.jsonl","seal528.csv")})
        phases[n]=dict(cases=cases,gaps_ms=gaps,MMC643={k:mmc[k] for k in ("intervals","line951","wait957","dense_ms","dense_VB","last_ACK")})
    for mode in MODES[1:]:
        folder=a.build/mode
        firmware=folder/"src/obj-nes-100/firmware.stm";fw=sha(firmware)
        assert all(p["cases"][mode]["firmware"]==fw for p in phases.values())
        pins={}
        for name in ("geometry","queue","menu","seal"):
            path=folder/(name+".json");assert read(path)["firmware"]==fw;pins[name]=sha(path)
        for reason in ("none","token","program","done","busy"):
            path=folder/f"base-{reason}/result.json";v=read(path)
            assert v["passed"] and v["firmware_sha256"]==fw and v["safe_return"]==v["base_restored"]==int(reason=="none")
            pins[reason]=sha(path)
        guards[mode]=dict(flash_B=firmware.stat().st_size,firmware=fw,pins=pins)
    return dict(phases=phases,guards=guards,source955=sha256(geometry).hexdigest(),
        first_seven_SHA256={label:[sha256(b).hexdigest() for b in blocks[:7]]
                            for label,blocks in zip(("original","compact"),pkts,strict=True)},
        scope="53 linked ARM/Mesen frames per run; read-only function clocks, modeled SPI/ROM and CPI2. Seven unchanged tokens, per-block independent extent, wire and decoded CRC. Producer reference generates packets without charging FPGA encode latency; no new board fit or hardware FPS.")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("traces","build","data","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
