"""Read the seven physical sessions, keeping stop paths, windows and clocks separate."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from analyze_nes_hardware706 import decode, duration_ms, fault, fields, windows, work

SESSIONS = ["763-1회차_실패","763-2회차_성공","764-성공_플레이중팅김",
            "765-1회차_실패","765-2회차_실패","765-3회차_실패","766-성공_플레이중팅김"]


def read_sessions(downloads, archive):
    rows = {}
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for suffix in SESSIONS:
            texts, hashes = {}, {}
            for kind in ("game-last","budget","progress"):
                p = downloads / f"nes-{kind}-mmc{suffix}.txt"
                blob = p.read_bytes()
                z.writestr(p.name,blob)
                hashes[p.name] = hashlib.sha256(blob).hexdigest()
                texts[kind] = blob.decode("utf-8-sig")
            g, b = fields(texts["game-last"]), fields(texts["budget"])
            ms = duration_ms(texts["progress"])
            assert g["candidate"] == "NES-MMC" + suffix[:3]
            assert g["loaded_bytes"] == g["compared_bytes"] == "393216"
            assert all(g[k]=="1" for k in ("verified","end_accepted","start_sent","stop_ok","base_restored","safe_to_reload"))
            assert g["menu_state"]=="PREPARED_RESET_HELD"
            marks = dict(re.findall(r"stage=(\w+).*?elapsed_ms=(\d+)", texts["progress"]))
            count=int(g["native_frames"])
            row=dict(files=hashes, duration_ms=ms, loader_to_display_next_ms=int(marks["DISPLAY_NEXT"]), frames=count, boot={k:v for k,v in b.items() if k.startswith("boot_")},
                     verified_B=393216, STOP_base_menu_prepared=True,
                     terminal={k:g[k] for k in ("run_error","run_stop_error","run_first_error","run_rom_error","native_result","native_receiver_error",
                         "native_sink_error","native_video_error","sink_window_flags","sink_window_error","native_transactions","trace_commits","trace_aborts","plan_error")},
                     failed_transfers=b["failed_transfers"], epoch_tick=b.get("epoch_tick"),
                     context_valid=g["fault_context_valid"],windows=None)
            if count:
                assert b["cost_crc_errors"]=="0" and b["cost_scene_crc32_hex"]=="5a04eed7"
                row["windows"]=windows(texts["budget"],ms)
                if suffix.startswith("763"):
                    row["work_windows"]=work(b)[1]
            else:
                assert g["native_transactions"]=="0" and b["cost_sampled"]=="0"
            if g["ppu_state_valid"]=="1":
                row["ppu_raw"]=g["ppu_state_hi"]+g["ppu_state_lo"]
                row["ppu"]=decode(int(row["ppu_raw"],16))
            if g["fault_context_valid"]=="1":
                row["fault"]=fault(g)
            rows[suffix]=row
    with ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist())==21
        for r in rows.values():
            for name,h in r["files"].items():
                assert hashlib.sha256(z.read(name)).hexdigest()==h
    return rows


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("downloads","archive","result"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    data=read_sessions(a.downloads,a.archive)
    a.result.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8",newline="\n")
