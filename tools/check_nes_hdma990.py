"""Compare the emitted packets, display rows and physical DMA bytes on aligned runs."""
import argparse
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, sha
from check_nes_tile985 import transfers
from nes_hdma990 import BASE, ROOT, PACKED
from test_nes_raw506_joint import PERIOD


def tail(folder):
    # Reconstruct all literal tails by target address, independently of queue order.
    data = {}
    for line in (folder / "packets.jsonl").read_text().splitlines():
        packet = bytes.fromhex(json.loads(line)[2])
        offset = int.from_bytes(packet[10:12], "little")
        if packet[:2] != bytes((2, 5)) or offset < 1121:
            continue
        g = int.from_bytes(packet[8:10], "little")
        block = packet[16:]
        assert len(block) == int.from_bytes(packet[12:14], "little")
        if offset == 1313 and len(block) == 183:
            block += bytes(60) + bytes((21, 0)) * 3
        if offset == 1121 and len(block) == 6:
            block = b"".join(block[i:i+2] * 32 for i in (0, 2, 4))
        dest = data.setdefault(g, {})
        for i, value in enumerate(block, offset):
            assert i not in dest
            dest[i] = value
    return data


def measure(temp, phase, mode, ref):
    folder = directory(temp, phase, "990" + mode, "cold")
    events = read(folder / "events.json")
    joint = read(folder / "joint.json")
    assert tail(folder) == tail(ref) and map_payloads(folder) == map_payloads(ref)
    assert all(sha(folder / f"frame-{g}.rgb") == sha(ref / f"frame-{g}.rgb") for g in range(905, 913))
    assert [r["records"] for r in read(folder / "e9931.json")] == [r["records"] for r in read(ref / "e9931.json")]
    commands, ledger = packet_path(folder, 911, expected_shape=(17 if mode == "late" else 16, 3))
    detail = []
    for c, r in zip(commands[-len(ledger):], ledger, strict=True):
        packet = bytes.fromhex(c[3])
        offset = int.from_bytes(packet[10:12], "little")
        if r["op"] == 2 and r["section"] == 5 and offset >= 1121:
            detail.append(dict(offset=offset, size=len(packet)-16, **r))
    origin = next(e["capture_ready"] for e in events if e["event"] == "source_begin" and e["generation"] == 911) - 240*1364
    ack909 = next(f["ACK_masterclock"] for f in joint["frames"] if f["generation"] == 909)
    last_d2 = max(e["clock"] for e in events if e.get("input_generation") == 910 and e.get("opcode") == "0xd2")
    capture = origin + round((ack909-origin)/PERIOD)*PERIOD
    m = transfers(folder)
    last = next(int(r["frame"]) for r in rows(folder/"window.csv") if r["event"] == "reveal" and r["g"] == "912")
    writes = read(temp / f"nes-hdma990-{mode}-p{phase}.json")
    assert writes["active_lengths"] == [21,21,21]
    return dict(writes=writes, hdma_minus_raw_ms=ms(max(writes["lengths_final"],writes["active_table_final"])-writes["raw_pixels_final"]),
                detail=detail, last_queue=ledger[-2], seal=m["seal"], upload=m["validated"], dma=m["dma"],
                reveal908=m["reveals"][908], ahead909_B=m["early909_B"], margin910_ms=ms(capture-last_d2),
                reveal911=m["reveals"][911], interval=m["interval911"], ahead911_B=m["early_B"],
                by246_B=m["completed_transfers_by_246_B"], six=last-m["reveals"][906][1],
                ACK912=joint["frames"][-1]["ACK_masterclock"], arm=joint["firmware_SHA256"], rom=sha(folder/"client.sfc"))


def analyze(temp, modes):
    result = dict(phases={}, budgets={}, guards={})
    for p in (1, 2):
        ref = directory(temp, p, "978returned", "cold")
        cases = result["phases"][p] = {m:measure(temp,p,m,ref) for m in ("ref", *modes)}
        control = cases["ref"]
        assert control["ACK912"] == read(ref/"joint.json")["frames"][-1]["ACK_masterclock"]
        gap = cases["safegap"]
        cutoff = read(Path("analysis/tile985-results.json"))["phases"][str(p)]["bound"]["cutoff_exclusive"]
        assert gap["dma"][2]["end"][1:] == [44,243] and gap["ahead911_B"] == gap["by246_B"] == 432
        budget = cutoff-gap["dma"][2]["end"][0]
        residual = sum(x["size"] for x in gap["dma"][3:])
        assert residual == 1248 and 0 < budget < residual*8
        measured = gap["reveal911"][0]-gap["dma"][3]["start"][0]
        gap["remaining_budget"] = dict(cutoff_exclusive=cutoff,available_clocks=budget,
                                      residual_bytes=residual,payload_only_clocks=residual*8,
                                      observed_raw_start_to_reveal=measured,
                                      latest_raw_start_line_at_observed_cost=247-measured/1364)
        for case in cases.values():
            case["delta_queue_ms"] = ms(case["last_queue"]["ack"]-control["last_queue"]["ack"])
            case["delta_ACK912_ms"] = ms(case["ACK912"]-control["ACK912"])
    for m in ("ref", *modes):
        root = BASE if m == "ref" else ROOT / m
        rom = PACKED if m == "ref" else ROOT / ("rom" if m == "late" else "repeat" if m.startswith(("repeat","rle")) else "compact")
        b = read(rom / "build.json")
        result["budgets"][m] = dict(flash_B=next((root/"link").rglob("firmware.stm")).stat().st_size,
                                   stored_ROM_B=64+b["loader_B"]+b["encoded_B"])
    result["planner_abort"] = {}
    for mode in ("early", "packed"):
        for phase in (1,2):
            folder = directory(temp,phase,"990"+mode,"cold")
            fault = read(folder/"fault.json")
            errors = {k:bytes.fromhex(v["bytes"])[v["layout"]["error"]] for k,v in fault.items()}
            last = rows(folder/"window.csv")[-1]
            assert int(last["g"]) == 909 and errors == {"plan":0,"sink":5,"transport":0}
            result["planner_abort"][f"{mode}-p{phase}"] = dict(errors=errors,last=last)
    for name in ("safegap-p1-missing_raw","safegap-p1-partial_raw","safegap-p1-damage",
                 "safegap-p1-stop_decode","safegap-p2-stop_decode","repeatgap-p1-damage",
                 "repeatgap-p1-stop_pending4","repeatgap-p2-stop_pending4"):
        f = temp / ("nes-hdma990-check-"+name) / "result.json"
        mode, phase, fault = name.split("-")
        ref = directory(temp, int(phase[1:]), "978returned", "cold")
        r = read(f)
        assert r["passed"] and r["commits"] == 6 and r["last_status"] == (228 if fault in ("stop_decode","stop_pending4") else 224)
        assert sha(f.parent/"retained.rgb") == sha(ref/"frame-910.rgb")
        result["guards"][name] = r["last_status"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("modes", nargs="+")
    a = parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.modes),indent=2)+"\n",encoding="utf-8")
