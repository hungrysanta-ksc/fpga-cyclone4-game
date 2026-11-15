# SPDX-License-Identifier: MIT
"""Bound first-blank map and tile admission on the original MMC763 consumer."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from analyze_nes_output768 import csv_groups, read
from replay_nes_tail779 import run

ROOT = Path(__file__).resolve().parents[1]


def replay(temp, client, mesen, phase, maps, tiles, real_obj=False, hold=True, order="original", lead=0, advance=0):
    base = temp / f"nes-cost768-763-p{phase}-ext"
    key = f"m{maps}t{tiles}" + ("-ready" if real_obj else "") + ("" if hold else "-free")
    if order != "original":
        key += "-" + order
    if lead:
        key += f"-lead{lead}"
    if advance:
        key += f"-advance{advance}"
    out = temp / f"nes-first780-{key}-p{phase}"
    first = read(ROOT / "analysis/range778.json")["phases"][str(phase)]["763"]["first_end246"]

    def schedule(packets, tx, _events):
        # Preserve per-section offsets and token order. Indices are determined
        # by decoded headers. Every transfer occupies its measured E1 duration.
        def offset(i):
            return int.from_bytes(packets[i][10:12], "little")
        map_heads = [i for i,h in enumerate(packets) if h[1] == 2]
        tile_heads = [i for i,h in enumerate(packets) if h[0] == 7]
        ordinary = [i for i,h in enumerate(packets) if h[0] == 9 or h[1] == 5]
        assert [offset(i) for i in map_heads] == [256,448,1024,1216,2304,2496,3072,3264]
        assert [offset(i) for i in tile_heads] == [0,64,128,256]
        early = sorted(map_heads[:3+maps] + tile_heads[:tiles])
        if order == "map":
            early = map_heads[:3+maps] + tile_heads[:tiles]
        elif order == "tile":
            early = tile_heads[:tiles] + map_heads[:3+maps]
        rest = sorted(set(map_heads[:6] + tile_heads[:2]) - set(early))
        late = rest + tile_heads[2:] + ordinary + map_heads[6:] + [len(packets)-1]
        # First possible cycle after line 261. NTSC's short line is 240.
        barriers = {late[0]:first+15*1364}
        if real_obj:
            for i in tile_heads[2:]:
                barriers[i] = max(barriers.get(i,0), tx[i]["start"]-advance*1364)
        if lead:
            # Advance the generation release, including BEGIN wire occupation.
            # Require prior display ACK before the hypothetical new BEGIN.
            ack, = [r["clock"] for r in csv_groups(base/"window.csv")[968]
                    if r["op"]==3 and r["event"]=="ack"]
            start=tx[0]["start"]-lead*1364
            assert start>=ack
            return 0,[0]+early+late,start,barriers
        return 1,[0]+early+late,tx[0]["clock"],barriers

    args = SimpleNamespace(trace=base, client=client, mesen=mesen, out=out, floor=True, hold=hold, pack=False)
    run(args, schedule)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("temp","client","mesen"):
        p.add_argument(arg,type=Path)
    p.add_argument("--case",action="append",nargs=2,type=int,metavar=("MAP","TILE"))
    p.add_argument("--real-obj",action="store_true")
    p.add_argument("--lead",type=int,choices=(0,16),default=0,help="diagnostic earlier BEGIN in scanlines")
    p.add_argument("--advance",type=int,default=0,help="advance the measured final two OBJ releases by this many scanlines")
    p.add_argument("--order",choices=("original","map","tile"),default="original")
    p.add_argument("--no-hold",action="store_true",help="allow normal post-SEAL DMA; keep original coverage and final VRAM checks")
    p.add_argument("--jobs",type=int,default=3)
    a=p.parse_args()
    if a.advance and not a.real_obj:
        p.error("--advance requires --real-obj")
    cases=a.case or [(m,t) for m in range(4) for t in range(3)]
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        jobs=[pool.submit(replay,a.temp,a.client,a.mesen,phase,m,t,a.real_obj,not a.no_hold,a.order,a.lead,a.advance)
              for m,t in cases for phase in (1,2)]
        for job in jobs:
            job.result()
