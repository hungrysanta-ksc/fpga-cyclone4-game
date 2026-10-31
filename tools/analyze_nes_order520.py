# SPDX-License-Identifier: MIT
"""Price stable, packet-local OBJ ordering against the pinned 53-display baseline."""
import argparse
import json
from pathlib import Path

from analyze_nes_dense519 import consumed_tiles, interval, measure, ms
from run_nes_scroll229 import sha
from test_nes_service509_schedule import Calendar
from prepare_nes_dense519 import tile_digest, tiles

ROOT=Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text(encoding="utf8"))


def e9_lengths(folder):
    return [(e["generation"],e["bytes"]) for e in read(folder/"events.json")
            if e["event"]=="SPI" and e["opcode"]=="0xe9"]


def analyze(a):
    saved=read(ROOT/"analysis/dense519-verification.json")
    prior=saved["variants"]["baseline"]
    plans={f["generation"]:f for f in read(ROOT/"analysis/obj518-verification.json")["plans"]["frames"]}
    calendar=Calendar(a.calendar)
    guards=read(a.guards)
    assert guards["invalid_slot_and_tag_preserved_buffer"] and guards["blobs"]["candidate"]["flash_free_B"]>=0
    assert guards["changed_packets"] and 15 in guards["counts"] and 240 in guards["payload_lengths"]
    assert len(guards["cases"])==7 and all(row["finish"]==(row["mode"]=="normal") for row in guards["cases"])
    expected=tiles(a.fixture,957)
    assert tile_digest(expected)==saved["tile_sha256"] and sha(a.fixture/"requests.bin")==saved["fixture_sha256"]
    if a.start_clock==3000000:
        assert all(sha(a.baseline/key)==value for key,value in prior["pins"].items())
    parameters=dict(prior["parameters"],start=a.start_clock)
    assert e9_lengths(a.baseline)==e9_lengths(a.candidate)
    builds={}
    frames={}
    for name,folder in (("baseline",a.baseline),("candidate",a.candidate)):
        rows,joint=measure(folder,plans,guards["blobs"][name]["sha256"],calendar)
        assert joint["parameters"]==parameters and joint["client_SHA256"]==prior["client_sha256"]
        assert joint["ROM_read_allocations"]==prior["rom_reads"] and joint["max_bulk_banks"]<=2
        assert consumed_tiles(folder)==expected
        frames[name]=rows
        worst=max(rows[2:],key=lambda r:r["gap_ms"])
        builds[name]=dict(warm_ms=interval(rows,907,957),dense_ms=interval(rows,951,955),
                          worst_warm_ms=worst["gap_ms"],worst_warm_generation=worst["generation"],
                          display_clocks=[r["display_ack"] for r in rows],
                          heavy=[r for r in rows if 948<=r["generation"]<=957],
                          obj_bulk_dense=sum(r["obj_bulk"] for r in rows if 951<=r["generation"]<=955),
                          wire=joint["wire_B"],instructions=joint["ARM_instructions"],irqs=joint["SysTick_calls"],
                          rom_reads=joint["ROM_read_allocations"],bulk_banks=joint["max_bulk_banks"],
                          vram_dma_bytes=joint["vram_DMA_B"],snes_stack_bytes=joint["observed_stack_B"],
                          arm_test_stack_bytes=0x2000ff00-int(joint["observed_stack_low"],16),
                          pins={n:sha(folder/n) for n in prior["pins"]})
    if a.start_clock==3000000:
        assert builds["baseline"]["display_clocks"]==prior["display_clocks"]
    assert builds["candidate"]["vram_dma_bytes"]==builds["baseline"]["vram_dma_bytes"]
    changes=[]
    for old,new in zip(frames["baseline"],frames["candidate"]):
        g=old["generation"]
        assert g==new["generation"] and sha(a.baseline/f"frame-{g}.rgb")==sha(a.candidate/f"frame-{g}.rgb")
        assert old["obj_tiles"]==new["obj_tiles"]
        if old["obj_tiles"]:
            counts=[b["tiles"] for b in old["obj_batches"]]
            assert counts==[b["tiles"] for b in new["obj_batches"]]
        if old.get("obj_slot_order")!=new.get("obj_slot_order"):
            changes.append(g)
    return dict(scope="Fixed 905-957 inputs, same start and replayed ROM calendar. No physical FPS measurement.",
                start_clock=a.start_clock,builds=builds,changed_order_generations=changes,identical_displays=53,
                canonical_tiles=len(expected),identical_e9_transactions=len(e9_lengths(a.baseline)),
                final_ack_delta_ms=ms(builds["candidate"]["display_clocks"][-1]-builds["baseline"]["display_clocks"][-1]))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("baseline","candidate","second_baseline","second_candidate","guards","general_guards","fixture","calendar","out"):
        p.add_argument("--"+n.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    a.start_clock=3000000
    first=analyze(a)
    a.start_clock=3178684
    a.baseline,a.candidate=a.second_baseline,a.second_candidate
    second=analyze(a)
    general=read(a.general_guards)
    assert general["blobs"]["candidate"]["flash_free_B"]<0
    board=read(ROOT/"analysis/window516-verification.json")["boards"]["both"]
    image=read(ROOT/"analysis/window516-package.json")
    report=dict(reused_board={k:board[k] for k in ("LE","comb","FF","RAM_bits","M9K","SOF_SHA256")},
                reused_BI3_SHA256=image["BI3_SHA256"],scope="Two matched starting clocks, 53 consecutive displays each. No hardware FPS measurement.",
                guards=read(a.guards),rejected_general=general,phases=[first,second])
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8",newline="\n")
