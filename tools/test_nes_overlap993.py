"""Measure a fixed OBJ-prefix diagnostic and inject STOP and a damaged table."""
import argparse
from pathlib import Path

from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw506 import once


def run(t,phase,case,mode="both"):
    base=case=="instant"
    d=directory(t,phase,"978returned" if base else "993"+mode,"cold")
    cmds,ledger=packet_path(d,911)
    folder={"instant":"instant2","stop":"stop3"}.get(case,case)
    out=t/f"nes-overlap993-{mode}-{folder}-p{phase}"
    src=next(i for i,c in enumerate(cmds) if c[0]==911 and (h:=bytes.fromhex(c[3]))[:2]==bytes((2,5)) and int.from_bytes(h[10:12],"little")==1322)
    if case=="stop":
        cmds=cmds[:next(i for i in range(src+1,len(cmds)) if cmds[i][1]==8)+1]
    def observe(lua):
        if base:
            # All SPI transactions that have already started at the second OBJ
            # return finish at the baseline clock. Later submissions are free
            # in this diagnostic. Actual FIFO space and receipt checks still run.
            last_obj=next(r for r in reversed(ledger) if r["op"]==7)
            cut=last_obj["ack"]
            fixed=max(r["arrive"] for r in ledger if r["issue"]<=cut)
            wires=[]
            commands=(out/"commands.txt").read_text().splitlines()
            for r in ledger:
                if r["issue"]<=cut:continue
                i=5*(r["index"]-1)
                assert commands[i+2]=="PUSH" and int(commands[i+1])==r["arrive"]
                commands[i+1:i+3]=[str(max(cut,fixed)),"EARLY"]
                wires.append("0")
            (out/"commands.txt").write_text("\n".join(commands)+"\n",newline="\n")
            (out/"wire.txt").write_text("\n".join(wires)+"\n")
            return lua
        if case=="live":
            return lua
        if case=="stop":
            lua=once(lua,"local function loaded()","local stopAt993=nil\nlocal function loaded()")
            lua=once(lua,'sample516("load");reads=0','if pw(8)==911 and pb(1)==5 and pw(10)==1322 then stopAt993=emu.getState().frameCount end\n sample516("load");reads=0')
            lua=once(lua," if a==0x6001 then"," if a==0x6001 then\n  if stopAt993 then return 128 end")
            lua=once(lua,"if (rejected or index>TOTAL)and not packet and st.frameCount>shown+2 then",
                     "if stopAt993 and st.frameCount>=stopAt993+4 then")
            lua=once(lua,"assert(not rejected==(MODE=='normal'),'unexpected reject')",
                     f"assert(index=={src+2} and sent>retired and not rejected and not packet and lastStatus==0 and word(0x1248)==6 and word(0x124a)==0,'held STOP advanced the queue or display')")
            return once(lua,"if rejected then\n   local screen","if stopAt993 then\n   local screen")
        # Damage the terminating/count field of the received first HDMA stream.
        return once(lua,'sample516("load");reads=0','''if pw(8)==911 and pb(0)==3 then
 local x=0x10000+word(0x1020)+0x6961+192
 emu.write(x,255,emu.memType.snesWorkRam)
end
sample516("load");reads=0''')
    return replay(t,d,out,"fixed",cmds,911,{"instant":None,"stop":"held_stop","live":"stop_decode","damage":"damage"}[case],observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("case",choices=("instant","stop","damage","live"))
    a=p.parse_args();run(a.temp,a.phase,a.case)
