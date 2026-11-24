"""Verify packet-admission proofs and final display timing against the 978 replay."""
import argparse
import json
from pathlib import Path

from check_nes_blank959 import directory, sha
from check_nes_dma1000 import records
from check_nes_output970 import counters
from nes_stage1001 import ORIGIN, PACKED, candidate
from pack_nes_column854 import encode


def packing(table):
    body = bytearray((PACKED / "body.bin").read_bytes())
    old = len(body)
    build = json.loads((PACKED / "build.json").read_bytes())
    assert len(encode(bytes(body), 0, 2, short_pairs=True)) == build["encoded_B"]
    for address, blob in candidate(False, table).items():
        start = address - ORIGIN
        assert 0 <= start <= len(body)
        body[start:start + len(blob)] = blob
    packed = len(encode(bytes(body), 0, 2, short_pairs=True))
    return dict(added_code=len(body)-old, encoded=packed, loader=build["loader_B"],
                free=build["physical_free_B"]+build["encoded_B"]-packed)


def phase(temp, p):
    src = directory(temp, p, "978returned", "cold")
    baseline = counters(src, 912)
    prefix = [r for r in records(src / "window.csv") if int(r["g"]) < 912]
    early = sum(int(r["value"]) for r in prefix if r["g"] == "909" and
                r["event"] == "ppu_dma" and r["op"] == "-1")
    assert early == 624
    events = json.loads((src / "events.json").read_bytes())
    d2 = max(e["clock"] for e in events if e.get("input_generation") == 910 and e.get("opcode") == "0xd2")
    control = temp / f"nes-dma1000-control-p{p}"
    latch = next(r for r in records(control / "seal528.csv") if r["g"] == "912" and r["event"] == "latch")
    end = int(latch["clock"]) + (247-int(latch["line"]))*1364 - int(latch["h"])
    result = dict(linked_978=baseline, end246_vb46=end, early_909_B=early,
                  reveal908=counters(src,908)["reveal"], input910_last_D2=d2,
                  events_sha256=sha(src/"events.json"), normal={}, guards={})
    result["late_returns_978"] = [{key:int(row[key]) for key in ("index","op","section","clock")}
                                  for row in records(src/"window.csv") if row["g"]=="912" and row["event"]=="ack"
                                  and row["op"]!="3" and int(row["clock"])>=end]
    for mode in ("recorded","paid","begin","fresh","tablerecorded","table","tablebegin","tablefresh"):
        d = temp / (f"nes-stage1001-{mode}-p{p}" if mode.endswith("recorded") else
                    f"nes-dma1000-1001{mode}-p{p}" + ("-begin" if mode.endswith("begin") else ""))
        frames = json.loads((d / "result.json").read_bytes())
        assert frames["passed"] and frames["commits"] == 8
        assert all(sha(d/f"frame-{g}.rgb")==sha(src/f"frame-{g}.rgb") for g in range(905,913))
        rows = records(d / "window.csv")
        assert [r for r in rows if int(r["g"]) < 912] == prefix
        c = counters(d,912)
        assert c["reveal"][1] == 47
        c["ACK_delta_vs_978"] = c["ack"][0]-baseline["ack"][0]
        rows = [r for r in rows if r["g"] == "912"]
        tail = [r for r in rows if r["op"] == "3"]
        dma = [[int(r[k]) for k in ("clock","frame","line","value")] for r in tail if r["event"]=="ppu_dma"]
        assert [r[-1] for r in dma[-2:]] == [512,544]
        c["DMA_clock_VBlank_line_bytes"] = dma
        table_idx = max(int(r["index"]) for r in rows if (r["op"],r["section"])==("2","5"))
        table_packet = [int(r["clock"]) for r in rows if int(r["index"])==table_idx and r["event"] in ("load","ack")]
        assert len(table_packet) == 2
        c["last_table_receiver_clocks"] = table_packet[1]-table_packet[0]
        if mode.startswith("table"):
            proof = {r["event"][6:]:int(r["clock"]) for r in tail if r["event"].startswith("p1001_")}
            assert "proof_hit" in proof and "fallback" not in proof
            c["seal_steps"] = proof
        if mode.endswith("fresh"):
            assert c["reveal"][2] == 246
        result["normal"][mode] = c
    for mode,fault in (("paid","bad_seal"),("paid","stop_raw"),("table","bad_seal"),("table","stop_raw"),("tablecorrupt","bad_seal"),("tablecoverage","bad_seal")):
        d = temp / f"nes-dma1000-1001{mode}-p{p}-{fault}"
        state = json.loads((d/"result.json").read_bytes())
        assert state["passed"] and state["commits"] == 7 and state["last_status"] == (228 if fault=="stop_raw" else 224)
        assert sha(d/"retained.rgb") == sha(src/"frame-911.rgb")
        marks = [r["event"] for r in records(d/"window.csv") if r["g"]=="912" and r["op"]=="3"]
        assert "reveal" not in marks
        if mode=="tablecorrupt":
            assert "p1001_mismatch" in marks and "p1001_fallback" in marks
        if mode=="tablecoverage":
            assert "p1001_proof_hit" in marks and "p1001_coverage212" in marks
        result["guards"][mode+"_"+fault] = dict(status=state["last_status"], retained=911, events=marks)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    data = dict(packing={k:packing(v) for k,v in (("dma",False),("dma_table",True))},
                phases={p:phase(a.temp,p) for p in (1,2)})
    a.output.write_text(json.dumps(data, indent=2)+"\n", encoding="utf8", newline="\n")
