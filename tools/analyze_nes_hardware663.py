"""Analyze the completed MMC662 hardware run against pinned MMC643 evidence."""
import argparse
import json
import re
import struct
from pathlib import Path
from analyze_nes_hardware552 import inputs
from analyze_nes_hardware559 import start_windows
from check_nes_fault641 import ROOT, digest, evidence
from decode_nes_minreject180 import decode
from nes_windows518 import windows, duration_ms


def work(b):
    columns = b["columns"].split(",")
    rows = [dict(zip(columns, (int(x,16) for x in b[f"b{i:02}"].split(",")), strict=True)) for i in range(12)]
    result = []
    for lo, hi in ((5,40),(40,55)):
        selected = rows[lo//5:hi//5]
        n = sum(r["frames"] for r in selected)
        result.append(dict(start_s=lo, end_s=hi, frame_starts=n,
                           per_frame={k:sum(r[k] for r in selected)/n for k in
                                      ("bg","obj","mapdirty","e1","d1_payload","plans")},
                           output_ms=10*sum(r["seal"] for r in selected)/n))
    return rows, result


def analyze(raw, baseline):
    old = evidence("hardware644-mmc643.json")
    g,b,p,pins = inputs(raw,662)
    _,bb,_,oldpins = inputs(baseline,643)
    assert oldpins == old["source_SHA256"]
    for key in ("run_error","run_rom_error","run_first_error","run_stop_error","fault_context_valid",
                "native_video_error","native_receiver_error","plan_error","trace_aborts"):
        assert g[key] == "0", key
    assert g["run_passed"] == g["native_result"] == "1"
    assert all(g[k] == "1" for k in ("verified", "stop_ok", "base_restored", "safe_to_reload"))
    assert g["compared_bytes"] == "393216"
    assert b["boot_reason"] == "1" and b["plan_valid"] == "0"
    assert all(b[k] == "0" for k in ("failed_transfers","cost_crc_errors","cost_transfer_stops"))
    assert b["cost_scene_crc32_hex"] == "5a04eed7" and b["cost_clock_hz"] == "84000000"
    assert b["cost_phase_and_op_are_nested"] == "1" and b["cost_cycles_include_IRQ_guard_and_wait"] == "1"
    n = int(g["native_frames"])
    elapsed = duration_ms(p)
    split = windows((raw/"nes-budget-mmc662.txt").read_text(encoding="utf-8-sig"), elapsed)
    periods = [dict(**a, previous_displays=o["displays"], previous_fps=o["fps"],
                    delta_pct=100*(a["fps"]/o["fps"]-1))
               for o,a in zip(old["completion_windows"],split,strict=True)]
    assert [(a["start_s"],a["end_s"]) for a in split] == [(5,40),(40,55)]
    commits = int(g["trace_commits"])
    ea = int(b["cost_op_08"].split(",")[0])
    assert commits == int(g["trace_begins"]) == int(g["trace_ends"]) == n+1
    assert ea == n and int(g["profile_last_display_tick"]) == 5995 and b["open"] == "1"
    phases = {}
    for i,key in enumerate(("receive","plan_supply","output_final_ack")):
        calls,_,hi,lo,maximum = map(int,b[f"cost_phase_{i:02}"].split(","))
        phases[key] = dict(calls=calls,ms_per_display=((hi<<32)+lo)*1000/84000000/n,max_ms=maximum/84000)
    assert phases["output_final_ack"]["calls"] == n
    pending = (int(g["sink_window_sent"])-int(g["sink_window_retired"])) & 65535
    assert pending == 1 and (g["native_sink_error"],g["sink_window_error"],g["sink_trace_ack_valid"],
                            g["sink_trace_mismatch_hex"]) == ("2","3","0","00")
    req = bytes.fromhex(g["sink_trace_request_hex"])
    assert len(req) == 16 and req[:2] == bytes((3,0))
    assert struct.unpack_from("<I",req,4)[0] == n+1
    assert struct.unpack_from("<H",req,8)[0] == int(g["trace_generation"]) == 1265
    assert bytes.fromhex(g["sink_trace_ack_hex"]) == bytes(12)
    rows,work662 = work(b)
    _,work643 = work(bb)
    assert sum(r["frames"] for r in rows) == n
    history = decode((raw/"nes-game-last-mmc662.txt").read_text(encoding="utf-8-sig"))
    events = history["events"]
    assert len(events) == 4 and [e["event"] for e in events] == ["REJECT","RECOVERY"]*2
    assert all(e["errors"] == 0 for e in events)
    times = [(name,int(t)) for name,t in re.findall(r"stage=(\w+).*?elapsed_ms=(\d+)",p)]
    assert times[-1][0] == "MENU_PREPARED"
    endpoints = dict(times)
    trimmed = sum(w["displays"] for w in split)/50
    return dict(trial=662, trial_family="MMC", physical=True, hardware_run_passed=True, logged_runs=1,
                user_report=dict(start_success=True,menu_return=True,perception="FPS felt improved"),
                source_SHA256=pins,reference="analysis/hardware644-mmc643.json",
                reference_SHA256=digest(ROOT/"analysis/hardware644-mmc643.json"),package="analysis/trial662-package.json",
                display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
                completion_windows=split,completion_comparison=periods,trimmed_fps=trimmed,
                trimmed_change_pct=100*(trimmed/old["trimmed_fps"]-1),
                phases=phases,phase_delta_ms={k:v["ms_per_display"]-old["phases"][k]["ms_per_display"] for k,v in phases.items()},
                frame_start_bins=[dict(start_s=i*5,displays=r["frames"],max_gap_ms=r["maxgap"]*10) for i,r in enumerate(rows)],
                start_bin_work_per_frame={"643":start_windows(bb),"662":start_windows(b)},
                work_comparison={"643":work643,"662":work662},
                terminal=dict(commits=commits,retires_EA=ea,pending=pending,serial=n+1,generation=1265,
                              last_display_s=59.95,request_hex=req.hex(),window_error=3,sink_error=2,
                              receiver_error=0,run_result=1,stop_ok=True,base_restored=True,
                              menu_state=g["menu_state"],last_checkpoint=times[-1][0],
                              stop_to_menu_ms=endpoints["MENU_PREPARED"]-endpoints["DISPLAY_STOPPED"],
                              interpretation="Runtime first result is DEADLINE. Final SEAL remains unretired at timed shutdown. Window 3 records a transfer callback failure; the exact pre/post transfer branch is not captured. No completed display is credited for it."),
                capture_history=history,boot=dict(polls=int(b["boot_polls"]),ticks=int(b["boot_ticks"])),
                limitations=["One playthrough per build with unsynchronized inputs and scenes.",
                             "Work bins are classified by frame start, completion windows by final display.",
                             "DWT phases include interrupts, waiting and overlapping operation measurements.",
                             "No physical per-frame DMA/VBlank split or captured failing transfer instruction."])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("raw","baseline","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    result=analyze(a.raw,a.baseline)
    a.out.write_text(json.dumps(result,indent=2)+"\n",newline="\n")
    print(json.dumps({k:result[k] for k in ("display","completion_comparison","trimmed_change_pct","phases","phase_delta_ms","work_comparison")},indent=2))
