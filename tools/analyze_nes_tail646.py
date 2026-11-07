"""Reconcile linked ARM memory-write clocks, actual transfers and the paired SNES display outcome."""
import argparse
import json
from pathlib import Path
from analyze_nes_export636 import run as verify_outputs
from analyze_nes_map617 import partition
from analyze_nes_oam618 import work
from analyze_nes_output615 import ROOT, csv_groups, one, packets, read, ms, sha


def measure(folder, golden, src):
    verified=verify_outputs(folder,golden)
    joint=verified["measured"]
    assert joint["firmware_SHA256"]==sha(src/"obj-nes-100/firmware.stm")
    assert joint["client_SHA256"]==read(ROOT/"analysis/reject643-package.json")["ROM_read"]["client"]
    assert work(folder)==work(golden)  # Including all expanded section-5 addresses, bytes, and display manifests.
    cpu=csv_groups(folder/"window.csv")
    commands=packets(folder)
    events=read(folder/"events.json")
    split=partition(folder)
    frames={}
    for g in (954,955):
        own=[e for e in events if e["generation"]==g]
        spi=[e for e in own if e["event"]=="SPI"]
        pubs=[e for e in spi if e["opcode"]=="0xe1"]
        oam,=[e for e in pubs if e["packet_opcode"]==9]
        origin=one(own,"planner_enter")["clock"]
        marked=one(own,"last_writes646")
        end=one(own,"end_enter")["clock"]
        out=one(own,"output_enter531")["clock"]
        stamps=marked["writes"]
        assert all(origin<=t<=end+1 for t in stamps.values()) and max(stamps.values())==stamps["valid"]
        assert abs(marked["clock"]-end)<=1 and end<=oam["start"]
        s=[r for r in cpu[g] if r["op"]==3]
        prev=one([r for r in cpu[g-1] if r["op"]==3],"reveal")
        reveal=one(s,"reveal")
        ack=one(s,"ack")
        i,=[i for i,(h,_,_) in enumerate(commands[g]) if h[0]==9]
        last=max(i for i,(h,_,_) in enumerate(commands[g]) if h[0]==7 or h[1]==2)
        oam_load=one([r for r in cpu[g] if r["op"]==9],"load")
        data=[(h,t) for h,_,t in commands[g] if h[1]==5]
        data_e1s=[e for e in pubs if any(abs(t-e["clock"])<=1 for _,t in data)]
        assert len(data_e1s)==len(data)
        data_heads=sorted({r["index"] for r in cpu[g] if r["section"]==5})
        service=[]
        for (h,_),idx in zip(data,data_heads,strict=True):
            head=[r for r in cpu[g] if r["index"]==idx]
            load=one(head,"load")
            assert load["op"]==h[0]
            service.append(dict(op=h[0],offset=int.from_bytes(h[10:12],"little"),
                payload=len(h)-16,expanded=int.from_bytes(h[14:16],"little") or len(h)-16,
                load_to_ACK_ms=ms(one(head,"ack")["clock"]-load["clock"])))
        wait=split[g]
        frames[g]=dict(
            writes_from_planner_ms={k:ms(v-origin) for k,v in stamps.items()},
            writes_before_END_ms={k:ms(end-v) for k,v in stamps.items()},
            planner_to_END_ms=ms(end-origin), from_previous_display_ms={
                "planner":ms(origin-prev["clock"]),"END":ms(end-prev["clock"]),
                "output_enter":ms(out-prev["clock"]),"OAM_start":ms(oam["start"]-prev["clock"]),
                "OAM_load":ms(oam_load["clock"]-prev["clock"]),
                "last_map_or_bulk_push":ms(commands[g][last][2]-prev["clock"]),
                "first_section5_E1":ms(data_e1s[0]["start"]-prev["clock"]),
                "last_section5_push":ms(data[-1][1]-prev["clock"]),
                "SEAL_load":ms(one(s,"load")["clock"]-prev["clock"]),"reveal":ms(reveal["clock"]-prev["clock"])},
            OAM_E1_ms=ms(oam["clock"]-oam["start"]), OAM_before_output=oam["clock"]<out,
            OAM_before_last_work=i<last, OAM_count=1,
            END_entry_to_OAM_start_ms=ms(oam["start"]-end),
            OAM_push_minus_last_map_or_bulk_ms=ms(commands[g][i][2]-commands[g][last][2]),
            section5_E1_B=sum(e["bytes"] for e in data_e1s),section5_packets=len(data),
            section5_E1_ms=sum(ms(e["clock"]-e["start"]) for e in data_e1s),
            section5_service=service,
            all_owner_SPI_B=sum(e["bytes"] for e in spi),
            seal_line=one(s,"load")["line"],interval=reveal["frame"]-prev["frame"],
            absolute_display_frame=reveal["frame"],display_clock=reveal["clock"],ACK=ack["clock"],
            upload_wait_ms=wait["serviced_VBlank_wait_ms"]-wait["final_wait_ms"],
            final_waits=wait["final_wait_count"])
    return dict(frames=frames, dense_intervals=[verified["rows"][g]["interval_VB"] for g in range(951,956)],
                dense_VB=verified["dense_VB"],dense_mean_ms=verified["dense_mean_ms"],
                last_ACK=verified["rows"][957]["ACK"],wait957=verified["rows"][957]["final_waits"],
                line951=verified["rows"][951]["line"],max_bulk_banks=joint["max_bulk_banks"],
                wire_B=joint["wire_B"],firmware=joint["firmware_SHA256"],client=joint["client_SHA256"],
                IRQ=joint["SysTick_calls"], Flash_B=(src/"obj-nes-100/firmware.stm").stat().st_size,
                pins={n:sha(folder/n) for n in ("joint.json","events.json","window.csv","seal528.csv","packets.jsonl")})


def analyze(a):
    phases={}
    for phase in (1,2):
        golden=a.traces/f"nes-front638-both{phase}h"
        baseline=measure(a.traces/f"nes-tail646-base{phase}",golden,a.base)
        old=read(ROOT/"analysis/output645-verification.json")["cases"][golden.name]
        assert baseline["last_ACK"]==old["last_ACK"] and baseline["dense_intervals"]==old["dense_intervals"]
        cases={"base":baseline}
        for mode in ("grant","short"):
            trial=measure(a.traces/f"nes-tail646-{mode}{phase}",golden,a.build/mode/"src")
            f,b=trial["frames"][955],baseline["frames"][955]
            gates=dict(relative_955=f["interval"]<b["interval"],
                       absolute_955=f["absolute_display_frame"]<b["absolute_display_frame"],
                       control954=trial["frames"][954]["interval"]<=baseline["frames"][954]["interval"],
                       dense_VB=trial["dense_VB"]<baseline["dense_VB"],
                       dense_time=trial["dense_mean_ms"]<baseline["dense_mean_ms"],
                       last_ACK=trial["last_ACK"]<baseline["last_ACK"],
                       protected=trial["line951"]<=246 and trial["dense_intervals"][1]<=4 and trial["wait957"]==0,
                       Flash=trial["Flash_B"]<=212992)
            trial.update(gates=gates,pass_all=all(gates.values()),last_ACK_delta_ms=ms(trial["last_ACK"]-baseline["last_ACK"]))
            cases[mode]=trial
        phases[phase]=cases
    guards={}
    for mode in ("grant","short"):
        fw=phases[1][mode]["firmware"]
        guards[mode]={name:sha(a.build/f"{mode}-{name}.json") for name in ("menu","bulk","stop","seal")}
        for name in guards[mode]:
            assert read(a.build/f"{mode}-{name}.json")["firmware"]==fw
        for reason in ("none","program","done","busy","token"):
            path=a.build/f"{mode}-base-{reason}/result.json"
            v=read(path)
            assert v["passed"] and v["firmware_sha256"]==fw and v["safe_return"]==v["base_restored"]==int(reason=="none")
            guards[mode]["base_"+reason]=sha(path)
    retained=read(ROOT/"analysis/reject643-package.json")
    assert sha(a.board/"output_files/board.sof")==retained["board"]["SHA"]["board.sof"]
    recovery=read(a.recovery/"result.json")
    assert recovery["SOF"]==retained["board"]["SHA"]["board.sof"] and recovery["healthy_release_and_STOP"]==[32,97]
    assert all(sha(a.board/k)==v for k,v in recovery["rtl"].items())
    assert all(sha(a.recovery/(k+".log"))==v for k,v in recovery["logs"].items())
    return dict(phases=phases,guards=guards,offer_guards=read(a.build/"offer.json"),
                retained_capture_recovery=dict(separate_RTL_replay=recovery,
                    physical_baseline="analysis/hardware644-mmc643.json",joint_trace_includes_rejects=False),
                scope="Two post-boot starts; linked ARM CPI2, SysTick, SPI cost and ROM calendar, emulated SNES CPU. Displayed-map/PPU byte checks on all 53 accepted inputs. Separate STOP and menu guards. No new FPGA, physical FPS or installation.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("traces","build","base","board","recovery","out"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+"\n",newline="\n")
