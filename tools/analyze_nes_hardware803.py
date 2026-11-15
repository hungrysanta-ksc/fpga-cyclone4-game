"""Compare the two physical 801I-board runs with the previous timed/fortress runs."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from analyze_nes_hardware706 import decode, duration_ms, fields, windows, work

ROOT = Path(__file__).resolve().parents[1]


def session(archive, number):
    texts, hashes = {}, {}
    for kind in ("game-last", "budget", "progress"):
        name = f"nes-{kind}-mmc{number}.txt"
        data = archive.read(name)
        hashes[name] = hashlib.sha256(data).hexdigest()
        texts[kind] = data.decode("utf-8-sig")
    game, budget = fields(texts["game-last"]), fields(texts["budget"])
    assert game["candidate"] == f"NES-MMC{number}"
    assert game["loaded_bytes"] == game["compared_bytes"] == "393216"
    assert all(game[k] == "1" for k in ("verified", "start_sent", "stop_ok", "base_restored", "safe_to_reload"))
    assert game["menu_state"] == "PREPARED_RESET_HELD"
    elapsed = duration_ms(texts["progress"])
    errors = {key: int(budget[key]) for key in ("failed_transfers", "cost_crc_errors", "cost_transfer_stops")}
    keys = ("run_passed", "run_first_error", "run_stop_error", "run_rom_error", "native_result",
            "trace_aborts", "native_sink_error", "sink_window_error", "sink_window_sent",
            "sink_window_retired", "sink_window_flags", "sink_window_ack", "fault_context_valid")
    terminal = {key: int(game[key]) for key in keys}
    result = dict(hashes=hashes, displays=int(game["native_frames"]), interval_ms=elapsed,
                  last_display_ms=int(game["profile_last_display_tick"]) * 10, terminal=terminal,
                  transfer_errors=errors, stop_ok=True, base_restored=True, menu_state=game["menu_state"],
                  windows=windows(texts["budget"], elapsed))
    if number == 802:
        assert game["run_passed"] == game["native_result"] == "1"
        assert game["run_first_error"] == game["run_rom_error"] == game["run_stop_error"] == "0"
        result["work_windows"] = work(budget)[1]
    else:
        assert game["run_passed"] == "0" and game["run_rom_error"] == "2"
        assert game["ppu_state_valid"] == "1" and game["fault_context_valid"] == "0"
        raw = game["ppu_state_hi"] + game["ppu_state_lo"]
        result.update(ppu_raw=raw, ppu=decode(int(raw, 16)), physical_request=None,
                      pending_request_hex=game["sink_trace_request_hex"],
                      outstanding=(terminal["sink_window_sent"] - terminal["sink_window_retired"]) % 65536,
                      budget_epoch_ms=int(budget["epoch_tick"]) * 10)
    return result


def analyze(path):
    with ZipFile(path) as archive:
        assert len(archive.namelist()) == 6 and archive.testzip() is None
        timed, long_run = (session(archive, n) for n in (802, 803))
    prior = json.loads((ROOT / "analysis/hardware799-results.json").read_bytes())
    previous = prior["MMC798"]
    return dict(MMC802=timed, MMC803=long_run,
                timed_fps_delta_vs798=[a["fps"] - b["fps"] for a, b in
                                       zip(timed["windows"], previous["windows"], strict=True)],
                MMC798_windows=previous["windows"], MMC798_work=previous["work_windows"],
                MMC799_ppu_raw=prior["MMC799"]["ppu_raw"], MMC799_ppu=prior["MMC799"]["ppu"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.archive), indent=2) + "\n", encoding="utf8", newline="\n")
