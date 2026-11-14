"""Analyze the physical MMC770/771 timed pair and MMC772 long run."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

from analyze_nes_hardware706 import decode as decode_ppu, duration_ms, fields
from read_nes_frame769 import decode, REASONS


def averages(rows, keys):
    return {key: mean(r[key] for r in rows) for key in keys}


def session(files, number):
    def get(prefix, ext="txt"):
        return files.read(f"nes-{prefix}-mmc{number}.{ext}")
    budget = get("budget").decode("utf-8-sig")
    b = fields(budget)
    g = fields(get("game-last").decode("utf-8-sig"))
    progress = get("progress").decode("utf-8-sig")
    elapsed = duration_ms(progress)
    assert g["candidate"] == f"NES-MMC{number}" and g["loaded_bytes"] == g["compared_bytes"] == "393216"
    assert all(g[k] == "1" for k in ("verified","start_sent","stop_ok","base_restored","safe_to_reload"))
    assert "stage=MENU_PREPARED" in progress and g["menu_state"] == "PREPARED_RESET_HELD"
    rows = list(decode(get("frame","bin"),budget))
    assert rows and all(r["valid"] for r in rows) and int(b["dropped"]) == 0
    assert all(b["generation"] > a["generation"] for a,b in zip(rows,rows[1:]))
    counters = [r for r in rows if not r["saturated"]]
    early, late = map(int,b["display_5_40_55"].split(","))
    result = dict(duration_ms=elapsed, frames=int(g["native_frames"]), displayed=[early,late],
                  fps=[early/35,late/15,(early+late)/50],terminal={k:g[k] for k in
                      ("run_passed","run_rom_error","run_first_error","run_stop_error","native_result",
                       "native_generation","trace_generation","profile_last_display_tick","fault_context_valid",
                       "sink_window_error","sink_window_sent","sink_window_retired","plan_error","native_video_error")},
                  STOP_base_menu_prepared=True,rows=len(rows),dropped=0,saturated=len(rows)-len(counters),
                  work=averages(rows,("map_groups","obj","bg")),
                  mean_counts_without_saturated_rows=averages(counters,["output_E0","output_E0_quiet","output_E8","output_E8_ready",
                      *REASONS,*(k+("_quiet" if k.startswith("E0") else "_ready") for k in REASONS)]),
                  seal_to_dma=dict(Counter(r["seal_to_dma_vb"] for r in rows)),
                  dma_to_ack=dict(Counter(r["dma_to_ack_vb"] for r in rows)),
                  interval_VB=mean(r["ack_interval_vb"] for r in rows[1:]),
                  previous_ACK_to_SEAL_VB=mean(r["ack_interval_vb"]-r["seal_to_dma_vb"]-r["dma_to_ack_vb"] for r in rows[1:]),
                  two_VB_upload=[r for r in rows if r["seal_to_dma_vb"]>=2])
    if number in (770,771):
        assert g["run_passed"]==g["native_result"]=="1" and g["run_rom_error"]=="0"
        bin5=[int(s,16) for s in b["b05"].split(",")]
        assert [bin5[i] for i in (0,16,17,18)] == [len(rows),*(sum(r[k] for r in rows) for k in ("bg","obj","map_groups"))]
        result["bin5_mean_ms"]={k:10*bin5[i]/len(rows) for i,k in enumerate(("recv","plan","output"),1)}
    else:
        old=json.loads((Path(__file__).resolve().parents[1]/"analysis/hardware767-mmc763-766.json").read_bytes())
        raw=g["ppu_state_hi"]+g["ppu_state_lo"]
        assert g["ppu_state_valid"]=="1" and g["run_rom_error"]=="2" and not int(g["fault_context_valid"])
        for prefix in ("764","766"):
            prev,=(v for name,v in old.items() if name.startswith(prefix))
            assert prev["ppu_raw"]==raw and prev["terminal"]["run_rom_error"]=="2"
        result["ppu"]=dict(raw=raw,**decode_ppu(int(raw,16)))
    return result,rows


def matched(a,b,limits):
    # Prefer the nearest map, OBJ, BG, then tick. Each captured screen is used once.
    edges=[]
    for i,x in enumerate(a[1:],1):
        for j,y in enumerate(b[1:],1):
            distance=tuple(abs(x[k]-y[k]) for k in ("map_groups","obj","bg"))
            if not (x["saturated"] or y["saturated"]) and all(d<=t for d,t in zip(distance,limits)):
                edges.append((*distance,abs(x["start_tick"]-y["start_tick"]),i,j))
    used_a,used_b=set(),set()
    pairs=[]
    for *_,i,j in sorted(edges):
        if i not in used_a and j not in used_b:
            used_a.add(i);used_b.add(j);pairs.append((a[i],b[j]))
    keys=("map_groups","obj","bg","output_E0_quiet","output_E8","seal_to_dma_vb","dma_to_ack_vb","ack_interval_vb")
    return dict(limits=limits,generations=[[x["generation"],y["generation"]] for x,y in pairs],
                means=[averages(side,keys) for side in zip(*pairs)])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    parser.add_argument("result",type=Path)
    args=parser.parse_args()
    with ZipFile(args.archive) as z:
        assert len(z.namelist())==12 and z.testzip() is None
        data={};all_rows={}
        for n in (770,771,772):
            data[n],all_rows[n]=session(z,n)
        report=dict(sessions=data, matched=[matched(all_rows[770],all_rows[771],t) for t in ((0,0,0),(0,2,8),(1,4,8),(2,8,16))],
                    raw_sha256={k:hashlib.sha256(z.read(k)).hexdigest() for k in z.namelist()})
    args.result.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8",newline="\n")
