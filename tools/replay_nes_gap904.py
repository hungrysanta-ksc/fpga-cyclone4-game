"""Replay the original game's rendering gap and a separate later tile workload."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from corpus_nes_848 import index
from capture_nes_mask820 import capture
from prepare_nes_geometry230 import main as translate
from prepare_nes_trial802 import PROBES
from prepare_nes_tile821 import prepare
from check_nes_input848 import run as sender
from test_nes_mirror822 import test as cache
from replay_nes_mask820 import simulate
from replay_nes_output852 import joint, monitor, main, MirrorLink, gates
from replay_nes_strip869 import map_samples
from nes_raw506 import once, sha

OBJ=list(range(3408,3437,4))
SAMPLE=[3346,3347,3350,3360,3368,3369]
EDGE=[3344,3348,3362,3363,3366]
BLANK=3350
TEST=sorted(set(SAMPLE+EDGE+OBJ)-{3360})
ARM=PROBES/'nes-sram897/link/src'
CLIENT=PROBES/'nes-trial890/client02'


def geometry(work):
    rtl=work/'rtl'
    rtl.mkdir(exist_ok=True)
    for f in TEST:
        d=work/('edge-split' if f in EDGE else 'split')/str(f)
        if f==BLANK:
            assert all((d/s).stat().st_size==0 for s in ('rows.bin','ppu-fetch.bin','nametable.bin'))
            assert len(set((d/f'frame-{f:04d}.rgb').read_bytes()[::3]))==1
            # No CHR or NT input. The disabled-mask test checks rejection and
            # recovery; palette, fine scroll and raw colour are not compared.
            (rtl/f'frame{f}.hex').write_text(('0'*27+'\n')*(233*341))
            (rtl/f'frame{f}.palette').write_text('0'*48+'\n')
        else:
            dest=rtl/str(f)
            args=['geometry','--capture',str(d),'--prior',str(d),'--out',str(dest),
                  '--first',str(f),'--last',str(f)]
            if f==3348:args+=['--allow-disabled-tail']
            with patch.object(sys,'argv',args):translate()
            for suffix in ('hex','palette'):
                shutil.copyfile(dest/f'frame{f}.{suffix}',rtl/f'frame{f}.{suffix}')


def board(temp,work,rom):
    rtl=work/'rtl'
    project=temp/'nes-trial816-board903'
    def adapt(s):
        s=once(s,'integer first,last,f,t,','integer sample_id,first,last,f,t,')
        cases=' '.join(f'{i}:f={f};' for i,f in enumerate(TEST))
        s=once(s,'for(f=first;f<=last;f++)begin',
               'for(sample_id=first;sample_id<=last;sample_id++)begin case(sample_id) '+cases+' endcase')
        s=once(s,'for(t=7*341+257;','for(t=0;')
        start=s.index('   if(!owned||!geometry_valid)')
        s=s[:start]+'''   if (!owned) $fatal(1,"collector did not complete %d",f);
   if (!geometry_valid || group_count==0) begin
    if(f!=3350 && f!=3348) $fatal(1,"unexpected rejected capture %d",f);
    enable=1; repeat(12) begin @(negedge clk); if(tx_valid)$fatal(1,"rejected capture exported"); end
    if(owned || export_error!=2)$fatal(1,"missing release");
    enable=0;frames++;$display("REJECT904 %0d %0d",f,generation);continue;
   end
   if(f==3350)$fatal(1,"no-fetch capture accepted");
'''+s[start:]
        return s
    simulate(project,rtl,[(0,len(TEST)-1)],adapt=adapt)
    groups={'gap':[f for f in [3344,3346,3347,3348,3362,3363,3366,3368,3369]
                   if (rtl/f'frame{f}.wire').exists()], 'obj':OBJ}
    # Preserve source fetches per frame even when captured in separate runs.
    merged=work/'fetch'
    for f in sum(groups.values(),[]):
        d=merged/str(f);d.mkdir(parents=True)
        shutil.copyfile(work/('edge-split' if f in EDGE else 'split')/str(f)/'ppu-fetch.bin',d/'ppu-fetch.bin')
    for group,frames in groups.items():
        gen={f:905+i for i,f in enumerate(frames)}
        if group=='gap':
            before=max(f for f in frames if f<3362)
            for f in frames:
                if f>=3362:gen[f]+=3362-before-1
        data=work/f'data-{group}'
        prepare(rtl,merged,rom,PROBES/'nes-output823/link-826/src',data,[(group,frames)],capture_generations=gen)
        cache(temp,data,data,rom,held=True,inputs=[(data,merged,rtl)],out=work/f'hits-{group}')
        sender(project,data/group,PROBES/'nes-output823/link-826/src',work/f'sender-{group}')
    (work/'groups.json').write_text(json.dumps(groups))


class TimedLink(MirrorLink):
    ideal=False
    cold_obj=False
    def __init__(self,a):
        self.returns=[]
        super().__init__(a)
        if self.cold_obj:
            # Withdraw capture hits only on scored frames. Keep both the
            # backing CHR bytes and its ordinary two-lookup miss cost.
            for gen in self.lookups:
                if int(gen)>=907:
                    self.lookups[gen]=dict.fromkeys(self.lookups[gen],2)
                    self.cache[gen]={}
        self.grants=[]
        self.original_select=self.calendar.select
        self.calendar.select=self.select

    def select(self,request):
        grant,reply=self.original_select(request)
        if self.ideal:
            # Sensitivity only: identical misses, hit costs and PSRAM latency.
            reply=request+(reply-grant)
            grant=request
        self.grants.append((self.generation,self.read_kind,request,grant,reply))
        return grant,reply

    def next_rom(self,t):
        self.read_kind=self.pending[0][0]
        return super().next_rom(t)

    def exchange(self,seq,t,op,args):
        lines=super().exchange(seq,t,op,args)
        for item in (lines[3] if len(lines)>3 else '').split(';'):
            if item:
                self.returns.append(list(map(int,item.split(':'))))
        if op=='FINISH':
            (self.a.out/'grants904.json').write_text(json.dumps(self.grants))
            (self.a.out/'banks904.json').write_text(json.dumps(self.phases))
            (self.a.out/'returns904.json').write_text(json.dumps(self.returns))
        return lines


def replay(temp,work,group,phase,ideal=False,cold_obj=False):
    source=json.loads((work/f'sender-{group}/sender.json').read_bytes())
    def adapt(s):
        return map_samples(once(monitor(s,'demo'),'local n=pb(0)==2 and pw(12) or pw(14)',
                                'local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)'))
    tag='904-cold' if cold_obj else ('904-ideal2' if ideal else ('904-retire' if group=='obj' else '904-trace2'))
    args=['replay','','','','','',tag,str(Path.home()/'Downloads/nes-budget-mmc872.txt')]
    with patch.object(sys,'argv',args),patch.object(TimedLink,'ideal',ideal),patch.object(TimedLink,'cold_obj',cold_obj),patch.object(TimedLink,'lookup_file',work/f'hits-{group}/hits.json'),gates(source,True):
        status=joint.Runtime.status
        def observed(cpu):
            reply=status(cpu)
            cpu.events.append(dict(event='input_status904',generation=cpu.generation,input_generation=cpu.input_generation,
                                   clock=cpu.clock,reply=reply.hex()))
            return reply
        with patch.object(joint.Runtime,'status',observed):
            main(work/f'data-{group}',group,'jointmirror',phase,temp,arm=ARM,client=CLIENT,
                 client_hash=sha(CLIENT/'sink165.sfc'),link_class=TimedLink,packet_source=source,adapt_template=adapt)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['capture','count','index','geometry','board','replay'])
    parser.add_argument('temp',type=Path)
    parser.add_argument('rom',type=Path)
    parser.add_argument('--group',choices=['gap','obj'])
    parser.add_argument('--phase',type=int,choices=[1,2])
    controls=parser.add_mutually_exclusive_group()
    controls.add_argument('--ideal-grant',action='store_true')
    controls.add_argument('--cold-obj',action='store_true')
    a=parser.parse_args();w=a.temp/'nes-gap904'
    if a.action=='capture':
        for name,ids in [('capture',SAMPLE+OBJ),('edges',EDGE)]:
            capture(a.rom,a.temp/'nes-bonus698-mesen/Mesen.exe',w/name,ids)
    elif a.action=='count':
        w.mkdir(parents=True,exist_ok=True)
        lua=w/'count.lua'
        template=Path(__file__).resolve().parents[1]/'tests/nes-functional/ppu_gap904.lua'
        lua.write_text('local OUT='+json.dumps((w/'count.csv').as_posix())+'\n'+template.read_text())
        with (w/'count.log').open('wb') as log:
            subprocess.run([a.temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',lua,a.rom,'--timeout=120',
                            '--enableStdout','--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true'],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW,
                           env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    elif a.action=='index':
        index(w/'capture',w/'split',w/'index.json',{'transition':SAMPLE,'obj':OBJ})
        index(w/'edges',w/'edge-split',w/'edge-index.json',{'edges':EDGE})
    elif a.action=='geometry':geometry(w)
    elif a.action=='board':board(a.temp,w,a.rom)
    else:replay(a.temp,w,a.group,a.phase,a.ideal_grant,a.cold_obj)
