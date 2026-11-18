"""Build warm paired Adventure Island IV workloads from actual MMC820 geometry and its linked ARM planner."""
import json
import struct
from pathlib import Path
from check_nes_mask820 import inputs
from check_nes_game478 import Machine
from build_nes_game164 import palette
from test_nes_obj609 import lanes
from analyze_nes_scroll229 import FETCH,records
from check_nes_snoop601 import samples
from prepare_nes_opening818 import ADVENTURE_SHA
from nes_raw506 import sha

def obj_lines(writes,fold):
    lines={}
    for kind,addr,value in writes:
        if kind!=1:
            continue
        tag=addr//16
        index=(tag^(tag>>7) if fold else tag)&127
        if index not in lines or lines[index][0]!=tag:
            lines[index]=(tag,{})
        lines[index][1][addr%16]=value
    return lines


def frame_fetches(capture):
    if not (capture/"ppu-fetch.bin").is_file():
        def one(frame):
            path=capture/str(frame)/"ppu-fetch.bin"
            return records(path,FETCH) if path.is_file() else None
        return one
    byframe={}
    for row in records(capture/"ppu-fetch.bin",FETCH):byframe.setdefault(row[0],[]).append(row)
    return byframe.get


def prepare(rtl,capture,rom,src,out,groups=None):
    assert sha(rom)==ADVENTURE_SHA
    chr=rom.read_bytes()[-131072:]
    out.mkdir(parents=True,exist_ok=False)
    fetch=frame_fetches(capture)
    for group,first in groups or (("early",660),("late",1320),("earlyB",700),("lateB",1440),("demo",2700),
                                  ("demoA",2440),("demoB",2560),("demoC",2860),("demoD",3110)):
        frames=range(first,first+24,4) if isinstance(first,int) else first
        if fetch(frames[0]) is None:continue
        base=out/group
        base.mkdir()
        machine=Machine(src,palette())
        summary=[]
        bundle=bytearray()
        index=0
        cache={}
        folded={}
        for serial,f in enumerate(frames,1):
            g=904+serial
            d=base/f"frame{g}"
            d.mkdir()
            packets,geo,raw,_=inputs(rtl,f,wire_generation=g)
            (d/"packets.json").write_text(json.dumps([p.hex() for p in packets]))
            result=machine.frame(packets,geo,raw,g,serial)
            read=lambda base,data,field,n:bytes(machine.u.mem_read(base+machine.layout[data][field],n))
            video=lambda field,n:read(machine.video,"nes_native_video165",field,n)
            for suffix,data in (("geometry",geo),("raw",raw)):(base/f"frame{g}.{suffix}").write_bytes(data)
            hdma=video("hdma",1121)
            patch=video("patch",2298)
            hdma=(hdma+patch[:2291]+patch[2292:]) if len(raw) else hdma[:int.from_bytes(video("hdma_size",2),"little")]
            (base/f"expected-{g}.bin").write_bytes(hdma)
            (base/f"map-{g}.bin").write_bytes(video("map",4096))
            (base/f"colors636-{g}.bin").write_bytes(video("cgram",512)+video("oam",544))
            (d/"plans.json").write_text(json.dumps(machine.plans))
            bg=obj=0
            for _,hx in machine.plans:
                q=bytes.fromhex(hx)
                _,slot,tag,k,mask=struct.unpack_from("<3H2B",q)
                kind=int(k==1)
                size=32 if kind else 16
                bg+=int(k==0)
                obj+=kind
                payload=bytearray(size)
                if k!=2:
                    for j,addr in lanes(q):payload[j]=chr[addr]
                packet=struct.pack("<BBHIHHHHI",7,kind,0,1,g,slot*size,4,size,index)
                index+=1
                bundle.extend(struct.pack("<H",len(packet))+packet)
                (base/f"tile-{index:04}.bin").write_bytes(payload)
            writes,_=samples(fetch(f),rtl/f"frame{f}.hex",chr)
            cache[g]=obj_lines(writes,False)
            folded[g]=obj_lines(writes,True)
            hits=int.from_bytes(read(machine.resident,"nes_resident211","hits",4),"little")
            summary.append(dict(source_frame=f,g=g,bg_new=bg,obj_new=obj,resident_hits=hits,mapdirty=int.from_bytes(video("map_dirty",8),"little").bit_count(),tile_bytes=16*bg+32*obj))
        (base/"requests.bin").write_bytes(bundle)
        (base/"work.json").write_text(json.dumps(summary))
        (base/"cache.json").write_text(json.dumps(cache))
        (base/"folded.json").write_text(json.dumps(folded))
        print(group,summary,flush=True)

if __name__=="__main__":
    import sys
    prepare(*[Path(s).resolve() for s in sys.argv[1:]])
