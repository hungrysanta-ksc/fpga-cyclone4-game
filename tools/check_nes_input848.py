"""Measure board D1 transactions for a geometry corpus, then check the receiver's restored bytes."""
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

from build_nes_game164 import palette
from check_nes_game478 import Machine, sha
from check_nes_sender652 import prepare
from check_nes_serial654 import bench
from nes_direct653 import encode


def run(board, data, arm, out):
    if os.environ.get("SALT_LICENSE_SERVER") != "18000@localhost":
        raise RuntimeError("Run inside the project FLOAT wrapper")
    work = json.loads((data / "work.json").read_text())
    gens = [row["g"] for row in work]
    assert gens == list(range(905, 905 + len(work)))
    args = SimpleNamespace(board=board, data=data, out=out, guards=False,
                           bin=Path("C:/altera_standard/25.1std/questa_fse/win64"))
    prepare(args, encoder=encode, codec="nes_geometry_sender653.sv", bench=bench, generations=gens)
    replies = json.loads((out / "sender.json").read_text())
    machine = Machine(arm, palette())
    frames = []
    for serial, row in enumerate(work, 1):
        g = row["g"]
        packets = [bytes.fromhex(r["wire"]) for r in replies[str(g)]]
        result = machine.frame(packets, (data / f"frame{g}.geometry").read_bytes(),
                               (data / f"frame{g}.raw").read_bytes(), g, serial)
        original = json.loads((data / f"frame{g}" / "packets.json").read_text())
        assert json.loads(json.dumps(result["plans"])) == json.loads((data / f"frame{g}" / "plans.json").read_text())
        frames.append(dict(source=row["source_frame"], generation=g, transactions=len(packets),
                           board_D1_B=sum(len(p) + 3 for p in packets),
                           replay_D1_B=sum(len(bytes.fromhex(p)) + 3 for p in original),
                           receive_instructions=result["receive_instructions"],
                           planner_instructions=result["planner_instructions"]))
    sources = {p.name: sha(p) for p in out.glob("nes_*.sv")}
    (out / "verified.json").write_text(json.dumps(dict(rtl=sources,
        arm=sha(arm / "obj-nes-100/firmware.stm"), frames=frames), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("board", "data", "arm", "out"):
        parser.add_argument(arg, type=Path)
    run(**vars(parser.parse_args()))
