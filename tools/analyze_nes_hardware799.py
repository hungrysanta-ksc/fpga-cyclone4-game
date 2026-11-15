"""Compare the physical control runs with the timed 763 run and retained fortress faults."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

from analyze_nes_hardware706 import decode, duration_ms, fault, fields, windows, work

ROOT = Path(__file__).resolve().parents[1]


def session(raw, n):
    texts, hashes = {}, {}
    for kind in ("progress", "game-last", "budget"):
        name = f"nes-{kind}-mmc{n}.txt"
        data = raw.read(name)
        texts[kind] = data.decode("utf-8-sig")
        hashes[name] = hashlib.sha256(data).hexdigest()
    g, b = fields(texts["game-last"]), fields(texts["budget"])
    assert g["candidate"] == f"NES-MMC{n}" and g["verified"] == g["start_sent"] == "1"
    assert g["loaded_bytes"] == g["compared_bytes"] == "393216"
    assert all(g[k]=="1" for k in ("stop_ok","base_restored","safe_to_reload"))
    assert g["menu_state"]=="PREPARED_RESET_HELD" and g["run_stop_error"]=="0"
    marks = {m:int(t) for m,t in re.findall(r"stage=(\w+).*?elapsed_ms=(\d+)",texts["progress"])}
    elapsed = duration_ms(texts["progress"])
    assert "PROBE_STOPPED" not in marks and b["boot_reason"]=="1"
    assert b["cost_crc_errors"]==b["failed_transfers"]=="0"
    r = dict(hashes=hashes, interval_ms=elapsed, display_next_ms=marks["DISPLAY_NEXT"],
             stopped_to_menu_ms=marks["MENU_PREPARED"]-marks["DISPLAY_STOPPED"],
             boot_ms=10*int(b["boot_ticks"]), frames=int(g["native_frames"]),
             final_display_ms=10*int(g["profile_last_display_tick"]), stop_base_menu_prepared=True,
             windows=windows(texts["budget"],elapsed),
             terminal={k:g[k] for k in ("run_passed","native_result","run_rom_error","run_first_error","run_stop_error",
                       "trace_aborts","native_sink_error","sink_window_sent","sink_window_retired","plan_error")})
    if n==798:
        assert g["run_passed"]==g["native_result"]=="1" and g["run_rom_error"]=="0"
        r["work_windows"]=work(b)[1]
    else:
        assert g["run_passed"]=="0" and g["run_rom_error"]==g["native_result"]=="2"
        assert g["fault_context_valid"]==g["ppu_state_valid"]=="1"
        r["context"]=fault(g)
        r["ppu_raw"]=g["ppu_state_hi"]+g["ppu_state_lo"]
        r["ppu"]=decode(int(r["ppu_raw"],16))
    return r


def analyze(archive):
    with ZipFile(archive) as raw:
        assert raw.testzip() is None and len(raw.namelist())==6
        timed, long_run = (session(raw,n) for n in (798,799))
    old=json.loads((ROOT/"analysis/hardware767-mmc763-766.json").read_bytes())
    reference=old["763-2회차_성공"]
    prev772=json.loads((ROOT/"analysis/hardware772-results.json").read_bytes())["sessions"]["772"]
    for n in (764,766):
        prev=next(row for key,row in old.items() if key.startswith(str(n)))
        assert prev["ppu_raw"]==long_run["ppu_raw"] and prev["terminal"]["run_rom_error"]=="2"
        if n==766:
            assert prev["fault"]==long_run["context"]
    assert prev772["ppu"]["raw"]==long_run["ppu_raw"] and prev772["terminal"]["run_rom_error"]=="2"
    return dict(MMC798=timed,MMC799=long_run,MMC763_windows=reference["windows"],
                MMC763_work=reference["work_windows"],same_frozen_PPU=[764,766,772,799],
                same_verified_address_and_response_context=[766,799])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("archive","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.archive),indent=2)+"\n",encoding="utf8")
