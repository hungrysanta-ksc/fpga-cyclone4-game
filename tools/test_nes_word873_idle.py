"""Replay the actual consumer through g950 with a bounded delay before section 5.

The paired control uses the same offline feed. All packet bytes and all
subsequent inter-packet spacings are fixed. This is a consumer-only experiment.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from analyze_nes_map830 import load, window
from nes_raw506 import once


def run(temp, phase, delay, tag):
    trial=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'
    suffix = '-872-final' if tag=='872-final' else ''
    out=temp/f'nes-word873-idle-p{phase}-{delay}{suffix}'
    out.mkdir()
    trace=window(trial)
    last_map=max(e['index'] for e in trace if e['g']==950 and e['section']==2 and e['event']=='ack')
    map_ack=next(e['clock'] for e in trace if e['index']==last_map and e['event']=='ack')
    wire=[e for e in load(trial/'events.json') if e.get('opcode')=='0xe1']
    pushes=[]
    shift=0
    for i,line in enumerate((trial/'packets.jsonl').read_text().splitlines(),1):
        _,target,payload,bulk=json.loads(line)
        b=bytes.fromhex(payload)
        if i==last_map+1:
            assert b[:2]==bytes((2,5)) and int.from_bytes(b[12:14],'little')==21
            if delay:
                # Start the scroll transaction at the last map ACK. Charge
                # its original wire duration before the packet becomes visible.
                tx=wire[i-1]
                shift=max(0,map_ack+round(tx['clock']-tx['start'])-target)
        pushes.append((target+shift,'PUSH',payload,bulk))
        if b[0]==3 and int.from_bytes(b[8:10],'little')==950:
            break
    else:
        raise ValueError('missing SEAL')
    result=run_consumer(temp,trial,out,pushes,46)
    assert (out/'frame-950.rgb').read_bytes()==(trial/'frame-950.rgb').read_bytes()
    rows=window(out)
    def view(events,g):
        return next([r['frame'],r['line'],r['clock']] for r in events if r['g']==g and r['event']=='reveal')
    assert view(rows,949)==view(trace,949)
    result_ack=result['frames'][-1]['ACK_masterclock']
    if not delay:
        assert view(rows,950)==view(trace,950)
        assert result_ack==next(e['clock'] for e in trace if e['g']==950 and e['event']=='ack' and e['op']==3)
    result=dict(shift_clocks=shift,previous=view(rows,949),show=view(rows,950),ACK=result_ack,
                dma=[[r['frame'],r['line'],r['value']] for r in rows if r['g']==950 and r['event']=='ppu_dma'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')


def run_consumer(temp,trial,out,pushes,frame_count,trace_points=None):
    pushes.append((pushes[-1][0]+1,'FINISH','',''))
    with (out/'commands.txt').open('w',encoding='ascii',newline='\n') as f:
        for i,push in enumerate(pushes,1):
            f.write('\n'.join(map(str,(i,*push)))+'\n')
    lua=(trial/'capture.lua').read_text()
    for pattern,replacement in ((r'^local ROOT=.*$','local ROOT='+json.dumps(out.as_posix())),
            (r'^local cmds=.*$',"local cmds=assert(io.open(ROOT..'/commands.txt','rb'))"),
            (r'^local replies=.*$',"local replies={write=function()end,flush=function()end}")):
        lua,n=re.subn(pattern,lambda _:replacement,lua,flags=re.M)
        assert n==1
    lua=once(lua,"MODE=='normal'and 62",f"MODE=='normal'and {frame_count}")
    # As in the STOP runner, advance the offline queue at its MMIO reads.
    lua=once(lua,'checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    if trace_points:
        lua=trace_points(lua)
    (out/'capture.lua').write_text(lua)
    for pattern in ('expected-*.bin','colors636-*.bin','map-*.bin','client.sfc'):
        for src in trial.glob(pattern):
            shutil.copyfile(src,out/src.name)
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',out/'capture.lua',
                        out/'client.sfc','--timeout=240','--doNotSaveSettings','--enableStdout',
                        '--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true',
                        '--debug.scriptWindow.scriptTimeout=90'],stdout=log,stderr=subprocess.STDOUT,
                       timeout=255,check=True,creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    result=load(out/'result.json')
    assert result['passed'] and result['commits']==frame_count and result['last_status']==1
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('delay',type=int,choices=(0,1))
    p.add_argument('--tag',choices=('872-final','873-word'),default='873-word')
    run(**vars(p.parse_args()))
