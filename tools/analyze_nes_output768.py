# SPDX-License-Identifier: MIT
"""Reconcile timed hardware bins and linked, same-work A/B output ownership."""
import argparse
import hashlib
import json
from bisect import bisect_left
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

from analyze_nes_hardware663 import work
from analyze_nes_supply485_hardware import fields
from analyze_nes_output531 import csv_groups, one, waits
from analyze_nes_phase537 import ms
from check_nes_game478 import Machine

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(n):
    archive, suffix = (("physical-selection.zip","763-2회차_성공") if n == 763 else
                       ("mmc767-physical.zip","767"))
    with ZipFile(PROBES / "nes-timer767" / archive) as z:
        budget = fields(z.read(f"nes-budget-mmc{suffix}.txt").decode())
        game = fields(z.read(f"nes-game-last-mmc{suffix}.txt").decode())
    assert budget.get("epoch_tick","0") == "0" and budget["tick_ms"] == "10"
    assert game["candidate"] == f"NES-MMC{n}"
    assert all(game[k] == "1" for k in ("verified", "stop_ok", "base_restored", "safe_to_reload"))
    assert budget["cost_phase_and_op_are_nested"] == "1"
    assert budget["cost_clock_hz"] == "84000000"
    row = work(budget)[0][5]
    frames = row["frames"]
    per = {k:v/frames for k,v in row.items() if k not in ("frames", "maxgap")}
    sample = int(game["native_frames"])
    polls = {}
    for i, name in enumerate(("credit","drain","final_ACK")):
        calls, progress, quiet, hi, lo, _ = map(int,budget[f"cost_poll_{i}"].split(","))
        polls[name] = dict(calls=calls/sample, quiet=quiet/sample,
                           quiet_ms=((hi << 32)+lo)/84000/sample)
    usable = {}
    for name, i in (("e0",4),("e8",6)):
        calls, wire, hi, lo, _ = map(int,budget[f"cost_op_{i:02}"].split(","))
        assert wire == 20*calls
        usable[name] = per[name]/20*((hi << 32)+lo)/84000/calls
    return dict(frames=frames, per_frame=per, output_ms=per["seal"]*10,
                query_ms_estimate=usable, whole_run_poll_per_frame=polls,
                archive_sha256=sha(PROBES/"nes-timer767"/archive))


def workload(folder, gen, descriptor):
    current = (folder/f"map-{gen}.bin").read_bytes()
    previous = (folder/f"map-{gen-1}.bin").read_bytes()
    assert len(current) == len(previous) == 4096
    return dict(map_groups=sum(current[j:j+64]!=previous[j:j+64] for j in range(0,4096,64)),
                obj=int.from_bytes(descriptor[18:20],"little")//32,
                bg=int.from_bytes(descriptor[16:18],"little")//16)


def span(lo, hi, a, b):
    return max(0, min(hi,b)-max(lo,a))


def timeline(folder, gen, cpu, events, packets):
    ev = [r for r in events if r["generation"] == gen]
    begin = one(ev,"output_enter531")["clock"]
    end = one(ev,"output_return531")["clock"]
    commands = [r for r in ev if r.get("opcode") == "0xe1"]
    rows = cpu[gen]
    loads = [r for r in rows if r["event"] == "load"]
    acks = [r for r in rows if r["event"] == "ack"]
    assert len(commands) == len(loads) == len(acks)
    seal = [r for r in rows if r["op"] == 3]
    issue = commands[-1]["start"]
    push = commands[-1]["clock"]
    head = one(seal,"load")["clock"]
    ack = one(seal,"ack")["clock"]
    final = one(seal,"final212")["clock"]
    assert begin <= issue <= push <= head <= final <= ack <= end
    blank = waits(seal)
    pre = sum(b-a for a,b in blank if a<final)
    post = sum(b-a for a,b in blank if a>=final)
    starts = [r for r in seal if r["event"] == "ppu_dma"]
    lasts = [r for r in seal if r["event"] == "ppu_last"]
    dma = sum(b["clock"]-a["clock"] for a,b in zip(starts,lasts,strict=True))
    assert all(not span(a,b,x["clock"],y["clock"]) for a,b in blank for x,y in zip(starts,lasts))
    # At saturation, distinguish a physical slot being busy from its checked
    # retirement not yet visible on the host. These intervals may hide CPU work.
    status = [r for r in ev if r.get("opcode") == "0xe0"]
    times = [r["clock"] for r in status]
    retired = [int.from_bytes(bytes.fromhex(r["reply"])[5:7],"big") for r in status]
    assert retired == sorted(retired)
    publications = [r for r in ev if r["event"] == "credit673"]
    confirmed = [r["after"] for r in publications]
    assert confirmed == sorted(confirmed)
    full = invisible = 0
    for prev, cur in zip(loads, loads[1:]):
        k = prev["index"]
        a = packets[k-1][1]
        b = commands[cur["index"]-loads[0]["index"]]["start"]
        required = k-3
        if required < loads[0]["index"]:
            continue
        j = bisect_left(retired, required)
        assert j < len(times) and times[j] <= b+1
        seen = times[j]
        if publications:
            h = bisect_left(confirmed, required)
            assert h < len(confirmed) and seen <= publications[h]["clock"]+1
            seen = publications[h]["clock"]
            assert seen <= b+1
        actual = acks[required-loads[0]["index"]]["clock"]
        assert actual <= times[j]+1
        full += span(begin,issue,a,min(b,actual))
        invisible += span(max(begin,a),min(issue,b),actual,seen)
    pre_issue = issue-begin
    assert full+invisible <= pre_issue+1
    check = one(seal,"upload165_entry")["clock"]-head
    control = ack-head-check-dma-pre-post
    terms = dict(before_SEAL_except_saturation=pre_issue-full-invisible,
                 four_slots_busy=full, retired_before_credit_observed=invisible,
                 SEAL_SPI=push-issue, pushed_to_65816_load=head-push,
                 SEAL_validation=check, post_SEAL_DMA_active=dma,
                 upload_VBlank=pre, final_VBlank=post, setup_and_display=control,
                 final_ACK_to_ARM=end-ack)
    assert min(terms.values()) >= 0 and abs(sum(terms.values())-(end-begin))<1e-5
    # Auxiliary clocks overlap the partition; the 719 loop contains SPI/credit
    # and is not correctly measured by summing wait callbacks alone.
    borrows = [r for r in ev if r["event"]=="idle676_return" and begin<=r["begin"]<r["clock"]<=issue]
    packet_detail = []
    for send, load, ret in zip(commands,loads,acks,strict=True):
        _,arrival,raw,_ = packets[load["index"]-1]
        hdr = bytes.fromhex(raw)
        assert abs(arrival-send["clock"])<=1 and hdr[0]==load["op"] and hdr[1]==load["section"]
        assert arrival<=load["clock"]<=ret["clock"]
        packet_detail.append(dict(op=hdr[0],section=hdr[1],offset=int.from_bytes(hdr[10:12],"little"),
                                  bytes=send["bytes"], issue_ms=ms(send["start"]-begin),
                                  snes_load_ms=ms(load["clock"]-begin), retire_ms=ms(ret["clock"]-begin)))
    reveal = one(seal,"reveal")
    previous = one([r for r in cpu[gen-1] if r["op"]==3],"reveal")
    wire = {}
    for op in sorted({r["opcode"] for r in ev if r["event"] == "SPI" and span(begin,issue,r["start"],r["clock"])}):
        wire[op]=ms(sum(span(begin,issue,r["start"],r["clock"]) for r in ev if r["event"] == "SPI" and r["opcode"]==op))
    before_cpu = ms(pre_issue)-sum(wire.values())
    assert before_cpu >= 0
    early_dma = [r for r in rows if r["event"] == "ppu_dma" and begin <= r["clock"] < head]
    return dict(work=workload(folder,gen,hdr), output_ms=ms(end-begin),
                terms_ms={k:ms(v) for k,v in terms.items()}, before_SEAL_ms=ms(pre_issue),
                credit_scope="within-generation subsequent E1 only; elapsed exposure, not removable stall",
                credit_endpoint="ARM validated counter store" if publications else "end of E0 response",
                e1_bytes=sum(r["bytes"] for r in commands),
                non_SPI_before_SEAL_ms=before_cpu, dma_bytes_output_entry_to_SEAL_load=sum(r["value"] for r in early_dma),
                wire_before_SEAL_ms=wire, idle_callbacks=len(borrows),
                idle_callback_ms=ms(sum(r["clock"]-r["begin"] for r in borrows)),
                post_SEAL_DMA_bytes=sum(r["value"] for r in starts),
                final_waits=sum(a>=final for a,_ in blank), display_interval_VB=reveal["frame"]-previous["frame"],
                reveal_clock=reveal["clock"], reveal_line=reveal["line"], final_ACK=ack, final_ACK_line=one(seal,"ack")["line"], post_SEAL_load_line=one(seal,"load")["line"],
                packets=packet_detail, omit_events=[r["clock"] for r in ev if r["event"]=="omit_optional_wait768"])


def run(temp, report):
    result = dict(scope="b05 physical bin 25..30 s, one successful run per build; 969 matched map deltas/OBJ extent only; linked ARM and 65816 with modeled CPI, SPI overhead, IRQ and ROM calendar",
                  physical={n:physical(n) for n in (763,767)}, phases={})
    sender = temp / "nes-output768-sender"
    result["source"] = {name:sha(sender/name) for name in ("nes_geometry_sender653.sv", "sender.json", "joint-sender.json", "tb.sv")}
    result["cache_sha256"] = sha(PROBES/"nes-output768-inputs/obj-cache.json")
    capture = PROBES / "nes-output489/audit01"
    captured_arm = PROBES / "nes-output489/ARM01/src"
    assert sha(captured_arm/"obj-nes-100/firmware.stm") == read(capture/"result.json")["firmware_SHA256"]
    layout = Machine(captured_arm,bytes(128)).layout["nes_native_video165"]
    matched_counts = {}
    for gen in (961,967,969):
        raw = (capture/f"frame{gen}/video-before.bin").read_bytes()
        assert len(raw) == layout["size"]
        def field(name, width):
            offset = layout[name]
            return int.from_bytes(raw[offset:offset+width],"little")
        matched_counts[gen] = dict(map_groups=field("map_dirty",8).bit_count(),
                                    obj=field("obj_count",2), bg=field("bg_count",2))
    result["captured_planner"] = matched_counts
    pin763 = read(ROOT/"analysis/trial763-package.json")["variants"]["763"]
    rom767 = read(ROOT/"analysis/trial763-package.json")["variants"]["765"]["ROM_SHA256"]
    pin767 = read(ROOT/"analysis/trial767-package.json")
    for phase in (1,2):
        comparisons = {}
        for mode, name in (("A",f"763-p{phase}-ext"),("B",f"767-p{phase}-ext"),("omit",f"767-p{phase}-omit")):
            d = temp/f"nes-cost768-{name}"
            j = read(d/"joint.json")
            assert j["commits"]==j["map_WRAM_VRAM_verified"]==66 and j["passed"]
            assert j["firmware_SHA256"]==(pin763["firmware"] if mode=="A" else pin767["firmware"])
            assert j["client_SHA256"]==(pin763["ROM_SHA256"] if mode=="A" else rom767)
            assert j["parameters"]["start"]==7288416+(phase-1)*178684
            reference=temp/f"nes-cost768-763-p{phase}-ext"
            for gen in range(905,971):
                for pattern in ("map-{}.bin","frame-{}.rgb","expected-{}.bin"):
                    assert (reference/pattern.format(gen)).read_bytes()==(d/pattern.format(gen)).read_bytes()
            cpu=csv_groups(d/"window.csv")
            events=read(d/"events.json")
            packets=[json.loads(line) for line in (d/"packets.jsonl").read_text().splitlines()]
            elffile = PROBES / ("nes-trial763/linked763/src" if mode == "A" else "nes-timer767/arm/src") / "obj-nes-100/sd2snes.elf"
            assert sha(elffile) == (pin763["ELF"] if mode == "A" else pin767["ELF"])
            selected=timeline(d,969,cpu,events,packets)
            cohort = {}
            for gen in range(958, 971):
                row = timeline(d,gen,cpu,events,packets)
                cohort[gen] = {k:row[k] for k in ("work", "output_ms", "terms_ms", "display_interval_VB", "post_SEAL_DMA_bytes", "final_waits")}
            warm_output = []
            for gen in range(907, 971):
                generation_events = [r for r in events if r["generation"] == gen]
                start = one(generation_events, "output_enter531")["clock"]
                finish = one(generation_events, "output_return531")["clock"]
                warm_output.append(ms(finish-start))
            for gen, counts in matched_counts.items():
                assert cohort[gen]["work"] == counts
            prefix=[r["ACK_masterclock"] for r in j["frames"] if r["generation"]<969]
            if mode=="B":
                before=prefix
            elif mode=="omit":
                assert prefix==before
            comparisons[mode]=dict(frame969=selected, extended=cohort, warm_output_mean_ms=mean(warm_output), final970=j["frames"][-1]["ACK_masterclock"],
                                    firmware_sha256=j["firmware_SHA256"], client_sha256=j["client_SHA256"], elf_sha256=sha(elffile),
                                    inputs={p:sha(d/p) for p in ("joint.json","events.json","window.csv","packets.jsonl","seal528.csv")},
                                    parameters=j["parameters"], prefix_ACK_through_968=prefix[-1])
        assert comparisons["A"]["parameters"] == comparisons["B"]["parameters"] == comparisons["omit"]["parameters"]
        assert comparisons["A"]["frame969"]["work"]==comparisons["B"]["frame969"]["work"]
        result["phases"][phase]=comparisons
    # Secondary sensitivity: 961 and 967 bracket the hardware map count and
    # also match the average number of issued OBJ tile jobs more closely.
    target = mean(result["physical"][n]["per_frame"]["mapdirty"] for n in (763,767))
    for comparisons in result["phases"].values():
        for comp in comparisons.values():
            left, right = (comp["extended"][g] for g in (961,967))
            assert left["work"]["map_groups"] == 0 and right["work"]["map_groups"] == 24
            weight = target / 24
            def mix(a,b):
                return a*(1-weight) + b*weight
            jobs = []
            for g in (961,967):
                plans = read(PROBES/f"nes-output768-inputs/plans/frame{g}/plans.json")
                jobs.append(sum(bytes.fromhex(q)[6] == 1 for _,q in plans))
            comp["two_scene_sensitivity"] = dict(generations=[961,967], weight967=weight,
                map_groups=target, obj_extent=mix(left["work"]["obj"],right["work"]["obj"]),
                obj_jobs=mix(*jobs), output_ms=mix(left["output_ms"],right["output_ms"]),
                terms_ms={k:mix(v,right["terms_ms"][k]) for k,v in left["terms_ms"].items()})
    for phase, variants in result["phases"].items():
        assert len(variants["omit"]["frame969"]["omit_events"]) == 1
        assert not variants["A"]["frame969"]["omit_events"] and not variants["B"]["frame969"]["omit_events"]
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("report",type=Path)
    a=p.parse_args()
    run(a.temp,a.report)
