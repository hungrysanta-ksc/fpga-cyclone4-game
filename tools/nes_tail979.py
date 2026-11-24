"""Separate the raw/table issue order from the idle DMA opportunity at SEAL."""
import argparse
import shutil
from pathlib import Path

from check_nes_plan975 import directory, packet_path, replay
from nes_capture978 import work as parent
from nes_cell977 import simulate
from nes_raw506 import once
from test_nes_banks557 import MASTER


def work(mode):
    return parent("returned").with_name("nes-tail979-"+mode)


def prepare(mode):
    dest=work(mode)/"link"
    shutil.copytree(parent("returned")/"link",dest)
    path=dest/"src/nes_native_sink165.c"
    src=path.read_text()
    if mode in ("clear","fitted","fitted96"):
        planner=dest/"src/nes_planner211.c"
        body=planner.read_text()
        assert body.index("offsetof(struct nes_native_video165,oam),0,sizeof")<body.index(" memset(p->oam,0,sizeof(p->oam));")
        planner.write_text(once(body," memset(p->oam,0,sizeof(p->oam));",""),newline="\n")
        if mode=="clear":return
    if mode in ("prefix","prefix96","fitted","fitted96"):
        # The planner has completed OBJ slots, all sprite attributes and
        # the first BG palettes before the prefix callback. prefix_sent972
        # already excludes the bank-history shortcut later at SEAL.
        old=" if(!packet(s,24,3,0,p->cgram,32))return false;"
        src=once(src,old," if(!packet(s,24,3,0,p->cgram,32) || !oam227(s,p->oam))return false;")
        src=once(src," if(!oam227(s,p->oam))return false;"," if(!p->prefix_sent972 && !oam227(s,p->oam))return false;")
        if mode in ("fitted","fitted96"):
            src=once(src," }else if(!span(s,3,0,p->cgram,512))return false;\n if(!p->prefix_sent972 && !oam227(s,p->oam))return false;",
                     " }else if(!span(s,3,0,p->cgram,512) || !oam227(s,p->oam))return false;")
        if mode in ("prefix96","fitted96"):
            src=once(src,"if(!packet(s,24,3,0,p->cgram,32) || !oam227",
                     "if(!packet(s,24,3,0,p->cgram,32) || !packet(s,2,3,32,p->cgram+32,96) || !oam227")
            src=once(src,"if(!packet(s,2,3,32,p->cgram+32,96) ||\n     (","if((")
        path.write_text(src,newline="\n")
        return
    if mode in ("tables","split","tables_oam"):
        # Section 5 has its own checked ranges. Scroll/padding always precede
        # the compact body, even when the early scroll path did not run.
        first=src.index(" if(!p->scroll_issued && !span(s,5,0")
        end=src.index(" /* Both immutable section-5 heads",first)
        chunk=src[first:end]
        src=src[:first]+src[end:]
        anchor=" bool same=same635(s,p);"
        if mode=="split":
            chunk=" const uint8_t *last_table=NULL;\n"+once(chunk,
                "  if(!packet(s,2,5,offset+201,joined+201,240))return false;",
                "  last_table=joined+201;")
            # descriptor[10] stores the exclusive end of the compact raw
            # image and its tables. Last packet covers the final 240 bytes.
            mark=" /* Both immutable section-5 heads"
            src=once(src,mark," if(last_table && !packet(s,2,5,(descriptor[10]|((unsigned)descriptor[11]<<8))-240,last_table,240))return false;\n"+mark)
        src=once(src,anchor,chunk+anchor)
    if mode in ("oam","tables_oam"):
        call=" if(!oam227(s,p->oam))return false;\n"
        src=once(src,call,"")
        src=once(src," if(p->prefix_sent972){",call+" if(p->prefix_sent972){")
    elif mode not in ("tables","split"):
        raise ValueError(mode)
    path.write_text(src,newline="\n")


def beam(temp,phase,mode):
    trace=directory(temp,phase,"978returned","cold")
    commands,ledger=packet_path(trace,911)
    if mode=="idle":
        # Leave the queue empty from the last real ACK up to the end of the
        # blank. This is a consumer opportunity test, not a faster ARM trace.
        g,op,arrival,*tail=commands[-1]
        assert (g,op)==(911,3)
        commands[-1]=(g,op,ledger[-2]["ack"]+38*1364,*tail)
    policy=mode
    if mode in ("last1","all1","all2","all3"):
        # Sensitivity only. Keep the byte stream, wire duration, four-credit
        # limit and order. Move recorded producer-ready bounds, not ARM code.
        policy="frame"
        advance=round(MASTER*int(mode[-1])/1000)
        last=max(i for i,c in enumerate(commands) if c[:2]==(911,7))
        for i,c in enumerate(commands):
            if c[:2]==(911,7) and (mode!="last1" or i==last):
                commands[i]=(*c[:5],max(0,c[5]-advance),c[6])
    replay(temp,trace,temp/f"nes-979-{mode}-p{phase}",policy,commands,911)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","beam","guard"))
    p.add_argument("mode")
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--fault",choices=("bad_seal","stop_decode"))
    a=p.parse_args()
    if a.action=="prepare":prepare(a.mode)
    elif a.action=="beam":beam(a.temp,a.phase,a.mode)
    elif a.action=="guard":
        trace=directory(a.temp,a.phase,"979"+a.mode,"cold")
        commands,_=packet_path(trace,911)
        replay(a.temp,trace,a.temp/f"nes-979-{a.mode}-{a.fault}","control",commands,911,a.fault)
    else:simulate(a.temp,a.phase,"cold",True,work(a.mode),True,tag="979"+a.mode,edition=966)
