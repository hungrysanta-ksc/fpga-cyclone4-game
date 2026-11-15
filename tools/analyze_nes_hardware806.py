"""Read the physical MMC805/806 logs and exercise the shipped 806 planner's OBJ limit."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from analyze_nes_hardware706 import duration_ms, fields, windows, work
from check_nes_game478 import Machine


def read_session(folder, number):
    logs, hashes = {}, {}
    for kind in ("game-last", "budget", "progress"):
        path = folder / f"nes-{kind}-mmc{number}.txt"
        raw = path.read_bytes()
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
        logs[kind] = raw.decode("utf-8-sig")
    game = fields(logs["game-last"])
    assert game["candidate"] == f"NES-MMC{number}"
    assert game["verified"] == game["start_sent"] == "1"
    assert game["stop_ok"] == game["base_restored"] == game["safe_to_reload"] == "1"
    assert game["menu_state"] == "PREPARED_RESET_HELD"
    budget = fields(logs["budget"])
    elapsed = duration_ms(logs["progress"])
    keys = ("native_result native_frames native_generation native_video_error native_receiver_error "
            "native_sink_error run_first_error run_rom_error run_stop_error trace_begins trace_ends "
            "trace_commits trace_aborts trace_generation plan_error sink_window_error "
            "ppu_state_valid fault_context_valid").split()
    session = dict(hashes=hashes, interval_ms=elapsed, terminal={k: int(game[k]) for k in keys},
                   menu_state=game["menu_state"], base_restored=True, stop_ok=True,
                   last_display_ms=int(game["profile_last_display_tick"]) * 10,
                   transfers={k: int(budget[k]) for k in ("failed_transfers", "cost_crc_errors", "cost_transfer_stops")})
    if number == 805:
        assert game["run_passed"] == game["native_result"] == "1" and game["run_first_error"] == "0"
        session["windows"] = windows(logs["budget"], elapsed)
        session["work_windows"] = work(budget)[1]
    else:
        assert game["run_passed"] == "0" and game["native_video_error"] == "12"
    return session


def planner_case(src, count, spread):
    m = Machine(src, bytes(128))
    layout = m.layout["nes_native165"]

    def write(field, data):
        m.u.mem_write(m.state + layout[field], data)

    write("state", bytes([4]))  # committed geometry, one palette epoch
    write("generation", struct.pack("<H", 1))
    write("counts", struct.pack("<6H", 33, 224, count, 0, 224, 32))
    write("rows", bytes(range(8)) * 28)
    write("raster", struct.pack("<Q", 0x1e << 36) * 224)
    write("ntiles", struct.pack("<H", 1))
    write("tiles", struct.pack("<HBx", 0, 3))
    fragments = []
    for i in range(count):
        top = 72 if spread and i == 32 else 64
        # Eight distinct evaluation ranks per visible fine row. Each resulting
        # OAM entry still covers eight physical lines during SNES evaluation.
        word = (top << 13) | ((8 * (i % 32)) << 22) | (1 << (38 + i // 8)) | ((i % 8) << 46)
        fragments.append(struct.pack("<Q", word))
    write("objects", b"".join(fragments))
    assert m.call("nes_resident211_begin", [m.resident, 1, 1, 1, m.writer | 1, 0]) == 1
    planned = m.call("nes_native_video211_plan", [m.state, m.lut, m.video, m.resident])
    error = m.u.mem_read(m.video + m.layout["nes_native_video165"]["error"], 1)[0]
    expected_failure = count > 32 and not spread
    assert (planned, error) == ((0, 12) if expected_failure else (1, 0)), (planned, error)
    return dict(fragments=count, moved_last_by_lines=8 if spread else 0, planned=bool(planned), error=error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("logs", "src806", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    result = {f"MMC{n}": read_session(args.logs, n) for n in (805, 806)}
    result["planner_firmware_sha256"] = hashlib.sha256((args.src806 / "obj-nes-100/firmware.stm").read_bytes()).hexdigest()
    result["synthetic_linked_planner"] = [planner_case(args.src806, count, spread)
                                          for count, spread in ((32, False), (33, False), (33, True))]
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
