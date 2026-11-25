"""Decode a completed MMC1016 acquisition. Keep the NES and host clocks explicit."""
import argparse
import json
import struct
from pathlib import Path
from read_nes_display1010 import HEADER, ROW

CAP=80
META=16+CAP*ROW.size+8
SIZE=META+32+2048+ROW.size
NES_MS=16384/21477.272  # nominal NTSC; raw NES ticks are retained
HOST_MS=65536/84000

def events(words,generation):
    tiles=[]
    closed=True
    request=grant=overlap_start=None
    spans=[]
    last_stamp=0
    i=0
    while i<len(words):
        word=words[i]; i+=1
        op=word>>28
        if word==0xff000000:
            if not closed or len(tiles)!=15:
                raise ValueError("incomplete 15-tile stream")
            return tiles
        stamp=word&255
        if stamp<last_stamp:raise ValueError("backwards NES event")
        last_stamp=stamp
        if op in (10,11) and (request is not None or grant is not None or overlap_start is not None or spans):
            raise ValueError("unfinished operand at tile boundary")
        if op==10:
            if word&(1<<27):
                if closed:raise ValueError("unexpected previous-tile completion")
                tiles[-1]["done"]=word&255
                closed=True
            if not closed or i>=len(words) or words[i]!=(0xd0000000|generation):
                raise ValueError("tile boundary or generation mismatch")
            i+=1;closed=False
            tiles.append(dict(tag=(word>>8)&8191,kind=(word>>21)&3,start=word&255,reads=[]))
        elif op==11 and not closed:
            tiles[-1]["done"]=word&255;closed=True
        elif (op==8 or word<0x80000000) and not closed:
            response=op!=8
            flags=(word>>(25 if response else 8))&15
            stamp=word&255
            if flags&8:
                if request is not None:raise ValueError("duplicate foreground request")
                request=stamp
            if flags&4:
                if grant is not None or request is None:raise ValueError("unpaired ROM grant")
                grant=stamp
            if flags&2:
                if overlap_start is not None:raise ValueError("duplicate prefetch overlap")
                overlap_start=stamp
            if flags&1:
                if overlap_start is None:raise ValueError("unpaired prefetch release")
                spans.append([overlap_start,stamp]);overlap_start=None
            if not response:continue
            source=(word>>29)&3
            if source>2 or (source==2)!=(request is not None and grant is not None):
                raise ValueError("cache result and physical request/grant disagree")
            if (source!=2 and request is not None) or overlap_start is not None:
                raise ValueError("unfinished request")
            if source==2 and not tiles[-1]["start"]<=request<=grant<=stamp:
                raise ValueError("nonmonotonic ROM timing")
            tiles[-1]["reads"].append(dict(tag=(word>>12)&8191,plane=(word>>11)&1,row=(word>>8)&7,
                source=("capture_cache","row_cache","demand_ROM")[source],foreground_request=request,
                first_grant=grant,response=stamp,prefetch_overlap_seen=bool(spans),prefetch_overlap_intervals=spans,
                prefetch_overlap_ticks=sum(end-begin for begin,end in spans)))
            request=grant=None;spans=[]
        else:
            raise ValueError("invalid or saturated event stream")
    raise ValueError("missing end of trace")

def decode(raw):
    if len(raw)!=SIZE:raise ValueError("truncated MMC1016 log")
    magic,edition,mode,n,d0,d1,width,cap=HEADER.unpack_from(raw)
    if (magic,edition,width,cap)!=(0x9001,1016,ROW.size,CAP) or n>cap or mode>3:
        raise ValueError("wrong MMC1016 ABI")
    displayed,selected,pages,attempts=struct.unpack_from("<4H",raw,META-8)
    report=dict(rows=[],displayed55=displayed,dropped=[d0,d1],attempts=attempts,pages=pages,
                NES_tick_ms_nominal_NTSC=NES_MS,host_tick_ms=HOST_MS)
    for i in range(n):
        tick,g,bg,ia,ea,probe,obj,dirty,valid,bank,h,desc=ROW.unpack_from(raw,16+i*ROW.size)
        report["rows"].append(dict(tick=tick,generation=g,BG=bg,OBJ=obj,map=dirty,valid=valid,bank=bank))
    if not selected:return report
    if selected>n or not 1<=pages<=128:raise ValueError("invalid selection")
    row=report["rows"][selected-1]
    h=raw[META:META+32]
    gen=row["generation"]
    descriptor=ROW.unpack_from(raw,16+(selected-1)*ROW.size)[-1]
    token=int.from_bytes(h[4:8],"little")
    if not (row["valid"]==7 and row["BG"]==521 and row["OBJ"]==17 and row["map"]==23 and
            5900<=row["tick"]<6000 and h[1]==0xb6 and h[30:]==bytes((128,165)) and
            (h[27]&7)==3 and int.from_bytes(h[2:4],"little")==gen and
            struct.unpack("<BBHHHI",descriptor)==(1,1,64,480,gen,token)):
        raise ValueError("unverified target or final descriptor")
    tiles=events(struct.unpack_from(f"<{pages*4}I",raw,META+32),gen)
    chunks=[];pos=0
    for j,word in enumerate(struct.unpack_from("<3I",h,8)):
        kind=(word>>16)&1; units=(word>>8)&255; tok=(token-2+j)&0xffffffff
        stamp=word&255
        if not units or units%(1+kind) or word>>18!=(tok&2047):
            raise ValueError("invalid bank receipt")
        nt=units//(1+kind);bank=(word>>17)&1
        group=tiles[pos:pos+nt]
        if len(group)!=nt or any((t["kind"]==1)!=bool(kind) for t in group):
            raise ValueError("tile stream and returned bank disagree")
        chunks.append(dict(token=tok,bank=bank,bytes=units*16,first_tile=pos,
                           tile_count=nt,return_host_tick=stamp))
        pos+=nt
    if (pos!=15 or chunks[-1]["bytes"]!=64 or chunks[-1]["tile_count"]!=2 or
        any(b["return_host_tick"]<a["return_host_tick"] or a["bank"]==b["bank"] for a,b in zip(chunks,chunks[1:]))):
        raise ValueError("inconsistent returned banks")
    for i,t in enumerate(tiles):
        stamps=[t["start"]]
        for r in t["reads"]:stamps.extend(v for v in (r["foreground_request"],r["first_grant"],r["response"]) if v is not None)
        stamps.append(t["done"])
        if stamps!=sorted(stamps) or (i and tiles[i-1]["done"]>t["start"]):
            raise ValueError("overlapping tile execution")
    report["detail"]=dict(generation=gen,first_E9_to_last_publish_host_ticks=h[24],tiles=tiles,chunks=chunks)
    return report

def compare(first,second):
    """Compare only identical tile/operand order and bank boundaries."""
    a,b=first.get("detail"),second.get("detail")
    if not a or not b:return dict(comparable=False,reason="one or both runs have no complete selection")
    differences=[]
    def change(tile,field,left,right,tick):
        if left!=right:
            differences.append(dict(tile=tile,field=field,first=left,second=right,
                delta_ms=(right-left)*tick if tick and left is not None and right is not None else None))
    def shape(t):
        return (t["kind"],t["tag"],[(r["tag"],r["plane"],r["row"]) for r in t["reads"]])
    if list(map(shape,a["tiles"]))!=list(map(shape,b["tiles"])):
        return dict(comparable=False,reason="different CHR tag, row, plane or tile sequence")
    keys=("first_tile","tile_count","bytes")
    if [[x[k] for k in keys] for x in a["chunks"]]!=[[x[k] for k in keys] for x in b["chunks"]]:
        return dict(comparable=False,reason="different bank group boundaries")
    for i,(ta,tb) in enumerate(zip(a["tiles"],b["tiles"])):
        change(i,"start",ta["start"],tb["start"],NES_MS)
        for j,(ra,rb) in enumerate(zip(ta["reads"],tb["reads"])):
            for key in ("source","foreground_request","first_grant","prefetch_overlap_seen","prefetch_overlap_ticks","response"):
                change(i,f"read[{j}].{key}",ra[key],rb[key],NES_MS if key not in ("source","prefetch_overlap_seen") else None)
        change(i,"done",ta["done"],tb["done"],NES_MS)
    returns=[]
    for x,y in zip(a["chunks"],b["chunks"]):
        returns.append(dict(first_tile=x["first_tile"],bytes=x["bytes"],first=x["return_host_tick"],
            second=y["return_host_tick"],delta_ms=(y["return_host_tick"]-x["return_host_tick"])*HOST_MS))
    # Two staging banks alternate. Only a later group reusing the same bank
    # can depend on its return. Keep rounding bounds, including origin CDC.
    bounds=[]
    for run in (a,b):
        reuse=[]
        for i,previous in enumerate(run["chunks"]):
            later=next((c for c in run["chunks"][i+1:] if c["bank"]==previous["bank"]),None)
            if later is None:continue
            start=run["tiles"][later["first_tile"]]["start"]
            ret=previous["return_host_tick"]
            origin_sync_ms=3/21477.272
            reuse.append(dict(bank=previous["bank"],returned_token=previous["token"],
                reused_token=later["token"],tile_start_minus_return_ms_bounds=[
                    start*NES_MS-(ret+1)*HOST_MS,(start+1)*NES_MS+origin_sync_ms-ret*HOST_MS]))
        bounds.append(reuse)
    return dict(comparable=True,generations=[a["generation"],b["generation"]],
                first_different_operand_event=next(iter(differences),None),differences=differences,bank_returns=returns,bank_reuse_bounds_by_run=bounds)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("log",type=Path)
    p.add_argument("second",type=Path,nargs="?")
    args=p.parse_args()
    first=decode(args.log.read_bytes())
    result=compare(first,decode(args.second.read_bytes())) if args.second else first
    print(json.dumps(result,indent=2))
