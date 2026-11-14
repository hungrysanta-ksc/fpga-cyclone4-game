# SPDX-License-Identifier: MIT
"""Measure the original consumer and isolate tail wire packing with four FIFO credits."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as player
from analyze_nes_output768 import csv_groups, one, read
from nes_raw506 import once
from trace_nes_owner739 import observe


def run(a):
    a.frames = 66
    labels = read(a.client/"labels.json")
    events = [e for e in read(a.trace/"events.json") if e.get("generation")==969]
    tx = [e for e in events if e.get("opcode")=="0xe1"]

    def edit(script):
        samples = ["local seen779={}"]
        for name in ("header","data","data_size_ok","literal1814","accepted","reply","seal","validate181","coverage212","upload165_entry"):
            samples.append(f"""checkedMem527(function()
 if packet and pw(8)==969 and (pb(0)==3 or (pb(1)==5 and pw(12)==240)) and seen779['{name}']~=index then
  seen779['{name}']=index;sample516('tail779_{name}')
 end
end,emu.callbackType.exec,{labels[name]})""")
        script = once(script, "local function loaded()", "\n".join(samples)+"\nlocal function loaded()")
        if a.floor:
            path=a.out/"arrivals.tsv"
            rows=[r.split("\t") for r in path.read_text().splitlines()]
            ids=[i for i,(_,h,_) in enumerate(rows[:-1]) if bytes.fromhex(h)[8:10]==(969).to_bytes(2,"little")]
            packets=[bytes.fromhex(rows[i][1]) for i in ids]
            ordinary=[i for i,h in enumerate(packets) if h[0]==9 or h[1]==5]
            maps=[i for i,h in enumerate(packets) if h[1]==2]
            tiles=[i for i,h in enumerate(packets) if h[0]==7]
            seal=len(ids)-1
            assert len(tiles)==4 and len(ordinary)==9 and packets[seal][0]==3
            # Independent scheduling bound. Assume all tile descriptors can be
            # produced at output entry. Publish all heads with their measured wire
            # time and backpressure; runtime feasibility is checked by full links.
            prefix=next(i for i,t in enumerate(tx) if t["start"]>=one(events,"output_enter531")["clock"])
            order=list(range(prefix))+[i for i in maps if i>=prefix][:1]+tiles+ordinary+[i for i in maps if i>=prefix][1:]+[seal]
            assert sorted(order)==list(range(len(ids)))
            cursor=one(events,"output_enter531")["clock"]
            schedule=[]
            for new,i in enumerate(order[prefix:],prefix):
                _,h,b=rows[ids[i]]
                cursor+=tx[i]["clock"]-tx[i]["start"]
                schedule.append([str(round(cursor)),h[:4]+new.to_bytes(2,'little').hex()+h[8:],b])
            for dest,row in zip(ids[prefix:],schedule,strict=True):
                rows[dest]=row
            path.write_text("".join("\t".join(r)+"\n" for r in rows),newline="\n")
            instructions=",".join(f"[{ids[new]+1}]={{{round(tx[i]['clock']-tx[i]['start'])},{packets[i][0]}}}"
                                  for new,i in enumerate(order[prefix:],prefix))
            if a.hold:
                # Keep the original VRAM oracle, and wait for all five specified
                # destinations to pass it before allowing the SEAL wire to start.
                script=once(script,"local bytes532={}","local done779={};local gate779=nil;local bytes532={}")
                script=once(script,"  tile532=nil\n end", """  if word(0x1226)==969 then
   if t.dst==0 and t.n>=16 then done779[1]=true end
   if t.dst<=16448 and t.dst+t.n>=16480 then done779[2]=true end
  end
  tile532=nil
 end""")
                script=once(script,"end),emu.callbackType.exec,8269685)", """ if word(0x1226)==969 and done779[1] and done779[2] and not gate779 then
  local ready=true
  for _,off in ipairs({1216,1280,1344,2304,2368,2432,2496}) do ready=ready and copied526[off] end
  if ready then gate779=emu.getState().masterClock end
 end
end),emu.callbackType.exec,8269685)""")
            return enforce_wire(script,instructions)
        if not a.pack:
            return script
        path=a.out/"arrivals.tsv"
        rows=[r.split("\t") for r in path.read_text().splitlines()]
        ids=[i for i,(_,h,_) in enumerate(rows[:-1]) if bytes.fromhex(h)[8:10]==(969).to_bytes(2,"little")]
        packets=[bytes.fromhex(rows[i][1]) for i in ids]
        lastmap=max(i for i,h in enumerate(packets) if h[1]==2)
        ordinary=[i for i,h in enumerate(packets) if i>lastmap and (h[0]==9 or h[1]==5)]
        tiles=[i for i,h in enumerate(packets) if i>lastmap and h[0]==7]
        seal=len(ids)-1
        assert packets[seal][0]==3 and len(tiles)==2 and len(ordinary)+3==seal-lastmap
        # Give all ordinary data the most favorable release (last map PUSH).
        # Keep measured OBJ release times; each E1 still owns the common wire.
        order=[]
        cursor=tx[lastmap]["clock"]
        while ordinary or tiles:
            if tiles and (not ordinary or tx[tiles[0]]["start"]<=cursor):
                i=tiles.pop(0)
                cursor=max(cursor,tx[i]["start"])
            else:
                i=ordinary.pop(0)
            cursor+=tx[i]["clock"]-tx[i]["start"]
            order.append((i,cursor))
        order.append((seal,cursor+tx[seal]["clock"]-tx[seal]["start"]))
        durations=[]
        rewritten=[]
        for new_seq,(old,tick) in enumerate(order,lastmap+1):
            _,h,body=rows[ids[old]]
            durations.append((ids[new_seq]+1,round(tx[old]["clock"]-tx[old]["start"]),packets[old][0]))
            rewritten.append([str(round(tick)),h[:4]+new_seq.to_bytes(2,"little").hex()+h[8:],body])
        for idx,row in zip(ids[lastmap+1:],rewritten,strict=True):
            rows[idx]=row
        path.write_text("".join("\t".join(r)+"\n" for r in rows),newline="\n")
        instructions=",".join(f"[{index}]={{{duration},{op}}}" for index,duration,op in durations)
        return enforce_wire(script,instructions)

    def enforce_wire(script,instructions):
        script=once(script,"local finished522=false",f"local wire779={{{instructions}}};local wireEnd779=0;local bulk779=0\nlocal finished522=false")
        script=once(script," while now>=target522 do", """ while now>=target522 do
  local job=wire779[sent+1]
  if job then
   local endAt=math.max(target522,wireEnd779+job[1])
   if sent>=4 then
    if not retiredEvents[sent-3] then return end
    endAt=math.max(endAt,retiredEvents[sent-3][2]+job[1])
   end
   if (job[2]==7 or job[2]==3) and bulk779>0 then
    if not retiredEvents[bulk779] then return end
    endAt=math.max(endAt,retiredEvents[bulk779][2]+job[1])
   end
   if now<endAt then return end
   wireEnd779=endAt
   if job[2]==7 then bulk779=sent+1 end
  end""")

        if a.hold:
            script=once(script,"   if now<endAt then return end","""   if job[2]==3 then
    if not gate779 then return end
    endAt=math.max(endAt,gate779+job[1])
   end
   if now<endAt then return end""")
        return script

    def compare(old,new):
        assert [r for r in new if int(r["g"])<969]==[r for r in old if int(r["g"])<969]
        if not (a.pack or a.floor):
            assert [r for r in new if not r["event"].startswith("tail779_")]==old
        w=csv_groups(a.out/"window.csv")
        def mark(g,event):
            return one([r for r in w[g] if r["op"]==3],event)
        return dict(interval=mark(969,"reveal")["frame"]-mark(968,"reveal")["frame"],
                    seal=mark(969,"load")["clock"],upload=mark(969,"upload165_entry")["clock"],
                    ack969=mark(969,"ack")["clock"],ack970=mark(970,"ack")["clock"])
    with patch.object(player,"observe",observe):
        player.run(a,edit_script=edit,compare_trace=compare)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ("trace","client","mesen","out"):
        parser.add_argument("--"+n,type=Path,required=True)
    schedule=parser.add_mutually_exclusive_group()
    schedule.add_argument("--pack", action="store_true")
    schedule.add_argument("--floor", action="store_true")
    parser.add_argument("--hold", action="store_true",help="delay SEAL until five pre-DMA ranges pass VRAM checks in --floor mode")
    args=parser.parse_args()
    if args.hold and not args.floor:
        parser.error("--hold requires --floor")
    run(args)
