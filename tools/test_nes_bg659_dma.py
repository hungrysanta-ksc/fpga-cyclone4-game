"""Execute 16-byte DMA subroutine at 637's upload entry, with timed cartridge read responses.
Harness supplies the accepted job descriptors. No modified firmware is packaged."""
import argparse,json,runpy,struct,sys
from pathlib import Path
from unittest.mock import patch
import test_nes_raw506_joint as joint
from test_nes_service509_schedule import Calendar
from check_nes_fault641 import evidence
from check_nes_reference658 import sha
from nes_raw506 import once


def routine():
    code=bytearray();labels={};fix=[]
    def emit(*b):code.extend(b)
    def label(k):labels[k]=len(code)
    def rel(op,k):emit(op,0);fix.append((len(code)-1,k))
    # DBR 0, M=8, X=16. $e0..e2 is saved across this diagnostic call.
    emit(0xda,0x5a,0xa5,0xe2,0x48,0xc2,0x20,0xa5,0xe0,0x48,0xe2,0x20,0xa2,0,0)
    label("tile")
    emit(0xc2,0x20,0xbf,0,0x3e,0x7e,0x85,0xe0,0x8d,2,0x43,0xa9,16,0,0x8d,5,0x43,
         0xe2,0x20,0xbf,2,0x3e,0x7e,0x8d,4,0x43,0x18,0x69,2,0x85,0xe2,0x87,0xe0)
    label("poll");emit(0xad,0x12,0x42);rel(0x10,"fail");emit(0xa7,0xe0);rel(0x30,"fail");emit(0x29,1);rel(0xf0,"poll")
    # Channel mode, VRAM destination and increment are already configured by 637.
    emit(0xa9,1,0x8d,0x0b,0x42,0xa7,0xe0,0xc9,2);rel(0xd0,"fail")
    emit(0xe8,0xe8,0xe8,0xec,0xe0,0x0e);rel(0x90,"tile");rel(0x80,"return")
    label("fail");emit(0xa9,1,0x8f,0,0x60,0x5f);label("stop");rel(0x80,"stop")
    label("return");emit(0xa9,0x7f,0x8d,4,0x43,0xc2,0x20,0x68,0x85,0xe0,0xe2,0x20,0x68,0x85,0xe2,0x7a,0xfa,0xa9,1,0x60)
    for at,name in fix:
        distance=labels[name]-at-1;assert -128<=distance<128;code[at]=distance&255
    return bytes(code)


def setup(a,opts,old):
    old(a)
    root=a.out
    game=opts.game.read_bytes()
    assert sha(game)==evidence("mmc480-verification.json")["live_functional"]["rom_sha256"]
    chrdata=game[-131072:]
    (root/"chr659.bin").write_bytes(bytes(chrdata[(i&~15)+(i%2)*8+((i%16)//2)] for i in range(len(chrdata))))
    jobs={}
    for g in (954,955):
        jobs[g]={}
        for bank,row in json.loads((a.plans/f"frame{g}/plans.json").read_bytes()):
            p=bytes.fromhex(row);gen,slot,tag,kind,mask=struct.unpack_from("<HHHBB",p)
            if kind!=0:continue
            assert gen==g and p[8:24]==bytes(i//2 for i in range(16)) and p[24:]==b"\xff"*16
            jobs[g][(32768 if bank else 0)+slot*16]=tag
    cal=Calendar(opts.calendar659)
    window=Path(__file__).with_name("nes_bg659_window.lua").read_text()
    window=window.replace("MODE659",repr(opts.mode)).replace("TARGET659",str(opts.target)).replace("PERIOD659",str(cal.period))
    window=window.replace("STARTS659",",".join(str(g) for g,r in cal.pairs)).replace("ENDS659",",".join(str(r) for g,r in cal.pairs))
    window=window.replace("JOBS659",",".join("["+str(k)+"]={"+",".join(f"[{x}]={v}" for x,v in plan.items())+"}" for k,plan in jobs.items()))
    window=window.replace("CODE659",",".join(map(str,routine())))
    if opts.published:
        start=window.index("local function replaceDMA")
        end=window.index("checkedMem527(function(a,v)\n base=",start)
        window=window[:start]+"""checkedMem527(function()
 local g=word(0x1226);return jobs[g] and (target==0 or target==g) and 1 or 0
end,emu.callbackType.read,0x540000)
"""+window[end:]
        window=window.replace("0x5f6000","0x546000")
    path=root/"capture.lua";s=path.read_text(encoding="utf-8")
    path.write_text(once(s,"local function write(a,v)",window+"\nlocal function write(a,v)"),encoding="utf-8",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument("--mode",choices=("open","calendar"),required=True)
    p.add_argument("--target",type=int,default=0);p.add_argument("--game",type=Path,required=True)
    p.add_argument("--published",type=Path)
    a,rest=p.parse_known_args();a.calendar659=Path(rest[rest.index("--calendar")+1]);sys.argv[1:]=rest
    # Wrap the finished chain of Lua instrumentation (at Link construction).
    original=joint.Link.__init__
    def init(self,opts):
        writer=joint.lua_rpc
        with patch.object(joint,"lua_rpc",lambda cfg:setup(cfg,a,writer)): original(self,opts)
    import test_nes_bg659_sensitivity as timing
    timing.selected={a.target} if a.target else {954,955}
    from trace_nes_obj518 import ObjLink
    accept=ObjLink.accept
    descriptors=json.loads(a.published.read_bytes()) if a.published else {}
    def accept_jobs(link,tx,t):
        g=link.generation
        if descriptors and g in timing.selected and tx[0]==0xe9:
            for q in link.plansets[g][link.plan_at:link.plan_at+tx[3]]:
                if q[6]==0:
                    slot=struct.unpack_from("<H",q,2)[0]
                    link.tilebytes[g,0,16*slot]=bytes.fromhex(descriptors[f"{g}/{slot}"])
        return accept(link,tx,t)
    with patch.object(joint.Link,"__init__",init),patch.object(ObjLink,"accept",accept_jobs),patch.object(runpy,"run_module",timing.shortcut):
        runpy.run_module("test_nes_direct653",run_name="__main__")
