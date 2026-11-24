"""Compare byte-checked first E9 admission against the full eight-screen schedule."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from analyze_nes_chr951 import logtext
from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from check_nes_plan975 import FAULTS, directory, milliseconds, read, sha
from check_nes_tail979 import display
from check_nes_menu533 import check as menu
from nes_head980 import work, baseline
from test_nes_raw506_joint import PERIOD

TAGS = {0:"978returned", 2:"980checked2", 5:"980head5", 9:"980run8"}


def records(folder):
    return Counter((batch["g"], record) for batch in read(folder/"e9931.json") for record in batch["records"])


def measure(folder, ref):
    assert map_payloads(folder) == map_payloads(ref) and records(folder) == records(ref)
    assert all(sha(folder/f"frame-{g}.rgb") == sha(ref/f"frame-{g}.rgb") for g in range(905, 913))
    full = read(folder/"joint.json")
    assert full["passed"] and full["commits"] == 8
    events = read(folder/"events.json")
    planner, = (e["clock"] for e in events if e["generation"] == 911 and e["event"] == "planner_enter")
    spi = [e for e in events if e["generation"] == 911 and e.get("event") == "SPI"]
    e9 = [e for e in spi if e["opcode"] == "0xe9"]
    d = folder/"gen911"
    log = logtext(d/"admit980.log")
    assert "PASS954 prefix" in log and "Errors: 0" in log
    edge, length, count, crc = re.search(r"ACCEPT954 batch=0 edge=(\d+) bytes=(\d+) plans=(\d+) crc=([a-f0-9]+)", log).groups()
    accepted = int((d/"origin914.txt").read_text()) + int(edge)
    wire = bytes.fromhex(json.loads((folder/"e9wire914-911.jsonl").read_text().splitlines()[0])[1])
    assert int(length) == len(wire)-8 and int(count) == wire[3] and crc == wire[-4:-2].hex()
    assert abs(accepted-e9[0]["clock"]) < 2
    screen = display(folder)
    win = rows(folder/"window.csv")
    reveals = [int(x["frame"]) for x in win if x["event"] == "reveal"]
    assert len(reveals) == 8
    ack909 = max(int(x["clock"]) for x in win if x["g"] == "909" and x["event"] == "ack")
    ready, = (e["capture_ready"] for e in events if e["event"] == "source_begin" and e["generation"] == 911)
    target = ready-240*341*4
    target += round((ack909-target)/PERIOD)*PERIOD
    last_d2 = max(e["clock"] for e in events if e.get("input_generation") == 910 and e.get("opcode") == "0xd2")
    packets = [bytes.fromhex(json.loads(line)[2]) for line in (folder/"packets.jsonl").read_text().splitlines()]
    section = [(b[0], b[1]) for b in packets if int.from_bytes(b[8:10],"little") == 911]
    assert section[:3] == [(1,0),(2,5),(5,5)] and section[-1][0] == 3
    tiles = [r for r in map(json.loads,(folder/"producer.jsonl").read_text().splitlines()) if r["generation"] == 911]
    costs = {}
    for op in ("0xe9","0xe8","0xe1","0xe0"):
        transactions = [e for e in spi if e["opcode"] == op and planner <= e["start"] < screen["seal"][0]]
        costs[op] = dict(count=len(transactions), bytes=sum(e["bytes"] for e in transactions),
                         ms=milliseconds(sum(min(e["clock"],screen["seal"][0])-e["start"] for e in transactions)))
    return dict(planner=planner, first_issue=e9[0]["start"], first_RTL_accept=accepted,
                planner_to_first_issue_ms=milliseconds(e9[0]["start"]-planner),
                planner_to_first_accept_ms=milliseconds(accepted-planner), wire_B=[e["bytes"] for e in e9],
                tiles=[(r["kind"],r["bytes"],milliseconds(r["producer"]-planner)) for r in tiles],
                SPI_to_SEAL=costs, interval911=reveals[6]-reveals[5], dense6=reveals[-1]-reveals[1],
                capture_margin_ms=milliseconds(target-last_d2), ACK912=full["frames"][-1]["ACK_masterclock"],
                rgb_matches=8, firmware_sha256=full["firmware_SHA256"], rtl_log_sha256=sha(d/"admit980.log"), **screen)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a = p.parse_args()
    out = {"phases":{}, "guards":{}, "flash_B":{}, "menu":{}}
    for phase in (1,2):
        ref = directory(a.temp,phase,TAGS[0],"cold")
        data = out["phases"][phase] = {}
        for n,tag in TAGS.items():
            result = data[tag] = measure(directory(a.temp,phase,tag,"cold"),ref)
            image, = ((work(n) if n else baseline("returned"))/"link").rglob("firmware.stm")
            assert sha(image) == result["firmware_sha256"]
            out["flash_B"][tag] = image.stat().st_size
            result["ACK_change_ms"] = milliseconds(result["ACK912"]-data[TAGS[0]]["ACK912"])
            result["absolute_first_accept_change_ms"] = milliseconds(result["first_RTL_accept"]-data[TAGS[0]]["first_RTL_accept"])
    for n in (2,5,9):
        tag = TAGS[n]
        check = menu(work(n)/"link/src","966")
        assert check["rows"]["normal"]["released"]
        out["menu"][tag] = {mode:bool(row["released"]) for mode,row in check["rows"].items()}
        out["guards"][tag] = {}
        for fault,status in FAULTS.items():
            d = a.temp/f"nes-{tag}-{fault}"
            r = read(d/"result.json")
            assert r["passed"] and r["commits"]==6 and r["last_status"]==status
            assert sha(d/"retained.rgb")==sha(directory(a.temp,1,tag,"cold")/"frame-910.rgb")
            out["guards"][tag][fault] = status
    a.out.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
