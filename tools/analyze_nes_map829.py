"""Tie the board, bus test, linked ARM and original 65816 display replay together."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map828 import analyze, CLOCK_MS, read, sha
from analyze_nes_output822 import resources, CLIENT
from prepare_nes_map828 import OUT, PROBES, ROOT


def validate_reads(folder, control, lookup):
    observations = []
    for line in (folder/"reads829.txt").read_text().splitlines():
        kind, *fields = line.split()
        if kind == "P":
            wire = bytes.fromhex(fields[0])
            expected = lookup[wire]
            generation = int.from_bytes(wire[8:10],"little")
            offset = int.from_bytes(wire[10:12],"little")
            map_bytes = (control/f"map-{generation}.bin").read_bytes()
            assert expected[16:] == map_bytes[offset:offset+len(expected)-16]
            cursor = 0
        elif kind == "R":
            address, value = [int(s,16) for s in fields]
            assert address == cursor and value == expected[cursor]
            cursor += 1
        else:
            assert kind=="A" and cursor==len(expected)
            observations.append((generation,len(wire)-16,cursor-16))
    return observations


def sample(folder, control, lookup, control_ack):
    row = analyze(folder,control,False)
    assert row["client"] == CLIENT
    for g in range(905,911):
        for prefix in ("map-","expected-","colors"):
            for f in control.glob(f"{prefix}{g}.bin"):
                assert f.read_bytes()==(folder/f.name).read_bytes()
    row.pop("RGB_SHA256")
    row["last_ack_delta_ms"]=round((row["last_ack"]-control_ack)/CLOCK_MS,6)
    if lookup is not None:
        counts=validate_reads(folder,control,lookup)
        row["compact_heads"]=len(counts)
        if "demoB" in folder.name:
            for g in (909,910):
                chosen=[r for r in counts if r[0]==g]
                assert len(chosen)==8 and sum(r[1] for r in chosen)==414 and sum(r[2] for r in chosen)==1472
    with (folder/"window.csv").open() as f:
        rows=list(csv.DictReader(f))
    row["seal_display"]=[
        [int(r["g"]),r["event"],int(r["clock"]),int(r["frame"]),int(r["line"])]
        for r in rows if r["g"] in ("908","909","910") and
        ((r["event"]=="load" and r["op"]=="3") or r["event"]=="reveal")]
    if "demoB" in folder.name:
        row["map_and_final_DMA"]={}
        for g in ("909","910"):
            seal=next(int(r["clock"]) for r in rows if r["g"]==g and r["event"]=="load" and r["op"]=="3")
            row["map_and_final_DMA"][g]=[
                [int(r["clock"]),int(r["frame"]),int(r["line"]),int(r["value"])] for r in rows
                if r["g"]==g and r["event"]=="ppu_dma" and (int(r["value"])>=1024 or int(r["clock"])>=seal)]
    return row


def run(temp,guard):
    assert "PASS829" in (guard/"map829_tb.log").read_text() and "PASS" in (guard/"progress680_tb.log").read_text()
    for f in (ROOT/"src/fpga/nes_map829").glob("*.sv"):
        assert sha(f)==sha(guard/f.name)==sha(temp/"nes-trial816-board829reserved"/f.name)
    lookup={}
    for line in (guard/"lut.txt").read_text().splitlines():
        wire,view=map(bytes.fromhex,line.split())
        assert lookup.setdefault(wire,view)==view
    results={}
    for group in ("earlyB","change","demoB"):
        for phase in (1,2):
            prefix=f"nes-tile821-{group}-jointmirror-p{phase}-"
            control=temp/(prefix+("827-mark-baseline" if group=="change" else "827control"))
            last=read(control,"joint.json")["frames"][-1]["ACK_masterclock"]
            result={"MMC826":sample(control,control,None,last)}
            # Original timing replays are checked byte-for-byte against the final board.
            for variant in ([""] if group!="demoB" else ["","split","one","two"]):
                folder=temp/(prefix+"829ref2"+variant)
                result[variant or "plain"]=sample(folder,control,lookup,last)
            rtl=temp/(prefix+"829rtlsplitlocal")
            replay=sample(rtl,control,lookup,last)
            if group=="demoB":
                assert replay==result["split"]
                if phase==1:
                    cold=temp/(prefix+"829coldsplitlocal")
                    assert sample(cold,control,lookup,last)==result["split"]
            else:
                result["split"]=replay
            results[f"{group}-{phase}"]=result
    protection={}
    for variant in ("split","one","two","plain"):
        dest=(OUT/"checks-link-right" if variant=="plain" else PROBES/"nes-map829"/("checks-"+variant))
        base=read(dest/"base","result.json")
        menu=read(dest,"menu.json")
        assert base["base_restored"] and base["safe_return"] and menu["rows"]["normal"]["released"]
        root=(OUT/"link-right" if variant=="plain" else PROBES/"nes-map829"/("link-"+variant))
        fw=root/"src/obj-nes-100/firmware.stm"
        assert all(results[f"demoB-{phase}"][variant]["ARM"]==sha(fw) for phase in (1,2))
        assert menu["firmware"]==sha(fw)
        protection[variant]=dict(Flash_B=fw.stat().st_size,BSS_B=int((root/"size.log").read_text().splitlines()[-1].split()[2]),
                                 SHA256=sha(fw),base_restored=base["base_restored"],safe_return=base["safe_return"],menu_released=True)
    boards={}
    for key in ("822held","829checked","829local","829port","829bound","829reserved"):
        # Intermediate layouts are optional when reproducing the final comparison.
        if key not in ("822held","829reserved") and not (temp/f"nes-trial816-board{key}").is_dir():
            continue
        boards[key]=resources(temp,key)
        summary=(temp/f"nes-trial816-board{key}/output_files/board.fit.summary").read_text()
        boards[key]["fitted"]="Fitter Status : Successful" in summary
        assert boards[key]["fitted"]==("min_slack_ns" in boards[key])
    return dict(scope="Six linked ARM/Mesen screens per clip. MMC826 SPI costs, modeled ROM grants and IRQ dispatch; physical FPS unmeasured. Separate pin-level Questa replay of E1, the actual consumer byte order, and ACK. Cold restart seeded with two partial WRAM maps.",
                board=boards,
                rtl=dict(heads=len((guard/"lut.txt").read_text().splitlines()),unique_heads=len(lookup),
                         vector_sha256=sha(guard/"stim.txt"),reads_sha256=sha(guard/"lut.txt"),source={f.name:sha(f) for f in (ROOT/"src/fpga/nes_map829").glob("*.sv")}),
                recovery=protection,clips=results)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("temp","guard","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.temp,a.guard),indent=2)+"\n")
