"""Verify the physical 807/808 exits, OBJ admission and timed display windows."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_hardware706 import duration_ms, fields, windows, work

ROOT = Path(__file__).resolve().parents[1]


def session(folder, edition):
    texts, hashes = {}, {}
    for kind in ("progress", "budget", "game-last"):
        path = folder / f"nes-{kind}-mmc{edition}.txt"
        raw = path.read_bytes()
        texts[kind] = raw.decode("utf-8-sig")
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
    g = fields(texts["game-last"])
    b = fields(texts["budget"])
    assert g["candidate"] == f"NES-MMC{edition}"
    assert g["loaded_bytes"] == g["compared_bytes"] == "393216"
    assert all(g[k] == "1" for k in ("verified", "start_sent", "run_passed", "stop_ok", "base_restored", "safe_to_reload"))
    assert all(g[k] == "0" for k in ("run_rom_error", "run_first_error", "run_stop_error", "native_receiver_error", "native_video_error"))
    assert g["menu_state"] == "PREPARED_RESET_HELD"
    elapsed = duration_ms(texts["progress"])
    keys = ("native_result native_frames native_generation trace_generation trace_begins trace_ends trace_aborts "
            "trace_commits trace_first_abort_reason trace_last_abort_reason obj_line obj_load screen_stage "
            "native_sink_error sink_window_error plan_error sink_window_sent sink_window_retired").split()
    terminal = {key: int(g[key]) for key in keys}
    assert terminal["trace_begins"] == terminal["trace_ends"] == terminal["trace_commits"] + terminal["trace_aborts"]
    assert b["cost_op_order"].split(",")[8] == "EA"
    ea_count = int(b["cost_op_08"].split(",")[0])
    assert ea_count == terminal["native_frames"] == terminal["trace_commits"] - 1
    errors = {key: int(b[key]) for key in ("failed_transfers", "cost_transfer_stops", "cost_crc_errors")}
    assert not any(errors.values())
    result = dict(hashes=hashes, elapsed_ms=elapsed, last_display_ms=int(g["profile_last_display_tick"])*10,
                  menu_prepared=True, base_restored=True, stop_ok=True, terminal=terminal,
                  ea_count=ea_count, transport_errors=errors)
    if edition == 807:
        assert terminal["native_result"] == 1 and terminal["obj_load"] == terminal["trace_aborts"] == 0
        rows = windows(texts["budget"], elapsed)
        ref = json.loads((ROOT/"analysis/hardware806-results.json").read_bytes())["MMC805"]
        delta = []
        for row, old in zip(rows, ref["windows"], strict=True):
            assert (row["start_s"],row["end_s"]) == (old["start_s"],old["end_s"])
            delta.append(row["fps"]-old["fps"])
        result.update(windows=rows, work=work(b)[1], delta_fps_vs805=delta)
    else:
        assert terminal["native_result"] == 8 and terminal["screen_stage"] == 0x7e
        assert terminal["trace_aborts"] == 1 and terminal["trace_first_abort_reason"] == terminal["trace_last_abort_reason"] == 6
        assert terminal["obj_load"] > 32
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    results = {f"MMC{n}": session(args.logs,n) for n in (807,808)}
    args.output.write_text(json.dumps(results,indent=2)+"\n",encoding="utf8",newline="\n")
