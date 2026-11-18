"""Compare actual wire maps, independently rendered output, decode service and final display."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from prepare_nes_map828 import OUT, PROBES, ROOT

CLOCK_MS = 21477.272
def read(folder, name):
    return json.loads((folder/name).read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def analyze(folder, control, target):
    result=read(folder,"joint.json")
    assert result["passed"] and result["commits"]==6 and result["last_status"]==1
    for g in range(905,911):
        assert (folder/f"frame-{g}.rgb").read_bytes()==(control/f"frame-{g}.rgb").read_bytes(),(folder,g)
    rows=list(csv.DictReader((folder/"window.csv").open()))
    reveals=[(int(r["frame"]),int(r["clock"])) for r in rows if r["event"]=="reveal" and int(r["g"])>=906]
    assert len(reveals)==5
    out=dict(display_VBlanks=[b[0]-a[0] for a,b in zip(reveals,reveals[1:])],
             display_ms=round((reveals[-1][1]-reveals[0][1])/CLOCK_MS,6),
             last_ack=result["frames"][-1]["ACK_masterclock"],commits=6,
             RGB_SHA256=[sha(folder/f"frame-{g}.rgb") for g in range(905,911)],
             ARM=result["firmware_SHA256"], client=result["client_SHA256"])
    if not target:
        return out
    packets=[bytes.fromhex(json.loads(x)[2]) for x in (folder/"packets.jsonl").read_text().splitlines()]
    if (folder/"codec828.csv").exists():
        with (folder/"codec828.csv").open() as stream:
            codec=list(csv.reader(stream))
    else:
        codec=[]
    for g in (909,910):
        chosen=[(i,b) for i,b in enumerate(packets,1) if b[1]==2 and int.from_bytes(b[8:10],"little")==g]
        expected=(control/f"map-{g}.bin").read_bytes()
        wire=expanded=service=0
        offsets=[]
        for i,b in chosen:
            at=int.from_bytes(b[10:12],"little")
            offsets.append(at)
            raw=b[16:]
            wire+=len(raw)
            if b[0]==9:
                assert len(raw) in (18,36,54) and b[14:16]==bytes(2)
                raw=b"".join(raw[x:x+18]+bytes(46) for x in range(0,len(raw),18))
            else:
                assert b[0]==2
            assert raw==expected[at:at+len(raw)]
            expanded+=len(raw)
            times={r["event"]:int(r["clock"]) for r in rows if int(r["index"])==i and r["event"] in ("load","ack")}
            service+=times["ack"]-times["load"]
        assert offsets==list(range(2048,3393,192)) and expanded==1472
        assert wire==(414 if codec else 1472)
        timed=[(r[3],int(r[4])) for r in codec if int(r[0])==g]
        assert [e for e,t in timed]==["begin","verified"]*(8 if codec else 0)
        out[str(g)]=dict(map_wire_B=wire,expanded_B=expanded,map_packets=len(chosen),
                 decode_readback_service_ms=round(sum(b[1]-a[1] for a,b in zip(timed[::2],timed[1::2]))/CLOCK_MS,6),
                 head_to_packet_ack_ms=round(service/CLOCK_MS,6))
    return out

def run(temp):
    results={}
    for group in ("demoB","earlyB","late","change","demoD"):
        for phase in (1,2):
            prefix=f"nes-tile821-{group}-jointmirror-p{phase}-"
            ref=temp/(prefix+("827control" if group in ("demoB","earlyB") else "827-mark-baseline"))
            variants={"MMC826":ref,"fast":temp/(prefix+"828fast")}
            if group=="demoB":
                variants["rom_control"]=temp/(prefix+"828boot")
            if group in ("earlyB","demoB","change"):
                variants["word"]=temp/(prefix+"828b")
                variants["right"]=temp/(prefix+"828right")
            rows={k:analyze(path,ref,group=="demoB") for k,path in variants.items()}
            results[f"{group}-{phase}"]=rows
    guards={}
    for fault,code in (("damage",224),("stop",228)):
        d=temp/f"nes-tile821-demoB-jointmirror-p1-828guard{fault}"
        r=read(d,"result.json")
        assert r["commits"]==4 and r["last_status"]==code and r["passed"]
        assert (d/"retained.rgb").read_bytes()==(d/"frame-908.rgb").read_bytes()
        guards[fault]=dict(status=code,last_displayed=908,partial_map=sha(d/"canceled-map.bin"))
    recovered=temp/"nes-tile821-demoB-jointmirror-p1-828cold"
    guards["cold_restart"]=analyze(recovered,temp/"nes-tile821-demoB-jointmirror-p1-827control",True)
    for link in ("link-c","link-right"):
        dest=OUT/("checks-"+link)
        checks={n:read(dest,n+".json") for n in ("menu","windows","reports")}
        checks["base"]=read(dest/"base","result.json")
        assert checks["base"]["safe_return"]==1 and checks["base"]["base_restored"]==1
        assert checks["menu"]["rows"]["normal"]["released"] and checks["windows"]["layout"]=="demo"
        guards[link]=checks
    sizes={}
    for n,d in (("MMC826",PROBES/"nes-output823/link-826"),("broad",OUT/"link-c"),("right",OUT/"link-right")):
        fw=d/"src/obj-nes-100/firmware.stm"
        sizes[n]=dict(flash=fw.stat().st_size,space=212992-fw.stat().st_size,firmware=sha(fw),
                      bss=int((d/"size.log").read_text().splitlines()[-1].split()[2]))
    for n in ("client-b","client-fast"):
        b=read(OUT/n,"build.json")
        sizes[n]={k:b[k] for k in ("physical_ROM_B","body_bytes","loader_B","prefix_B","physical_free_B")}
    return dict(scope="Linked Cortex-M4 and Mesen 65816; MMC826 measured SPI cost and modeled ROM calendar; no hardware FPS",sizes=sizes,runs=results,guards=guards)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(run(a.temp),indent=2)+"\n")
