"""Measure both full links and exercise palette ownership on the actual receiver."""
import argparse
import json
from pathlib import Path

from check_nes_bg976 import map_payloads
from check_nes_blank959 import rows
from nes_blank960 import PACKED
from check_nes_menu533 import check as menu
from check_nes_plan975 import directory, milliseconds as ms, packet_path, read, replay, sha
from check_nes_tile985 import transfers
from nes_palette987 import ROM, WORK
from nes_raw506 import once
from test_nes_raw506_joint import PERIOD

FAULTS=("damage","owner","partial","stop","recover")


def exercise(t,p,fault):
    d=directory(t,p,"987palette","cold")
    cmds,_=packet_path(d,911,expected_shape=(14,3))
    labels=read(ROM/"labels.json")
    if fault in ("partial","owner"):
        # The normal capture schedules future PUSHes after successful credit
        # returns. Those credits never arrive once this particular head fails.
        stop=next(i for i,a in enumerate(cmds) if a[0]==911 and bytes.fromhex(a[3])[:2]==bytes((9,3)))
        cmds=cmds[:stop+1]
    out=guard_path(t,p,fault)
    snapshot=t/f"nes-palette987-stop-p{p}"/"interrupted.bin"
    def inspect(lua):
        if fault=="timing":
            return once(lua,"local function loaded()",f"""local timing987=assert(io.open(ROOT..'/compare.csv','w'))
local counts987={{}}
local comparing987=false
checkedMem527(function()
 if packet and pw(8)==911 then
  comparing987=true; timing987:write('chunk,'..emu.getState().masterClock..'\\n')
 end
end,emu.callbackType.exec,{labels['chunk987']})
checkedMem527(function(addr)
 if comparing987 then counts987[addr]=(counts987[addr] or 0)+1 end
end,emu.callbackType.read,0x7f6000,0x7fffff)
checkedMem527(function()
 if comparing987 then
  comparing987=false
  for _,base in ipairs({{0x7f6000,0x7fe000}}) do
   for i=0,511 do assert(counts987[base+i]==1, 'palette byte read count '..i) end
  end
  timing987:write('done,'..emu.getState().masterClock..'\\n');timing987:flush()
 end
end,emu.callbackType.exec,{labels['normal987']})
local function loaded()""")
        if fault=="recover":
            # Re-enter the real reset vector with both prior palettes and
            # receipt words from the interrupted run, before cold init.
            injected="""local stale987=file('interrupted.bin')
local pos987=1
for _,range in ipairs({{0x16000,512},{0x1e000,512},{0x14d0,12}}) do
 for i=0,range[2]-1 do emu.write(range[1]+i,stale987:byte(pos987)~(range[2]==512 and 255 or 0),emu.memType.snesWorkRam);pos987=pos987+1 end
end"""
            (out/"interrupted.bin").write_bytes(snapshot.read_bytes())
            return once(lua,"local index,retired",injected+"\nlocal index,retired")
        if fault=="owner":
            lua=once(lua,"if pb(0)==3 then\n   if MODE=='bad_version'", """if pb(0)==9 and pb(1)==3 then b[17]=b[17]~1 end
  if pb(0)==3 then
   if MODE=='bad_version'""")
        elif fault=="partial":
            # Send a valid shorter literal. A palette reuse requires exactly
            # 32 committed bytes; it may not fill the hole at byte 30.
            lua=once(lua,"packet=string.char(table.unpack(b))","""if pb(0)==2 and pb(1)==3 and pw(10)==0 then
   b[13]=30; b[#b]=nil; b[#b]=nil
  end
  packet=string.char(table.unpack(b))""")
        elif fault=="damage":
            lua=once(lua,'packet=requests[index];sample516',"""packet=requests[index]
 if pb(0)==3 and pw(8)==911 then
  assert(word(0x14da)==65534)
  local at=0x16000+word(0x1020)+511;emu.write(at,rd(at)~1,emu.memType.snesWorkRam)
 end
 sample516""")
        else:
            lua=once(lua,"local function loaded()",f"""local chunks987=0
checkedMem527(function()
 if packet and pw(8)==911 then chunks987=chunks987+1 end
end,emu.callbackType.exec,{labels['chunk987']})
local function loaded()""")
            lua=once(lua,"if MODE=='stop_decode'and decodeStart then return 128 end",
                     "if MODE=='stop_decode'and chunks987==2 then return 128 end")
        return once(lua,"if rejected then\n   local screen","""if rejected then
   for i=0,7 do assert(rd(0x14d0+i)==0,'fault kept ACK authority') end
   local memory=assert(io.open(ROOT..'/interrupted.bin','wb'))
   for _,range in ipairs({{0x16000,512},{0x1e000,512},{0x14d0,12}}) do
    for i=0,range[2]-1 do memory:write(string.char(rd(range[1]+i))) end
   end
   memory:close()
   local screen""")
    mode=None if fault in ("timing","recover") else "stop_decode" if fault=="stop" else "fault987"
    return replay(t,d,out,"fixed",cmds,911,mode,observe=inspect)


def guard_path(temp,phase,fault):
    suffix="-credit" if fault in ("partial","owner") else ""
    return temp/f"nes-palette987-{fault}-p{phase}{suffix}"


def analyze(t):
    image=next((WORK/"link").rglob("firmware.stm"))
    result=dict(phases={},flash_B=image.stat().st_size,firmware_sha256=sha(image),ROM_sha256=sha(ROM/"sink165.sfc"),
                physical_ROM_B=64+read(ROM/"build.json")["loader_B"]+read(ROM/"build.json")["encoded_B"],
                menu={k:v["released"] for k,v in menu(WORK/"link/src","966")["rows"].items()})
    for p in (1,2):
        cases={}
        for tag in ("978returned","987control","987palette"):
            d=directory(t,p,tag,"cold")
            ref=directory(t,p,"978returned","cold")
            assert sha(d/"client.sfc")==sha((PACKED if tag=="978returned" else ROM)/"sink165.sfc")
            assert map_payloads(d)==map_payloads(ref)
            assert [x["records"] for x in read(d/"e9931.json")]==[x["records"] for x in read(ref/"e9931.json")]
            assert all(sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
            m=transfers(d)
            cmds,q=packet_path(d,911,expected_shape=(14 if tag=="987palette" else 16,3))
            pal=[(a,b) for a,b in zip(cmds[-len(q):],q,strict=True) if b["section"]==3]
            for g in (905,906):
                cold=[bytes.fromhex(a[3]) for a in cmds if a[0]==g and bytes.fromhex(a[3])[1]==3]
                assert all(b[0] in (2,4) for b in cold)
                assert sum(int.from_bytes(b[12:14] if b[0]==2 else b[14:16],"little") for b in cold)==512
            events=read(d/"events.json")
            origin=next(e["capture_ready"] for e in events if e["event"]=="source_begin" and e["generation"]==911)-240*341*4
            frames=read(d/"joint.json")["frames"]
            ack909=next(f["ACK_masterclock"] for f in frames if f["generation"]==909)
            d2=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2")
            rv=next(x for x in rows(d/"window.csv") if x["g"]=="912" and x["event"]=="reveal")
            cases[tag]=dict(palette_wire=sum(len(bytes.fromhex(a[3]))+3 for a,b in pal),
                            palette_SPI_ms=ms(sum(b["arrive"]-b["issue"] for a,b in pal)),
                            palette_receiver_ms=ms(sum(b["ack"]-b["load"] for a,b in pal)),last_palette_ack=pal[-1][1]["ack"],
                            SEAL=m["seal"],upload=m["validated"],display911=m["reveals"][911],interval911=m["interval911"],
                            display908=m["reveals"][908],early909=m["early909_B"],capture910_ms=ms(origin+round((ack909-origin)/PERIOD)*PERIOD-d2),
                            six=int(rv["frame"])-m["reveals"][906][1],ack912=frames[-1]["ACK_masterclock"],dma=m["dma"])
        guard={}
        for fault in FAULTS:
            d=guard_path(t,p,fault);r=read(d/"result.json")
            assert r["passed"] and r["commits"]==(7 if fault=="recover" else 6)
            assert r["last_status"]==(1 if fault=="recover" else 228 if fault=="stop" else 224)
            if fault!="recover":
                assert sha(d/"retained.rgb")==sha(ref/"frame-910.rgb")
                assert len((d/"interrupted.bin").read_bytes())==1036
                tail=[x for x in rows(d/"window.csv") if x["g"]=="911" and x["event"]=="ack"]
                assert int(tail[-1]["op"])==(9 if fault in ("owner","partial") else 3)
                assert any(x["section"]=="3" and x["op"]=="2" and x["value"]=="0" for x in tail)
            guard[fault]=[r["commits"],r["last_status"]]
        timed=(t/f"nes-palette987-timing-p{p}"/"compare.csv").read_text().splitlines()
        assert [r.split(",")[0] for r in timed]==["chunk"]*8+["done"]
        times=[int(r.split(",")[1]) for r in timed]
        limit=read(Path("analysis/tile985-results.json"))["phases"][str(p)]["bound"]["cutoff_exclusive"]
        compare=times[-1]-times[0]
        margin=limit-cases["987palette"]["upload"][0]
        remaining=sum(v["size"] for v in cases["987palette"]["dma"] if v["size"]!=512)
        assert remaining==1168
        result["phases"][p]=dict(cases=cases,guards=guard,compare_clocks=times,compare_ms=ms(compare),
                                margin_after_upload_ms=ms(margin),margin_if_compare_free_ms=ms(margin+compare),
                                minimum_DMA_without_CGRAM_ms=ms(remaining*8))
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("temp",type=Path)
    parser.add_argument("--fault",choices=(*FAULTS,"timing"));parser.add_argument("--phase",type=int,choices=(1,2))
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    if a.fault:exercise(a.temp,a.phase,a.fault)
    else:a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n",encoding="utf-8")
