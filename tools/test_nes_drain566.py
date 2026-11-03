# SPDX-License-Identifier: MIT
"""Run the real MMC558 65816 around cancellation, using STOP/START frames from linked ARM."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for key in ('replay','arm_trace','mesen','out'):
        p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    replay=a.replay.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    rom=replay/'client.sfc';arrivals=replay/'arrivals.tsv'
    assert sha(rom)=='179fb2cfd3ba2bcdcd672f1a377d24225c41ef8e7903938163fa98ab82138539'
    arm=json.loads(a.arm_trace.read_text());events=arm['normal']
    stop=next(i for i,e in enumerate(events) if e['event']=='spi' and e['tx'].startswith('64'))
    start=next(i for i in range(stop+1,len(events)) if events[i]['event']=='spi' and events[i]['tx'].startswith('63'))
    transfers=[bytes.fromhex(e['tx']) for e in events[stop:start+1] if e['event']=='spi']
    assert [x[0] for x in transfers]==[0x64,0x65,0x65,0x63]
    clocks_per_byte=8*21477272/2625000
    stop_clock=math.ceil(len(transfers[0])*clocks_per_byte)
    start_clock=math.ceil(sum(map(len,transfers))*clocks_per_byte)
    image=rom.read_bytes()
    vec=int.from_bytes(image[0x7ffc:0x7ffe],'little')
    # Reset stub copies offset 0x60 to 7e:2000. Identify the first token STA.
    assert bytes.fromhex('a26080a00020547e00') in image[:96]
    signature=bytes.fromhex('af1000408d4c60af1200408d4e60')
    assert image.count(signature)==1
    store_pc=0x7e2000+image.index(signature)+4-0x60
    source=Path(__file__).with_suffix('.lua').read_text(encoding='utf-8')
    result=dict(arm=arm,rom=sha(rom),arrivals=sha(arrivals),mesen=sha(a.mesen),
                clock_hz=21477272,spi_hz=2625000,stop_clock=stop_clock,start_clock=start_clock,cases={})
    for cut,bypass in [('one_byte_left',False),('last_read',False),('before_first_store',False),('two_token_bytes',False),('last_read',True)]:
        name=cut+('_bypass' if bypass else '_reset')
        d=out/name;d.mkdir(exist_ok=False)
        trace=d/'bus.csv';lua=d/'test.lua';script=source
        for k,v in dict(TRACE=json.dumps(trace.as_posix(),ensure_ascii=False),ARRIVALS=json.dumps(arrivals.as_posix(),ensure_ascii=False),
                        CUT=json.dumps(cut),BYPASS=str(bypass).lower(),STORE=store_pc,VECTOR=vec,STOP=stop_clock,START=start_clock).items():
            script=script.replace('@'+k+'@',str(v))
        lua.write_text(script,encoding='utf-8')
        with (d/'mesen.log').open('wb') as log:
            subprocess.run([str(a.mesen.resolve()),'--testRunner',str(lua),str(rom),'--timeout=50','--doNotSaveSettings',
                '--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],
                cwd=d,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                stdout=log,stderr=subprocess.STDOUT,timeout=80,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        with trace.open() as f:
            rows=[dict(event=r[0],clock=int(r[1]),packet=int(r[2]),reads=int(r[3]),value=int(r[4])) for r in csv.reader(f)]
        labels=[r['event'] for r in rows]
        if bypass:assert labels[-1]=='unread_retired' and 'reset_applied' not in labels
        else:
            assert labels[-2:]==['fresh_commit','fresh_packet_ack'] and 'unread_write' not in labels
            assert labels.index('cancel')<labels.index('reset_applied')<labels.index('reset_vector')<labels.index('fresh_last_read')
        result['cases'][name]=rows
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
