"""Decode MMC642's first-fault E8 and next-capture history, with the two MMC639 controls."""
import argparse
import json
from pathlib import Path
import re
from check_nes_fault641 import digest, evidence
from decode_nes_minreject180 import decode


def analyze(folder, trial):
    files = [folder / f"nes-{kind}-mmc{trial}.txt" for kind in ("game-last", "budget", "progress")]
    game, budget, progress = (p.read_text(encoding="utf-8-sig") for p in files)
    fields = dict(line.split("=", 1) for line in (game + "\n" + budget).splitlines() if "=" in line)
    events = decode(game)["events"] if fields["ppu_history_valid"] == "1" else []
    e8 = bytes.fromhex(fields["plan_reply_hex"])
    if fields["plan_valid"] == "1":
        crc = 0
        for b in e8[1:-1]:
            crc ^= b
            for _ in range(8):
                crc = ((crc << 1) ^ (7 if crc & 128 else 0)) & 255
        assert len(e8) == 20 and e8[1:3] == bytes((0xd7, 4)) and crc == e8[-1]
    checkpoints = re.findall(r"stage=(\w+).*?elapsed_ms=(\d+)", progress)
    times = dict(checkpoints)
    assert checkpoints[-1][0] == "MENU_PREPARED" and fields["stop_ok"] == fields["base_restored"] == "1"
    keys = ("boot_reason boot_polls boot_ticks plan_generation plan_expected_sent plan_valid plan_reply_hex "
            "plan_phase plan_reason native_frames native_generation native_receiver_error run_rom_error "
            "sink_window_sent sink_window_retired profile_last_display_tick profile_tick_ms cost_crc_errors "
            "cost_transfer_stops display_5_40_55").split()
    return dict(input_SHA256={p.name: digest(p) for p in files}, fields={k: fields[k] for k in keys},
                E8_origin=e8[14:16].hex() if trial == 642 else None, history=events,
                START_reads=sum("buttons=START|" in s for s in game.splitlines()),
                display_interval_ms=int(times["DISPLAY_STOPPED"])-int(times["DISPLAY_NEXT"]),
                last_checkpoint=checkpoints[-1][0])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("current", "prior", "out"):
        p.add_argument("--"+n, required=True, type=Path)
    a = p.parse_args()
    hw = analyze(a.current, 642)
    prev = analyze(a.prior, 639)
    for run in (hw, prev):
        event, = run["history"]
        assert event["generation_mod256"] == (int(run["fields"]["plan_generation"]) + 1) % 256
        assert event["event"] == "REJECT" and event["rows"] == 224
        assert all(event[k] == 0 for k in ["groups","palettes_saturated31","objects","exceptions","errors","candidate_display_mask"])
    assert hw["E8_origin"] == "0024" and hw["fields"]["plan_generation"] == "97"
    timeout = evidence("hardware640-mmc639.json")["runs"][1]["fields"]
    assert timeout["boot_ticks"] == "500" and timeout["native_frames"] == "0"
    a.out.write_text(json.dumps(dict(MMC642=hw, MMC639_run1=prev, MMC639_run2="separate stage-0 boot timeout",
                     historical_stage_select="analysis/game215-hardware01-verification.json",
                     physical_per_frame_tile_counts=None, physical_FPS=None), indent=2)+"\n", newline="\n")
