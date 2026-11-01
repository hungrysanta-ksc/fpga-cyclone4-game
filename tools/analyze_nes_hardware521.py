# SPDX-License-Identifier: MIT
"""Reconcile a physical MMC run with its two completion windows and frame-start bins."""
import argparse
import json
from pathlib import Path

from analyze_nes_supply485_hardware import fields, sha
from audit_nes499 import capture_evidence
from nes_windows518 import duration_ms, windows

ROOT = Path(__file__).resolve().parents[1]


def analyse(raw, trial=520):
    files = {k: raw / f"nes-{k}-mmc{trial}.txt" for k in ("progress", "game-last", "budget")}
    progress, game, budget = [files[k].read_text(encoding="utf-8-sig") for k in files]
    g, b = fields(game), fields(budget)
    required = dict(candidate=f"NES-MMC{trial}", loaded_bytes="393216", compared_bytes="393216",
                    board_expected_hex="7b", board_observed_hex="7b", board_seen="1", verified="1",
                    verify_error="0", run_passed="1", start_sent="1", stop_ok="1", base_restored="1",
                    safe_to_reload="1", run_error="0", run_rom_error="0", fault_context_valid="0",
                    native_receiver_error="0", native_video_error="0")
    for key, value in required.items():
        assert g[key] == value, key
    assert all(line.startswith(f"MMC{trial} seq=") for line in progress.splitlines() if line.strip())
    assert b["bin_basis"] == "FRAME_START_NOT_SCENE" and b["bin_ticks"] == "500"
    assert b["cost_scene_crc32_hex"] == "5a04eed7" and b["cost_clock_hz"] == "84000000"
    assert b["cost_counter_available"] == "1"
    assert all(b[k] == "0" for k in ("cost_crc_errors", "failed_transfers", "cost_transfer_stops"))
    elapsed = duration_ms(progress)
    split = windows(budget, elapsed)
    n = int(g["native_frames"])
    outside = n - sum(w["displays"] for w in split)
    assert outside >= 0 and int(g["profile_last_display_tick"]) < 6000
    bins = []
    cols = b["columns"].split(",")
    for i in range(12):
        values = [int(x, 16) for x in b[f"b{i:02}"].split(",")]
        assert len(cols) == len(values)
        r = dict(zip(cols, values))
        count = r["frames"]
        obj, remainder = divmod(r["out"]-16*r["plans"], 16)
        assert count and remainder == 0 and 0 <= obj <= r["plans"]
        bins.append(dict(start_s=5*i, displays=count, approximate_fps=count/5,
                         phase_ms={k:10*r[k]/count for k in ("recv","plan","finish_ticks","seal")},
                         obj_plans=obj, obj_per_display=obj/count, max_gap_ms=r["maxgap"]*10))
    assert sum(r["displays"] for r in bins) == n
    phases = {}
    for i, name in enumerate(("receive", "plan_supply", "output_final_ack")):
        calls, _, hi, lo, _ = map(int, b[f"cost_phase_{i:02}"].split(","))
        phases[name] = dict(calls=calls, ms_per_display=((hi << 32) | lo)*1000/(int(b["cost_clock_hz"])*n))
    commits, eas = int(g["trace_commits"]), int(b["cost_op_08"].split(",")[0])
    pending = (int(g["sink_window_sent"])-int(g["sink_window_retired"])) % 65536
    assert commits == int(g["trace_ends"]) == int(g["trace_begins"]) == n+1
    assert int(g["trace_aborts"]) == 0 and eas == n == phases["output_final_ack"]["calls"]
    assert b["open"] == "1" and g["native_result"] == "1" and 0 <= pending <= 4
    previous, evidence, observation = {
        520: (516, "hardware517-mmc516.json", "Normal play and menu return. Early play clearly improved, late play felt similar."),
        524: (520, "hardware521-mmc520.json", "Normal play and menu return. Modest improvement felt through late play, with less slowdown when many enemies appeared."),
        529: (524, "hardware525-mmc524.json", "Normal execution and menu return. The user followed a similar playthrough."),
    }[trial]
    old = json.loads((ROOT/"analysis"/evidence).read_text())
    return dict(trial=trial, trial_family="MMC", hardware_run_passed=True, physical=True,
                user_observation=observation,
                source_SHA256={p.name:sha(p) for p in files.values()},
                display=dict(completed=n,seconds=elapsed/1000,fps=n*1000/elapsed,mean_ms=elapsed/n),
                completion_windows=split, first_second_displays=outside, frame_start_bins=bins,
                phases=phases, **{f"previous_MMC{previous}": old["display"]}, matched_playthrough=False,
                terminal=dict(commits=commits, retires_EA=eas, last_display_s=int(g["profile_last_display_tick"])/100,
                              outstanding=pending, runtime_result=int(g["native_result"]), errors={
                                  k:int(g[k]) for k in ("plan_error","sink_window_error","native_sink_error")}),
                capture=capture_evidence(game))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--trial", type=int, choices=(520,524,529), default=520)
    a = p.parse_args()
    a.out.write_text(json.dumps(analyse(a.raw, a.trial), indent=2)+"\n", encoding="utf8", newline="\n")
