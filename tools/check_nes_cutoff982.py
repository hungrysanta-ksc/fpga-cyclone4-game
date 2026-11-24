"""Reconcile the measured SEAL path with the scanline deadline and packet 135."""
import argparse
import json
import math
from pathlib import Path

from check_nes_blank959 import rows
from check_nes_plan975 import directory, milliseconds, packet_path, read, sha


def measure(temp, phase, mode):
    original=directory(temp,phase,"978returned" if mode=="ref" else "981pair","cold")
    d=temp/f"nes-cutoff982-{mode}-p{phase}"
    trace=rows(d/"window.csv")
    hooks=rows(d/"clocks982.csv")
    commands,_=packet_path(original,911)
    def ticks(name):
        return int(next(r["clock"] for r in hooks if r["event"]==name and r["index"]=="174"))
    marks=[(name,ticks(name)) for name in ("seal","validate181","scroll_end181","table181",
            "table_end181","coverage212","map_coverage212","local165_entry","upload165_entry")]
    costs={a:milliseconds(y-x) for (a,x),(_,y) in zip(marks,marks[1:])}
    def events(gen,event):
        return [r for r in trace if r["g"]==str(gen) and r["event"]==event]
    def first(gen,event):
        return int(events(gen,event)[0]["clock"])
    seal=next(r for r in hooks if r["event"]=="seal" and r["index"]=="174")
    # Treat the entire 246th line as usable. The real admission test can
    # reject earlier. The 1360-clock NTSC short line is outside this interval.
    cutoff=int(seal["clock"])+(247-int(seal["line"]))*1364-int(seal["h"])
    available=cutoff-int(seal["clock"])
    dma=events(911,"ppu_dma")
    assert [int(r["value"]) for r in dma]==[16,32,384,64,64,64,512,544]
    assert len({r["frame"] for r in dma})==1
    palette_start=int(dma[-2]["clock"])
    color_tail=first(911,"reveal")-palette_start
    assert color_tail>8*1056
    early=[r for r in events(909,"ppu_dma") if int(r["frame"])<int(events(909,"reveal")[0]["frame"])]
    candidate_next=next(r for r in events(909,"load") if r["index"]=="135")
    prior=next(r for r in events(909,"ack") if r["index"]=="134")
    cmd=commands[134]
    assert cmd[0]==909 and bytes.fromhex(cmd[3])[16:20]==bytes.fromhex("16000000")
    shifts=read(d/"retimed982.json")
    arrived=int(cmd[2]) if not shifts else math.ceil(shifts[0][2])
    committed=read(d/"result.json")
    assert committed["passed"] and committed["commits"]==7
    assert all(sha(d/f"frame-{g}.rgb")==sha(original/f"frame-{g}.rgb") for g in range(905,912))
    return dict(provenance={f:sha(d/f) for f in ("client.sfc","clocks982.csv","window.csv","retimed982.json")},
                seal_beam=[int(seal["line"]),int(seal["h"])],stage_clocks=dict(marks),stage_ms=costs,
                last_table_return_to_SEAL_load_ms=milliseconds(
                    int(events(911,"load")[-1]["clock"])-int(events(911,"ack")[-2]["clock"])),
                available_after_seal_clocks=available,available_after_seal_ms=milliseconds(available),
                cutoff_exclusive_clock=cutoff,
                # This is a lower bound on transfer alone, not a display prediction.
                ideal_wire_margin_ms={str(size):milliseconds(available-8*size) for size in (1680,1248,1056)},
                measured_palette_DMA_to_reveal_ms=milliseconds(color_tail),
                margin_if_only_measured_color_tail_at_SEAL_ms=milliseconds(available-color_tail),
                dma911=[int(r["value"]) for r in dma],
                display911_interval=int(events(911,"reveal")[0]["frame"])-int(events(910,"reveal")[0]["frame"]),
                displays={g:dict(reveal=first(g,"reveal"),vblank=int(events(g,"reveal")[0]["frame"]),
                                 ack=int(events(g,"ack")[-1]["clock"])) for g in (908,909,910,911)},
                capture909=dict(previous_packet_ack=int(prior["clock"]),token22_arrival=arrived,
                                token22_load=int(candidate_next["clock"]),empty_queue_DMA=[
                                    [int(r["clock"]),int(r["line"]),int(r["value"])] for r in early],
                                early_B=sum(int(r["value"]) for r in early)),
                hashes_match_through_911=True,retimed_SPI=shifts)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    data={p:{m:measure(args.temp,p,m) for m in ("ref","pair","defer")} for p in (1,2)}
    for phase,runs in data.items():
        assert runs["ref"]["capture909"]["early_B"]==624
        assert runs["pair"]["capture909"]["early_B"]==(592 if phase==1 else 624)
        assert runs["defer"]["capture909"]["early_B"]==624
        assert runs["defer"]["displays"][909]==runs["ref"]["displays"][909]
        assert all(r["display911_interval"]==2 for r in runs.values())
    guards={}
    source=directory(args.temp,1,"981pair","cold")
    for fault,status in (("bad_seal",224),("stop_decode",228)):
        path=args.temp/f"nes-cutoff982-defer-p1-{fault}"
        result=read(path/"result.json")
        assert result["passed"] and result["commits"]==6 and result["last_status"]==status
        retained=sha(path/"retained.rgb")
        assert retained==sha(source/"frame-910.rgb")
        guards[fault]=dict(commits=6,last_status=status,retained_rgb_sha256=retained)
    args.output.write_text(json.dumps(dict(phases=data,guards=guards),indent=2)+"\n")
