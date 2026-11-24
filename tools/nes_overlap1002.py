"""Replay generation 912 with two credits, byte-verified releases and tile-bank ownership."""
import argparse
import json
import math
import struct
from pathlib import Path

from check_nes_plan975 import directory, packet_path, read, replay, sha
from nes_dma1000 import PACKED, once


def ledger(temp, phase):
    d = directory(temp,phase,"978returned","cold")
    prof = directory(temp,phase,"1002ref","cold")
    for name in ("events.json","producer.jsonl","records.bin","window.csv"):
        assert sha(d/name)==sha(prof/name)
    m = read(temp/f"nes-1002ref-writes-p{phase}.json")
    last = {int(k):v for k,v in m["last"].items()}
    image = bytes.fromhex(m["image"])
    c, rows = packet_path(d,912,expected_shape=(21,8))
    events = read(d/"events.json")
    replies = {}
    for e in events:
        if e.get("opcode")=="0xe8" and e["generation"]==912:
            b=bytes.fromhex(e["reply"])
            if b[6] and int.from_bytes(b[12:14],"little")==912:
                replies.setdefault(int.from_bytes(b[14:18],"little"),e)
    tiles = {v["token"]:v for v in map(json.loads,(d/"producer.jsonl").read_text().splitlines()) if v["generation"]==912}
    returns = dict(read(d/"returns904.json"))
    canonical=[64*i+16*plane+b for plane in range(3) for i in range(32) for b in (0,1)]+list(range(2048,2291))+list(range(2292,2298))
    for cmd,j in zip(c[-21:],rows,strict=True):
        b=bytes.fromhex(cmd[3]); op,sec=b[:2]
        off,n,span=struct.unpack_from("<3H",b,10);span=span or n
        j.update(offset=off,span=span,wire_B=len(b)+3,duration=cmd[-1])
        if op==7:
            token=int.from_bytes(b[16:20],"little");tile=tiles[token];poll=replies[token]
            assert tile["producer"]<=math.ceil(poll["start"]) and poll["clock"]<=j["issue"]
            j.update(token=token,producer=tile["producer"],physical_return=returns[token],
                     e8_start=math.ceil(poll["start"]),e8_end=math.ceil(poll["clock"]),
                     e8_cost=math.ceil(poll["clock"]-poll["start"]),
                     fill_after_previous_return=max(0,tile["producer"]-returns[token-2]) if token>=33 else 0)
        elif op in (1,3):
            j["source"]=j["issue"] if op==1 else m["entry"]
        else:
            if sec==5 and off>=1121:
                ix=canonical[off-1121:off-1121+span]
                j["assembled"]=max(m["joined"][off-1121:off-1121+span])
            else:
                start={3:13344,4:12800,5:13856}[sec]+off
                ix=range(start,start+span)
            assert bytes(image[i] for i in ix)==(b[16:]*(1+span//n))[:span]
            j["source"]=max(last.get(i,0) for i in ix)
    return d,c,rows,events


# Compete for each free SPI interval. Physical queue service and bank return
# come from the running 65816. A long packet never blocks a shorter ready one.
SCHEDULER="""
  if operation=='EARLY' then
   if not inflight then
    if sent-retired>=2 then break end
    while busy[block] and now>=busy[block][2] do block=block+1 end
    local horizon=busy[block] and busy[block][1] or math.huge
    local picked,span,poll,credit=nil,0,0,0
    for i,j in ipairs(jobs1002) do
     if not j.sent and (not j.prev or jobs1002[j.prev].sent) and now>=j.ready
        and (j.op~=3 or issued1002==#jobs1002-1) then
      local release=j.token and j.token>=33 and returns1002[j.token-2] or 0
      local ok=not j.token or j.token<33 or returns1002[j.token-2]~=nil
      local query=0
      if j.token then
       if ok and now>=math.max(j.producer,release+j.fill) then
        if RETIME1002 or (j.token>=33 and release+j.fill>j.sample) then query=j.poll end
       else ok=false end
      end
      local status=0
      if not FREE1002 and retired>confirmed1002 and sent-confirmed1002>=2 then status=CREDIT1002 end
      local cost=j.duration+query+status
      if ok and now+cost<=horizon and (not picked or j.rank<jobs1002[picked].rank) then
       picked,span,poll,credit=i,cost,query,status
      end
     end
    end
    if not picked then break end
    local j=jobs1002[picked]
    if credit>0 then confirmed1002=retired end
    local bytes=unhex(j.hex)
    args={hex(bytes:sub(1,2)..string.pack('<I2',issued1002+1)..bytes:sub(5)),j.bulk}
    issued1002=issued1002+1;j.sent=true
    starts:write(j.id,' ',now+poll+credit,' ',now+span,' ',sent-retired,' ',poll,' ',credit,'\\n');starts:flush()
    target=now+span;inflight=true;break
   end
   inflight=false;operation='PUSH'
  end
"""


def run(temp,phase,mode,fault,audit=False,stage=False):
    d,cmds,rows,events=ledger(temp,phase)
    out=temp/(f"nes-overlap1002-{mode}-p{phase}"+("-"+fault if fault else "")+("-audit" if audit else "")+("-stage" if stage else ""))
    jobs=[];prior={}
    for cmd,j in zip(cmds[-20:],rows[1:],strict=True):
        op,sec=j["op"],j["section"]
        group="tiles" if op==7 else sec
        ready=(j["producer"] if mode in ("free","arb","tail") else j["e8_end"]) if op==7 else j.get("assembled",j["source"]) if mode=="joined" else j["source"]
        # Both release policies send the identical, independently checked bytes.
        b=bytearray.fromhex(cmd[3])
        if fault=="bad_seal" and op==3:b[8]^=1
        preferred = (op!=7) if mode=="tail" else (op==7)
        vals=dict(id=j["index"],op=op,hex=b.hex(),bulk=cmd[4],ready=ready,duration=j["duration"],
                  rank=(0 if preferred else 100)+j["index"])
        if op==7:
            vals.update(token=j["token"],producer=j["producer"],fill=j["fill_after_previous_return"],
                        sample=j["e8_start"],poll=j["e8_cost"])
        if group in prior:vals["prev"]=prior[group]
        prior[group]=len(jobs)+1
        jobs.append("{"+",".join(f"{k}={json.dumps(v)}" for k,v in vals.items())+"}")
    # The EARLY slots carry scheduling opportunities. Select the actual packet
    # in Lua, then assign the stream sequence used by the independent receiver.
    commands=[(*cmd[:5],0,cmd[-1]) if cmd[0]==912 and cmd[1]!=1 else cmd for cmd in cmds]
    def instrument(s):
        windows=[(math.floor(e["start"]),math.ceil(e["clock"])) for e in events
                 if "start" in e and e.get("opcode")!="0xe1" and mode!="free"
                 and not (mode in ("arb","tail") and e.get("generation")==912 and e.get("opcode") in ("0xe8","0xe0"))]
        assert windows==sorted(windows)
        (out/"busy.txt").write_text("".join(f"{a} {b}\n" for a,b in windows))
        cfg="local jobs1002={"+",".join(jobs)+"}\nlocal returns1002={}\nlocal issued1002=0\nlocal confirmed1002="+str(rows[0]["index"]-1)+"\n"
        s=once(s,"local function nextCommand()",cfg+"local function nextCommand()")
        s=once(s,'step920("consume920")','step920("consume920");returns1002[pw(16)+65536*pw(18)]=emu.getState().masterClock')
        lo=s.index("  if operation=='EARLY' then");hi=s.index("  if operation=='PUSH'then",lo)
        e0=max(math.ceil(e['clock']-e['start']) for e in events if e.get('generation')==912 and e.get('opcode')=='0xe0')
        s=s[:lo]+SCHEDULER.replace("FREE1002","true" if mode=="free" else "false").replace("RETIME1002","true" if mode in ("free","arb","tail") else "false").replace("CREDIT1002",str(e0))+s[hi:]
        pc=read(PACKED/"labels.json")["group_ready538"]
        anchor="local sequence=0;"
        s=once(s,anchor,f"checkedMem527(function()sample516('group1002')end,emu.callbackType.exec,{pc})\n"+anchor)
        if stage:
            from nes_stage1001 import observe
            s=observe(s,"paid")
        if audit:
            from nes_service1002 import instrument as count_service
            s=count_service(s)
        return s
    replay(temp,d,out,"fixed" if mode=="reference" else "frame",commands,912,fault,observe=instrument)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path);parser.add_argument("phase",type=int,choices=(1,2))
    parser.add_argument("mode",choices=("joined","source","free","arb","tail","reference"))
    parser.add_argument("--stage",action="store_true")
    parser.add_argument("--audit",action="store_true")
    parser.add_argument("--fault",choices=("bad_seal","stop_decode"))
    a=parser.parse_args();run(a.temp.resolve(),a.phase,a.mode,a.fault,a.audit,a.stage)
