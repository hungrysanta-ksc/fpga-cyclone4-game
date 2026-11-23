"""Compare a bounded next-pair prefetch with the 960 timing of the last 908 OBJ."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_chr951
import nes_ready958
from fixture_nes_port914 import fixture
from guard_nes_output852 import run as fault_run
from nes_blank960 import PACKED, WORK
from nes_companion952 import complete_row_set, project, replay, supply
from nes_raw506 import once
from nes_feedback953 import evidence
from prepare_nes_frame900 import QUARTUS, fit
from test_nes_banks557 import MASTER, crc, host_after


def next_pair(tag,mask):
    # Last even tile in a page, with seven low rows requested. Source is ROM.
    if (tag&15)==14 and tag<0x1ff0 and mask==0x7f:
        return (tag+2,16)
    return None


def run(temp,phase,cache, *, correction=None, recheck=False):
    redirected=correction!='960closed'
    folder=nes_ready958.directory(temp,phase,correction,'cold') if correction else None
    samples={}
    used=[]
    if correction:
        assert cache=='cold'
        for gen in (908,909):
            samples.update(evidence(folder,gen,log_name='tail961.log'))
    tag='961pair' if not correction else ('961wirepair' if redirected else '961wirebase')
    if recheck:
        previous=nes_ready958.directory(temp,phase,tag,'cold')
        for gen in (908,909):
            samples.update(evidence(previous,gen,log_name='tail961.log'))
        tag+='2'
    def wrapped(base,variant):
        parent=supply(base,variant,redirect=next_pair if redirected else None)
        if not samples:
            return parent
        class Measured(parent):
            def snapshot557(self,tx,start):
                reply=super().snapshot557(tx,start)
                at=round(host_after(start+7.5*MASTER/2625000,3))
                key=self.generation,at
                if tx[0]!=0xe8 or key not in samples:
                    return reply
                flags,count,desc=samples[key]
                assert count==int.from_bytes(reply[4:6],'big') and not any(reply[6:18])
                out=bytearray(reply)
                out[3]=flags
                out[6:18]=desc
                out[19]=crc(out[1:19],8,7,0)
                used.append(key)
                return bytes(out)
        return Measured
    with patch.object(nes_chr951,'ROM',PACKED):
        if cache=='cold':
            with patch.object(nes_ready958,'supply',wrapped):
                nes_ready958.feedback(temp,phase,close=True,trial_tag=tag,
                                      baseline_tag='960static',credit_tag='960credit')
        else:
            with complete_row_set():
                replay(temp,phase,'warm','banked',wrap=lambda b:wrapped(b,'checked'),
                       tag='961pair',work_arm=WORK,edition=955)
    if correction:
        out=nes_ready958.directory(temp,phase,tag,'cold')
        (out/'matched961.json').write_text(json.dumps(dict(measured=list(samples),used=used)))


def fixtures(temp,phase,tag):
    for g in (907,908,909):
        fixture(temp,phase,True,g,tag,include_bg=True)


def guards(temp,phase):
    folder=nes_ready958.directory(temp,phase,'961pair','cold')
    def damage(b,g,case):
        if g!=908:
            return b,False
        b[8]^=1
        return b,True
    fault_run(temp,folder,'bad-seal',column_client=PACKED,edit_seal=damage)
    def stop_at_seal(lua,labels):
        lua=once(lua,'if not injected852 then','if not injected852 and packet and pw(8)==908 and pb(0)==3 then')
        lua=once(lua,f"end,emu.callbackType.exec,{labels['column_service']})",
                 f"end,emu.callbackType.exec,{labels['service']})")
        return once(lua,'  assert(captured==commits)','  assert(injected852);assert(captured==commits)')
    fault_run(temp,folder,'stop',column_client=PACKED,select_packet=lambda b,g:g==908 and b[0]==3,
              adapt_lua=stop_at_seal,output_name='stop908')


def make_board(temp):
    old=project(temp,'checked')
    new=temp/'nes-trial816-board961'
    new.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(old/sub,new/sub)
    for f in old.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(PACKED/f.name if f.name=='sink-program.hex' else f,new/f.name)
    path=new/'nes_e9_rows914.sv'
    s=path.read_text()
    s=once(s,' wire take_hint952=',""" // Redirect an empty capture's idle cursor only on an accepted hint.
 wire cross961=hint && hint_ready && empty_capture && tag[3:0]==14 &&
               tag[12:4]!=9'h1ff && mask==8'h7f;
 wire take_hint952=""")
    s=once(s,'else if(take_hint952)begin',"""else if(cross961 && (!selected952 || page952!=tag[12:4]+1'b1 || cursor952>=32))begin
   selected952<=1;pending952<=1;page952<=tag[12:4]+1'b1;cursor952<=0;
  end else if(take_hint952)begin""")
    s=once(s,'if(cursor952==47 ||','if(cursor952==15 || cursor952==47 ||')
    path.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('run','wire','fixtures','board','fit','guards'))
    p.add_argument('temp',type=Path)
    p.add_argument('--phase',type=int,choices=(1,2))
    p.add_argument('--cache',choices=('warm','cold'),default='cold')
    p.add_argument('--tag',choices=('960closed','961pair','961wirebase','961wirepair','961wirebase2','961wirepair2'),default='961pair')
    p.add_argument('--recheck',action='store_true')
    a=p.parse_args()
    if a.mode=='board':
        make_board(a.temp)
    elif a.mode=='fit':
        fit(a.temp,961,QUARTUS)
    elif a.mode=='guards':
        guards(a.temp,a.phase)
    elif a.mode=='fixtures':
        fixtures(a.temp,a.phase,a.tag)
    elif a.mode=='wire':
        assert a.tag in ('960closed','961pair')
        run(a.temp,a.phase,a.cache,correction=a.tag,recheck=a.recheck)
    else:
        run(a.temp,a.phase,a.cache)
