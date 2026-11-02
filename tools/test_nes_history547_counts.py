# SPDX-License-Identifier: MIT
"""Directed count/format transitions, all rows equal, and the last byte different."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from nes_raw506 import once,sha
from replay_nes_history547 import history
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE

COUNTS=(2,2,1,3,2,2,2,2)


def payload(prefix,mask,count,gen):
    raw=bytearray(2048)
    for tile in range(32):
        for row in range(count):
            raw[tile*64+48+row*2]=255
            for plane in range(3):
                at=tile*64+plane*16+row*2
                raw[at:at+2]=bytes([(tile+plane)&255,251-row])
    if gen==912:raw[31*64+2+1]^=1
    tables=[]
    for section in range(3):
        data=bytearray()
        for n,active in ((count,True),(127,False),(97-count,False)):
            if section<2:data.extend([n,3 if active else 0,0,(0x38 if active else 0x31)+32*section,0])
            else:data.extend([n,1 if active else 17,0,0 if active or mask!=0x18 else 17,0])
        tables.append(bytes(data).ljust(81,b'\0'))
    tail=b''.join(tables)+struct.pack('<3H',16,16,16)
    packed=bytes(raw[t*64+p*16+r*2+k] for p in range(3) for r in range(count) for t in range(32) for k in range(2))
    return prefix+raw+tail,prefix+(packed if count<=2 else raw)+tail


def run(args,out,client,candidate):
    out.mkdir()
    requests=[]
    captured=[json.loads(s) for s in (args.trace/'packets.jsonl').read_text().splitlines()]
    for i,count in enumerate(COUNTS):
        g=905+i
        frame=[(bytearray.fromhex(b),tile) for _,_,b,tile in captured if int.from_bytes(bytes.fromhex(b)[8:10],'little')==g]
        seal,=[b for b,_ in frame if b[0]==3]
        image,wire=payload((args.trace/f'expected-{g}.bin').read_bytes()[:1121],int.from_bytes(seal[34:36],'little'),count,g)
        struct.pack_into('<H',seal,26,len(wire));struct.pack_into('<H',seal,38,count)
        frame=[(b,t) for b,t in frame if b[0]!=3 and b[1]!=5]
        for at in range(0,len(wire),240):
            data=wire[at:at+240]
            b=bytearray(seal[:16])+data;b[0:2]=bytes([2,5]);struct.pack_into('<3H',b,10,at,len(data),0)
            frame.append((b,None))
        frame.append((seal,None))
        for seq,(b,tile) in enumerate(frame):
            struct.pack_into('<H',b,2,seq);requests.append(struct.pack('<H',len(b))+b)
            if tile:(out/f'tile-{len(requests):04d}.bin').write_bytes(bytes.fromhex(tile))
        (out/f'expected-{g}.bin').write_bytes(image)
        shutil.copyfile(args.trace/f'map-{g}.bin',out/f'map-{g}.bin')
    (out/'requests.bin').write_bytes(b''.join(requests));shutil.copyfile(client/'sink165.sfc',out/'client.sfc')
    source=once(LUA,'   local hdma=file(',MAP_ORACLE+'   local hdma=file(')
    if candidate:
        source='local function verify526(f)return f end\n'+history(source,json.loads((client/'labels.json').read_text()))
    for key,val in dict(ROOT=json.dumps(out.as_posix()),MODE='"normal"',SCHEDULE='"continuous"',START=3000000,
                        POISON='true',FAULT=0,COMPACT='true',TOTAL=len(requests),FRAMES=len(COUNTS)).items():
        source=source.replace('@'+key+'@',str(val))
    lua=out/'capture.lua';lua.write_text(source,encoding='utf8',newline='\n')
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(args.mesen),'--testRunner',str(lua),str(out/'client.sfc'),'--timeout=120','--doNotSaveSettings',
                        '--snes.disableFrameSkipping=true','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       cwd=out,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=160)
    result=json.loads((out/'result.json').read_text());assert result['passed'] and result['commits']==len(COUNTS)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('client','base','trace','mesen','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    for name,client in [('base',args.base),('new',args.client)]:run(args,args.out/name,client,name=='new')
    for g in range(905,913):
        assert sha(args.out/'base'/f'frame-{g}.rgb')==sha(args.out/'new'/f'frame-{g}.rgb')
    with (args.out/'new/history547.csv').open() as f:masks={int(r['g']):int(r['mask']) for r in csv.DictReader(f)}
    assert masks=={905:0,906:0,909:0,910:0,911:63,912:61}
    (args.out/'result.json').write_text(json.dumps(dict(counts=COUNTS,masks=masks,RGB_frames=8))+'\n')
