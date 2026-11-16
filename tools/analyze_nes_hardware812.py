"""Record the two stage-entry stops without treating partial windows as frame rates."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from analyze_nes_hardware706 import duration_ms, fields
from package_nes_obj807 import ROOT, digest
from prepare_nes_prefix813 import WORK


def collect(folder):
    result, files = {}, {}
    for n in (811,812):
        logs, pins = {}, {}
        for kind in ("progress","budget","game-last"):
            name = f"nes-{kind}-mmc{n}.txt"
            files[name] = (folder/name).read_bytes()
            logs[kind] = files[name].decode("utf-8-sig")
            pins[name] = digest(files[name])
        g, b = fields(logs["game-last"]), fields(logs["budget"])
        assert g["candidate"] == f"NES-MMC{n}" and g["menu_state"] == "PREPARED_RESET_HELD"
        assert all(g[k]=="1" for k in ("verified","start_sent","stop_ok","base_restored","safe_to_reload"))
        assert g["loaded_bytes"] == g["compared_bytes"] == "393216"
        assert g["native_result"] == g["sink_window_error"] == g["plan_error"] == "5"
        assert g["native_frames"] == str(int(g["trace_commits"])-1)
        assert g["trace_generation"] == str(int(g["native_generation"])+1)
        assert all(g[k]=="0" for k in ("run_passed","run_rom_error","run_stop_error","obj_load","trace_aborts",
                                       "native_receiver_error","native_video_error","native_sink_error","sink_trace_valid"))
        assert b["plan_valid"] == b["cost_crc_errors"] == b["failed_transfers"] == "0"
        assert int(g["sink_window_sent"])-int(g["sink_window_retired"]) == 3
        result[n] = dict(duration_ms=duration_ms(logs["progress"]), hashes=pins,
                         partial_displays=b["display_5_40_55"], first_level_reported_by_player=True,
                         game={k:g[k] for k in ("run_first_error","run_rom_error","stop_ok","base_restored",
                               "native_frames","native_generation","trace_generation","sink_window_error",
                               "sink_window_sent","sink_window_retired","sink_window_flags","sink_window_ack",
                               "plan_error","plan_sent","plan_end","obj_load","profile_last_display_tick")})
    archive=WORK/"hardware811-812.zip"
    if not archive.exists():
        with ZipFile(archive,"x",ZIP_DEFLATED) as z:
            for name,data in files.items():
                z.writestr(name,data)
    with ZipFile(archive) as z:
        assert set(z.namelist())==set(files) and all(z.read(k)==v for k,v in files.items())
    record=dict(sessions=result,archive_sha256=digest(archive.read_bytes()),
                limitation="Neither the pending bulk target nor the raw failing E0 response is in the physical reports.")
    (ROOT/"analysis/hardware812-results.json").write_text(json.dumps(record,indent=2)+"\n",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("downloads",type=Path)
    collect(p.parse_args().downloads)
