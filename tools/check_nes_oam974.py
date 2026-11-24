"""Compare 911 OAM packet service, scroll padding overlap and final display across boots."""
import argparse
import json
from pathlib import Path

from analyze_nes_palette971 import measure
from check_nes_blank959 import directory, read
from check_nes_output970 import counters, packet_path
from nes_oam974 import PACKED, CONTROL, INLINE, WIDE, WIDE_CONTROL, WORK
from test_nes_banks557 import MASTER


ROMS = {"973before232": PACKED, "974inline": INLINE, "974control": CONTROL,
        "974oam": WORK, "974widecontrol": WIDE_CONTROL, "974wide": WIDE}


def summarize(temp):
    result = {"master_Hz": MASTER, "scope": "cold cache, linked ARM and 65816, FPGA port model",
              "physical_free_B": {}, "phases": {}, "guards": {}}
    for tag, rom in ROMS.items():
        result["physical_free_B"][tag] = read(rom/"build.json")["physical_free_B"]
        assert len((rom/"sink-program.hex").read_text().splitlines()) == 5120
    for phase in (1, 2):
        ref = directory(temp, phase, "973before232", "cold")
        data = result["phases"][phase] = {}
        for tag in ROMS:
            folder = directory(temp, phase, tag, "cold")
            m = measure(folder, ref)
            commands, ledger = packet_path(folder, 911)
            op8, = (p for p in ledger if p["op"] == 8)
            repeat, = (bytes.fromhex(p[3]) for p in commands if p[:2] == (911, 8))
            assert repeat[10:] == bytes.fromhex("b0000400500100f00000")
            pad, = (p for p in ledger if p["op"] == 5)
            obj = next(p for p in ledger if (p["op"], p["section"]) == (7, 1))
            v = m["reveal_vblank"]
            data[tag] = dict(reveals=v, interval911=v[6]-v[5], ack912=m["ack912"],
                             op8=op8, op8_ms=(op8["ack"]-op8["load"])*1000/MASTER,
                             pad_ack=pad["ack"], first_obj=obj, rgb_matches=m["rgb_matches"],
                             arm_sha256=m["arm_sha256"], client_sha256=m["client_sha256"],
                             seal911=counters(folder, 911))
        marks = dict(line.split() for line in (temp/f"nes-974-trace-p{phase}"/"oam974.txt").read_text().splitlines())
        marks = {key: int(value) for key,value in marks.items()}
        p = data["973before232"]["op8"]
        assert list(marks) == ["rule","data","literal","dma","expand","expanded","service","accept"]
        assert list(marks.values()) == sorted(marks.values()) and p["load"] < marks["rule"] < marks["accept"] < p["ack"]
        data["baseline_pc_marks"] = marks
        assert len({data[tag]["arm_sha256"] for tag in ROMS}) == 1
    for variant in ("", "wide-"):
        guards = result["guards"][variant or "inline"] = {}
        for length in (8, 12, 332, 336, 334, 340):
            folder = temp/f"nes-oam974-{variant}guard-{length}"
            status = read(folder/"result.json")
            valid = length in (8, 12, 332, 336)
            assert status["passed"] and status["commits"] == 6 and status["last_status"] == (228 if valid else 224)
            proof = (folder/"proof974.txt").read_text().strip()
            assert proof == ("exact bytes and neighbours before STOP" if valid else "range rejected")
            guards[length] = {"proof":proof, "status":status["last_status"], "commits":6}
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    args = p.parse_args()
    args.out.write_text(json.dumps(summarize(args.temp),indent=2)+"\n",encoding="utf-8")
