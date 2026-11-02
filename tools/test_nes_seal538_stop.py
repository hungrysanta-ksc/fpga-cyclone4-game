# SPDX-License-Identifier: MIT
"""Inject STOP during the actual sealed upload on both bank identities."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from nes_raw506 import once, sha
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE


def exercise(args, gen, label, *, edit_packet_case=None):
    out = args.out/f'{gen}-{label}'
    out.mkdir()
    frames = gen-904
    packets = []
    for line in (args.trace/'packets.jsonl').read_text().splitlines():
        _, _, body, payload = json.loads(line)
        record = bytes.fromhex(body)
        if int.from_bytes(record[8:10],'little') > gen:
            break
        packets.append(struct.pack('<H',len(record))+record)
        if payload:
            (out/f'tile-{len(packets):04d}.bin').write_bytes(bytes.fromhex(payload))
    (out/'requests.bin').write_bytes(b''.join(packets))
    for g in range(905,gen+1):
        for stem in ('expected','map'):
            shutil.copyfile(args.trace/f'{stem}-{g}.bin',out/f'{stem}-{g}.bin')
    shutil.copyfile(args.client/'sink165.sfc',out/'client.sfc')
    if edit_packet_case is not None:
        script = edit_packet_case(LUA)
    else:
        address = json.loads((args.client/'labels.json').read_text())[label]
        script = once(LUA,'local function loaded()',f"""local armed538,stopped538=false,false
    emu.addMemoryCallback(function()
     if packet and pb(0)==3 and pw(8)==FAULT then armed538=true end
    end,emu.callbackType.exec,{address})
    emu.addMemoryCallback(function()
     if packet and pb(0)==3 and pw(8)==FAULT then assert(not stopped538,'DMA after STOP') end
    end,emu.callbackType.write,0x420b)
    local function loaded()""")
        script = once(script,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",
                      "if armed538 then stopped538=true;return 128 end")
        script = once(script,"assert(lastStatus==0xe4,'STOP status')","assert(armed538 and stopped538 and lastStatus==0xe4,'STOP status')")
    script = once(script,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
    for key,value in dict(ROOT=json.dumps(out.as_posix()),MODE='"stop_final"',SCHEDULE='"continuous"',
                          START=3000000,FAULT=gen,COMPACT='true',POISON='false',TOTAL=len(packets),FRAMES=frames).items():
        script=script.replace('@'+key+'@',str(value))
    lua = out/'capture.lua'
    lua.write_text(script,newline='\n')
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(args.mesen),'--testRunner',str(lua),str(out/'client.sfc'),'--timeout=120','--doNotSaveSettings',
                        '--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true',
                        '--debug.scriptWindow.scriptTimeout=90'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=160,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    result=json.loads((out/'result.json').read_text())
    assert result['passed'] and result['last_status']==0xe4 and result['commits']==frames-1
    assert sha(out/'retained.rgb')==sha(args.trace/f'frame-{gen-1}.rgb')
    return dict(generation=gen,boundary=label,status=result['last_status'],commits=result['commits'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('client','trace','mesen','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--raw-rows',action='store_true')
    args=p.parse_args()
    args.out=args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    labels=['budget538','final212']
    if args.raw_rows:
        labels.append('raw_row489')
    results=[exercise(args,g,label) for g in (906,907) for label in labels]
    if args.raw_rows:
        results.append(exercise(args,906,'raw_high489'))
    (args.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
