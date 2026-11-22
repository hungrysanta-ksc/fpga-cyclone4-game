"""Compare an extended OAM wait and exact ARM packet-boundary searches."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch
from nes_chain935 import output, replay
from nes_raw506 import once, sha
from nes_wait936 import work as base


def work(mode):
    return base('batchfast').parent.parent/'nes-oam937'/mode


def prepare(mode):
    original=base('batchfast')/'link'
    assert sha(original/'src/obj-nes-100/firmware.stm')=='34d5e110c1801d131426132c850654dcbac97a380624bb18c48ceabccd454ee7'
    link=work(mode)/'link'
    shutil.copytree(original,link)
    src=link/'src/nes_native_sink165.c'
    code=src.read_text()
    anchor='!wait_map880(s->plan->window,12)'
    if mode=='double':
        code=once(code,anchor,'!wait_map880(s->plan->window,s->plan->sent>2 ? 24 : 12)')
    elif mode in ('linear','skip','runs'):
        start=code.index(' unsigned run=repeat_bytes(b,n);')
        end=code.index('\n}',start)
        linear=''' /* A 64-byte repeated word has 62 consecutive bytes equal to
  * the byte two places earlier. The last legal start in a packet is 239. */
 unsigned equal=0,stop=n<303?n:303;
 for(unsigned i=2;i<stop;i++){
  if(b[i]!=b[i-2])equal=0;
  else if(++equal==62)return i==63?repeat_bytes(b,n):i-63;
 }
 return n<240?n:240;'''
        skip=''' /* A mismatch at j rules out every 64-byte word run starting
  * at or before j-2 in this window. Start at the next possible byte. */
 for(unsigned at=0;at<240 && at+64<=n;){
  unsigned j=63;
  while(j>=2 && b[at+j]==b[at+j-2])--j;
  if(j<2)return at?at:repeat_bytes(b,n);
  at+=j-1;
 }
 return n<240?n:240;'''
        if mode=='runs':
            linear=' if(n<64)return n;\n'+linear
            linear=once(linear,' unsigned equal=0,stop=n<303?n:303;',
                        ''' unsigned run=repeat_bytes(b,n);
 if(run>=64)return run;
 unsigned equal=0,stop=n<303?n:303;''')
            # repeat_bytes may stop because the second byte of a pair differs;
            # restarting at index run+2 would skip an overlapping run.
            linear=once(linear,'return i==63?repeat_bytes(b,n):i-63;', 'return i-63;')
            linear=once(linear,'for(unsigned i=2;i<stop;i++)','for(unsigned i=run;i<stop;i++)')
        code=code[:start]+(skip if mode=='skip' else linear)+code[end:]
    else:
        raise ValueError(mode)
    src.write_text(code,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards'))
    p.add_argument('mode');p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    tag='937'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        if a.phase is None or a.cache is None:
            p.error('replay requires PHASE and CACHE')
        replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=work(a.mode),tag=tag)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),925,short_header=True)
    else:
        import nes_return920, nes_obj923
        from check_nes_chain935 import run
        from analyze_nes_palette921 import directory
        from analyze_nes_chain935 import measure
        for phase,cache in ((1,'warm'),(1,'cold'),(2,'cold')):
            folder=directory(a.temp,phase,tag,cache)
            if not (folder/'joint.json').exists():
                p.error(f'finish replay {a.mode} {phase} {cache} before running guards')
        with patch.object(nes_return920,'client',lambda _:output('bounded')),patch.object(nes_obj923,'client',lambda _:output('bounded')):
            nes_return920.guards(a.temp,'first',tag=tag,destination=work(a.mode)/'final-guards.json')
            nes_obj923.obj_stops(a.temp,'first',tag=tag,destination=work(a.mode)/'final-stops.json')
        for phase in (1,2):
            trial=measure(a.temp,'bounded',phase,'cold',tag=tag,trial=work(a.mode))
            if not trial['tail_grant']:
                continue
            for case in ('stop','head'):
                run(a.temp,'bounded',phase,case,tag=tag)
