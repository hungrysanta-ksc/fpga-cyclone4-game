"""Compare the actual linked planners, movement recorder and cartridge loader."""
import argparse
import json
from pathlib import Path

import check_carts1056 as carts
import check_dq4_movement1061 as movement
from check_ff3_battle1047 import captured, replay
from check_nes_retail_return1054 import run
from prepare_nes_compat1062 import MEASURE, BASE, OUT
from prepare_nes_carts1056 import OUT as CARTS
from check_ff3_sd1043 import Machine, fat16

def planner():
    log=OUT/"resume-5-vsim.log"
    assert "# PASS castle" in log.read_text()
    records=list(captured(log))
    assert len(records)==3
    result={}
    for cache_warm in (False,True):
        history={f:cache_warm for f,_ in records}
        pages={f:255 if cache_warm else 0 for f,_ in records}
        samples=[]
        for root in (MEASURE,OUT):
            samples.append(replay(root/"debug/link/src",records,history,True,1,pages=pages,
                                  profile=True,board_id=0x84))
        for a,b in zip(*samples):
            assert {k:v for k,v in a.items() if k!="planner_instructions"}=={k:v for k,v in b.items() if k!="planner_instructions"}
        result["retained" if cache_warm else "invalidated"]=samples
    # Same low index, different high tag and palette. Never alias a 14-bit
    # source tile even when the previous slot is at the same cache index.
    frame,geometry=records[0]
    geometry=list(geometry)
    geometry[0]=[(word&0xc000)|(0,256,512,8192,15871,16383)[i%6] for i,word in enumerate(geometry[0])]
    guards=[]
    for root in (MEASURE,OUT):
        guards.append(replay(root/"debug/link/src",[(frame,geometry)],{frame:False},True,1,pages={frame:0},board_id=0x84))
    assert guards[0]==guards[1]
    result["high_tag_alias_guard"]=guards[0]
    release=[]
    for root in (BASE,OUT):
        release.append(replay(root/"release/link/src",records,{f:True for f,_ in records},True,1,
                              pages={f:255 for f,_ in records},profile=True,board_id=0x84))
    for a,b in zip(*release):
        assert a["planner_instructions"]>b["planner_instructions"]
        assert {k:v for k,v in a.items() if k!="planner_instructions"}=={k:v for k,v in b.items() if k!="planner_instructions"}
    result["release_retained"]=release
    return result

def loader():
    folder=Path.home()/"Downloads/test"
    raw=(folder/"Tetris (j).nes").read_bytes()
    refs=json.loads((CARTS/"reference.json").read_text())
    result={}
    carts.OUT=OUT
    for mode in ("debug","release"):
        result[mode]=carts.headers(mode,refs)
        m=Machine(OUT/mode/"link/src",fat16())
        def classify(header,size,expected):
            m.u.mem_write(0x0807fc00,bytes(header))
            got=m.call("nes_image_id",0x0807fc00,size)
            assert got==expected,(mode,bytes(header).hex(),got,expected)
        classify(raw[:16],len(raw),0x81)
        h=bytearray(raw[:16]);h[6:9]=bytes((0x31,8,16))
        classify(h,len(raw),0x81)
        for index,val in ((8,32),(8,17),(6,0x30),(7,9),(6,0x35),(9,1),(10,7),(11,7),(12,1),(13,1),(14,1),(15,2)):
            copy=h.copy();copy[index]=val
            classify(copy,len(raw),0)
        ax=bytearray(16);ax[:12]=b"NES\x1a"+bytes((32,0,0x70,8,16,0,0,7))
        classify(ax,16+524288,0x82)
        for index,val in ((8,32),(10,7),(11,0),(11,0x70),(6,0x72)):
            copy=ax.copy();copy[index]=val
            classify(copy,16+524288,0)
        for pattern in ("Mother (*","Final Fantasy 1 & 2*","Zelda no Densetsu*","Metal Max*","Akumajou Densetsu*"):
            matches=list(folder.glob(pattern+".nes"));assert matches
            for path in matches:classify(path.read_bytes()[:16],path.stat().st_size,0)
    result["tetris_sd"]=run(0x81,OUT,1,raw=raw,image="/sd2snes/nes-m3.bi3")
    bad=bytearray(raw)
    bad[16]^=1
    result["crc_rejection"]=run(0x81,OUT,1,raw=bytes(bad),image="/sd2snes/nes-m3.bi3",reject_crc=True)
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("case",choices=("planner","loader","movement"))
    case=ap.parse_args().case
    movement.OUT=OUT
    result={"planner":planner,"loader":loader,"movement":movement.run}[case]()
    (OUT/(case+".json")).write_text(json.dumps(result,indent=2))
    print(case,"PASS")
