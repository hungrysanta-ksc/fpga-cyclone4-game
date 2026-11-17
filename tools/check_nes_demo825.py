"""Match the physical credit signature, then exercise the same ARM entry points after repair."""
import argparse
import json
import re
from pathlib import Path

from check_nes_prefix813 import exercise, sha
from prepare_nes_trial802 import PROBES
from analyze_nes_output822 import BASE_ARM, CLIENT


def transition(temp):
    work=PROBES/"nes-trial825"
    schedule=json.loads((work/"data/change/work.json").read_text())
    pictures=[r["source_frame"] for r in schedule]
    assert pictures==[1500,1504,1557,1561,1565,1569]
    results={}
    for phase in (1,2):
        control=temp/f"nes-tile821-change-base-p{phase}-825-820"
        for edition in (820,824,825):
            folder=control if edition==820 else temp/f"nes-tile821-change-jointmirror-p{phase}-825-{edition}"
            arm=BASE_ARM if edition==820 else sha(PROBES/f"nes-output823/link-{edition}/src/obj-nes-100/firmware.stm")
            key=f"{edition}-p{phase}"
            if edition==824:
                fault=json.loads((folder/"fault.json").read_text())
                def field(owner,k,n):
                    data=fault[owner]
                    off=data["layout"][k]
                    return int.from_bytes(bytes.fromhex(data["bytes"])[off:off+n],"little")
                sent=field("transport","sent",2)
                retired=field("transport","retired",2)
                target=field("plan","bulk_until",2)
                g=field("plan","generation",2)
                assert g==907 and pictures[g-905]==1557
                assert sent-target==5 and sent-retired==1 and field("plan","bulk_pending",1)
                assert field("plan","sent",2)==6 and field("transport","status_flags",1)==3
                assert field("transport","error",1)==field("plan","error",1)==5
                packets=[bytes.fromhex(json.loads(l)[2]) for l in (folder/"packets.jsonl").read_text().splitlines()]
                heads=[(p[0],p[1]) for p in packets[target-1:sent]]
                assert heads==[(7,0),(2,2),(2,2),(2,2),(2,5),(5,5)]
                assert all(int.from_bytes(p[8:10],"little")==g for p in packets[target-1:sent])
                results[key]=dict(passed=False,source_frame=1557,bulk_target=target,sent=sent,
                                  retired=retired,plan_sent=6,window_error=5,plan_error=5,heads=heads)
                continue
            result=json.loads((folder/"joint.json").read_text())
            assert result["firmware_SHA256"]==arm and result["client_SHA256"]==CLIENT
            assert result["passed"] and result["commits"]==6 and result["last_status"]==1
            hashes=[]
            for i in range(905,911):
                for name in (f"frame-{i}.rgb",f"map-{i}.bin",f"expected-{i}.bin",f"colors636-{i}.bin"):
                    assert (folder/name).read_bytes()==(control/name).read_bytes(),(key,name)
                hashes.append(sha(folder/f"frame-{i}.rgb"))
            results[key]=dict(passed=True,acks=[f["ACK_masterclock"] for f in result["frames"]],
                              arm=arm,RGB=hashes)
    return dict(source_frames=pictures,results=results,scope="Six captured pictures straddle the blank interval. Separate directed credit tests reproduce the observed queue signature. Hardware retest pending.")


def hardware(logs, edition):
    files = {name:logs/f"nes-{name}-mmc{edition}.txt" for name in ("progress","budget","game-last")}
    def fields(name):
        return dict(line.split("=",1) for line in files[name].read_text().splitlines() if "=" in line)
    game,budget=fields("game-last"),fields("budget")
    progress=dict((stage,int(ms)) for stage,ms in re.findall(r"stage=(\w+).*?elapsed_ms=(\d+)",files["progress"].read_text()))
    return dict(hashes={k:sha(p) for k,p in files.items()},display_ms=10*int(game["profile_last_display_tick"]),
                display_to_stop_ms=progress["DISPLAY_STOPPED"]-progress["DISPLAY_NEXT"],
                stop_to_menu_ms=progress["MENU_PREPARED"]-progress["DISPLAY_STOPPED"],
                bins_5_40_55=budget["display_5_40_55"],frames=int(game["native_frames"]),
                fields={k:int(game[k]) for k in ("verified","stop_ok","base_restored","native_result","native_generation","plan_sent","plan_end",
                    "native_receiver_error","native_video_error","native_sink_error","sink_window_error","plan_error",
                    "sink_window_sent","sink_window_retired","sink_window_flags","run_rom_error")})


def check(logs, out):
    sessions={str(n):hardware(logs,n) for n in (819,820,824)}
    physical=sessions["824"]["fields"]
    rows={}
    for edition in (824,825):
        src=PROBES/f"nes-output823/link-{edition}/src"
        fixed=edition==825
        common=dict(advance_credit=True,initial_plan_sent=physical["plan_sent"])
        cases={}
        for name,counter in (("observed",physical["sink_window_sent"]),("wrap",2)):
            cases[name]=exercise(src,counter,fixed,end_plan=True,**common)
        if fixed:
            cases["wrong_counter"]=exercise(src,physical["sink_window_sent"],True,bad_status=True,**common)
        rows[str(edition)]=dict(firmware=sha(src/"obj-nes-100/firmware.stm"),cases=cases)
    prior=rows["824"]["cases"]["observed"]
    for k in ("sent","retired","flags"):
        assert prior[k]==physical["sink_window_"+k]
    assert physical["plan_error"]==prior["plan_error"]==physical["sink_window_error"]==prior["window_error"]==5
    assert rows["825"]["cases"]["observed"]["plan_sent"]==physical["plan_sent"]+1
    result=dict(hardware=sessions,replay=rows,
                scope="Reachable four-credit sequence on the linked ARM matches physical counters and error codes. The cartridge log contains no last E1/E0 payloads or bulk target.")
    out.write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("logs",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    check(a.logs,a.out)
