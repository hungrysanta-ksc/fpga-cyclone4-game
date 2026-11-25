"""Feed the fitted exporter's records to the final ARM ELF and retain its tile plans and display data."""
import json
import struct
import sys
from pathlib import Path
from check_nes_game478 import Machine
from build_nes_game164 import palette


def inputs(folder, f, *, wire_generation=None, kirby14=False):
    gen, patches, obj, exc, groups, pals = map(int,(folder/f"frame{f}.cfg").read_text().split())
    counts = (33*groups,224,obj,exc,224,32*pals)
    geometry=bytearray(5741)
    raw=bytearray(patches*256)
    sizes=(2,1,8,4,8,1)
    offsets=(0,2112,2336,3360,3872,5664)
    seen={}
    for line in (folder/f"frame{f}.query").read_text().splitlines():
        kind,idx,val=line.split()
        k,i,v=int(kind),int(idx),int(val,16)
        assert seen.setdefault((k,i),v)==v
        if k==7:
            raw[i]=v
        elif k<6:
            off=offsets[k]+i*sizes[k]
            # Legacy compact test fixture stores the exception position and low 13 tag bits.
            # The Kirby checker compares the full exception from the separate query stream.
            stored = v & 0xffffffff if kirby14 and k==3 else v
            geometry[off:off+sizes[k]]=stored.to_bytes(sizes[k],"little")
    assert len(seen)==sum(counts)+len(raw)
    struct.pack_into("<6HB",geometry,5728,*counts,patches)
    packets=[]
    block=bytearray()
    for line in (folder/f"frame{f}.wire").read_text().splitlines():
        word=int(line,16)
        k,i=(word>>93),(word>>64)&8191
        assert ((word>>77)&65535)==gen
        width=8 if k==0 and i&4096 else (2,1,7,4,7,1,2,8)[k]
        if kirby14 and k==3:
            width=5
        payload=word&((1<<64)-1)
        # Bit 63 is the FPGA ingress flush strobe on map cells. Feed the
        # receiver's ordinary uncompressed map representation in this replay.
        if k==0:
            payload &= ~(1<<63)
        rec=struct.pack(">HH",k<<13|i,gen if wire_generation is None else wire_generation)+payload.to_bytes(width,"big")
        if len(block)+len(rec)>256 or (k,i)==(7,3):
            packets.append(bytes(block))
            block.clear()
        block+=rec
    packets.append(bytes(block))
    return packets,geometry,raw,gen


def run(src,folder,out):
    out.mkdir(exist_ok=False,parents=True)
    for f in sorted(int(p.stem[5:]) for p in folder.glob("frame*.cfg")):
        machine=Machine(src,palette())
        pkt,geo,raw,gen=inputs(folder,f)
        result=machine.frame(pkt,geo,raw,gen,1)
        d=out/str(f)
        d.mkdir()
        (d/"plans.json").write_text(json.dumps(machine.plans))
        layout=machine.layout["nes_native_video165"]
        for key,n in (("map",4096),("cgram",512),("oam",544),("hofs",448),("vofs",448),
                      ("hdma",1121),("patch",2048+3*81+1+6)):
            (d/(key+".bin")).write_bytes(machine.u.mem_read(machine.video+layout[key],n))
        (d/"geometry.bin").write_bytes(geo)
        (d/"raw.bin").write_bytes(raw)
        print(f,len(machine.plans),len(raw),result["source_SPI_calls"],flush=True)


if __name__=="__main__":
    run(*[Path(s).resolve() for s in sys.argv[1:]])
