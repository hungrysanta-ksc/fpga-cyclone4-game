"""Run the linked Kirby receiver and planner on captures exported by the board RTL."""
import argparse
import json
from pathlib import Path
import struct
from binascii import crc_hqx
from build_nes_game164 import palette
from check_nes_game478 import Machine
from check_nes_mask820 import inputs
from compare_nes_mask820 import compare
from cross_nes1022 import rom_path


def run(src, replay, capture, out, rom):
    rawcart=rom.read_bytes()
    chrrom=rawcart[16+rawcart[4]*16384:]
    out.mkdir(parents=True,exist_ok=True)
    (out/"chr.hex").write_text("\n".join(f"{v:02x}" for v in chrrom)+"\n")
    results=[]
    vectors=[]
    for cfg in sorted(replay.glob("frame*.cfg")):
        f=int(cfg.stem[5:])
        m=Machine(src,palette(),buffers=(0x20008000,0x2000c000,0x20011000,0x20014000))
        packets,geo,raw,gen=inputs(replay,f,kirby14=True)
        blocks=[bytes.fromhex(s) for s in (replay/f"frame{f}.d1").read_text().splitlines()]
        assert all(crc_hqx(b[:-2],65535)==int.from_bytes(b[-2:],"big") for b in blocks)
        packets=[b[:-2] for b in blocks]
        m.packets=packets
        m.index=0
        m.start_token=0
        m.prepared=False
        m.spi_calls=0
        buf=0x20015000
        for token,b in enumerate(packets):
            if m.state_value()==2:
                assert m.call("nes_native165_prepare",[m.state,1,m.spi|1,0])==1
            m.u.mem_write(buf,b)
            assert m.call("nes_native165_packet",[m.state,token,buf,len(b)])==1,(f,token,m.state_value())
        assert m.state_value()==4
        get=lambda base,key,off,n: bytes(m.u.mem_read(base+m.layout[key][off],n))
        counts=struct.unpack_from("<6H",geo,5728)
        for kind,(field,width,offset) in enumerate(zip(("maps","rows","objects","exceptions","raster","palette"),(2,1,8,4,8,1),(0,2112,2336,3360,3872,5664))):
            if field=="exceptions":
                # The oracle holds the complete 33-bit field from the synchronous RTL query.
                expected={int(i):int(v,16) for k,i,v in (row.split() for row in (replay/f"frame{f}.query").read_text().splitlines()) if k=="3"}
                reference=b"".join((expected[i]&0xffffffff).to_bytes(4,"little") for i in range(counts[kind]))
                hi=get(m.state,"nes_native165","exception_hi",16)
                assert all((hi[i//8]>>(i%8)&1)==v>>32 for i,v in expected.items())
            else:
                reference=geo[offset:offset+counts[kind]*width]
            assert get(m.state,"nes_native165",field,len(reference))==reference,field
        assert get(m.state,"nes_native165","raw_pixels",len(raw))==raw
        assert m.call("nes_resident211_begin",[m.resident,1,1,gen,m.writer|1,0])==1
        assert m.call("nes_native_video211_plan",[m.state,m.lut,m.video,m.resident])==1,("planner",f,get(m.video,"nes_native_video165","error",1))
        d=out/str(f)
        d.mkdir(exist_ok=True)
        (d/"geometry.bin").write_bytes(geo)
        (d/"display_mask.bin").write_bytes(get(m.video,"nes_native_video165","display_mask",1))
        (d/"plans.json").write_text(json.dumps(m.plans))
        layout=m.layout["nes_plan200"]
        for _,q in m.plans:
            m.u.mem_write(buf,bytes.fromhex(q))
            service=buf+256
            m.u.mem_write(service,bytes(layout["size"]))
            assert m.call("append",[service,buf])==1
            size=int.from_bytes(m.u.mem_read(service+layout["bytes"],2),"little")
            encoded=bytes(m.u.mem_read(service+layout["buffer"]+4,size))
            assert 3<=size<=32
            vectors.append(f"{f} {gen} {size} {crc_hqx(encoded,65535):04x} "+encoded.hex(" "))
        for key,n in (("map",4096),("cgram",512),("oam",544),("hofs",448),("vofs",448),("patch",2298)):
            (d/(key+".bin")).write_bytes(get(m.video,"nes_native_video165",key,n))
        report=compare(out,capture,chrrom,f,clip_left=True)
        tags=[struct.unpack_from("<H",bytes.fromhex(q),4)[0] for _,q in m.plans]
        print(f,len(tags),sum(t>=8192 for t in tags),report["errors"],flush=True)
        results.append(dict(frame=f,plans=len(tags),upper=sum(t>=8192 for t in tags),errors=report["errors"],rows=report["rows"]))
    (out/"pixels.json").write_text(json.dumps(results,indent=2))
    (out/"plans.txt").write_text("\n".join(vectors)+"\n")
    assert all(row["errors"]==0 for row in results)


def compare_rtl(out,capture,rom):
    raw=rom.read_bytes()
    chrrom=raw[16+raw[4]*16384:]
    frames={}
    for line in (out/"tiles.txt").read_text().splitlines():
        frame,kind,slot,index,value=line.split()
        tile=frames.setdefault(int(frame),{}).setdefault((int(kind)==1,int(slot)),bytearray())
        assert int(index)==len(tile)
        tile.append(int(value,16))
    results=[]
    for frame,slots in sorted(frames.items()):
        gfx={}
        for key,tile in slots.items():
            assert len(tile)==(32 if key[0] else 16) and not any(tile[16:])
            gfx[key]=list(zip(tile[:16:2],tile[1:16:2]))
        result=compare(out,capture,chrrom,frame,hardware_tiles=gfx,clip_left=True)
        assert result["errors"]==0
        plans=json.loads((out/str(frame)/"plans.json").read_text())
        high={int.from_bytes(bytes.fromhex(p)[4:6],"little") for _,p in plans}
        aliases=sum(chrrom[t*16:t*16+16]!=chrrom[(t-8192)*16:(t-8192)*16+16] for t in high if t>=8192)
        results.append(dict(frame=frame,pixels=256*224,errors=result["errors"],distinct_upper_tags_with_different_lower_tile=aliases))
    assert [r["frame"] for r in results]==[750,1830,3030,3570] and all(r["distinct_upper_tags_with_different_lower_tile"] for r in results)
    (out/"rtl-pixels.json").write_text(json.dumps(results,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("src","replay","capture","out"):
        p.add_argument(arg,type=Path)
    a=p.parse_args()
    run(a.src,a.replay,a.capture,a.out,rom_path(Path.home()/"Downloads/test","kirby"))
