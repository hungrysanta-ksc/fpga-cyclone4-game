"""Replay MMC925's recorded queue with only the last SEAL offer shifted in beam time."""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(folder, name):
    with (folder/name).open() as stream:
        return list(csv.DictReader(stream))


def candidate_client(dest, parent, policy):
    """Change only the selected admission or wait branch of the verified WRAM image."""
    from boot_nes_column854 import build
    source=ROOT.parent/'probes/nes-return920/mask'
    assert (source/'sink165.sfc').read_bytes()==parent.read_bytes()
    labels=json.loads((source/'labels.json').read_bytes())
    body=bytearray((source/'body.bin').read_bytes())
    if policy=='group':
        sample=labels['sample618']-0x7e2000
        offset=body.index(bytes.fromhex('eb c9 e1 90 1f c9 fd'),sample,sample+50)+2
        body[offset]=228
    else:
        # $4212 already sampled active display. Initialize the original blank
        # timeout and check STOP, without first waiting for active display again.
        sample=labels['group_wait912']-0x7e2000
        hook=body.index(bytes.fromhex('ad 12 42 10 38'),sample,sample+32)
        dest_blank=labels['blank169']-6
        assert body[dest_blank-0x7e2000:dest_blank-0x7e2000+9]==bytes.fromhex('a9 ff ff 8d 3e 10 20 19 36')
        def jump(pc):
            return b'\x4c'+(pc&65535).to_bytes(2,'little')
        labels['edge_wait928']=0x7e2000+len(body)
        body.extend(bytes.fromhex('ad 12 42 30 05 c2 20')+jump(dest_blank)+jump(0x7e2000+hook+5))
        body[hook:hook+5]=jump(labels['edge_wait928'])+bytes.fromhex('ea ea')
    if not dest.exists():
        build(source,dest,bytes(body),labels)
    assert (dest/'body.bin').read_bytes()==body
    return dest/'sink165.sfc'


def run(temp, output, phase, target, policy='baseline', stop=False):
    ref = temp/f'nes-tile821-obj-jointmirror-p{phase}-925final-warm-pair'
    out = output.resolve()/f'p{phase}-{target}{"" if policy=="baseline" else "-"+policy}{"-stop" if stop else ""}'
    if not str(out).isascii():
        raise ValueError('Mesen Lua file I/O requires an ASCII capture directory on this host')
    out.mkdir(parents=True, exist_ok=False)
    joint = json.loads((ref/'joint.json').read_bytes())
    package = json.loads((ROOT/'analysis/trial925-package.json').read_bytes())
    assert joint['passed'] and joint['firmware_SHA256']==package['firmware']
    rom = ref/'client.sfc'
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==package['client']==joint['client_SHA256']
    if policy!='baseline':
        rom=candidate_client(output.resolve()/('client928' if policy=='group' else 'edge928'),rom,policy)
    window = read_csv(ref,'window.csv')
    seal, = [r for r in window if (r['g'],r['op'],r['event'])==('912','3','load')]
    offers = [json.loads(l) for l in (ref/'packets.jsonl').read_text().splitlines()]
    assert int.from_bytes(bytes.fromhex(offers[-1][2])[8:10],'little')==912 and offers[-1][2].startswith('03')
    if target:
        # Within the same frame as the control SEAL. Actual acceptance is logged below.
        shift=(target-int(seal['line']))*1364
        assert shift>=0
        offers[-1][1]+=shift
    chunks = []
    for _,clock,packet,tile in offers:
        chunks.append(f'{{{clock},"{packet}","{tile}"}}')
    script=(ref/'capture.lua').read_text()
    script=re.sub(r'local ROOT="[^"]+"',lambda _: f'local ROOT="{out.resolve().as_posix()}"',script,count=1)
    begin=script.index('local cmds=assert(io.open')
    end=script.index('local progressLog=',begin)
    script=script[:begin]+'local offers={'+',\n'.join(chunks)+'}\n'+'''
TOTAL=#offers
rpc=function()
 local now=emu.getState().masterClock
 while sent<TOTAL and offers[sent+1][1]<=now do
  assert(sent-retired<4,'recorded offer exhausted the available credit')
  sent=sent+1
  local p=offers[sent]
  requests[sent]=unhex(p[2]);tilePayload[sent]=unhex(p[3])
  local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)
  frames[sent]=g-905;frameRelease[g-905]=frameRelease[g-905] or p[1]
  if requests[sent]:byte(1)==3 then sealIndex[g-905]=sent end
 end
end
'''+script[end:]
    # Only the queue peer is substituted. Original STOP service, PPU endpoint,
    # expected content/ownership, reveal and receipt checks all remain enabled.
    script=script.replace("checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)",
                          "-- Frozen offers only need to become visible on the next device access.")
    if stop:
        assert policy=='edge'
        labels=json.loads((rom.parent/'labels.json').read_bytes())
        site=labels['edge_wait928']+7  # Active display branch, just before original blank counter init.
        marker="local function loaded()"
        assert script.count(marker)==1
        script=script.replace("local MODE='normal'","local MODE='stop_final'").replace("local FAULT=905","local FAULT=912")
        script=script.replace(marker,f"""local stop928=false
checkedMem527(function() if packet and pw(8)==912 and pb(0)==3 then stop928=true end end,
 emu.callbackType.exec,{site})
"""+marker)
        script=script.replace("MODE=='stop_final'and rd(0x1025)==2","MODE=='stop_final'and stop928")
    for g in range(905,913):
        for prefix in ('colors636','expected','map'):
            name=f'{prefix}-{g}.bin'
            shutil.copyfile(ref/name,out/name)
    lua=out/'capture.lua'
    lua.write_text(script,encoding='utf-8')
    mesen=temp/'nes-bonus698-mesen/Mesen.exe'
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(mesen),'--testRunner',str(lua),str(rom),'--timeout=150','--doNotSaveSettings',
                        '--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true',
                        '--debug.scriptWindow.scriptTimeout=90'],stdout=log,stderr=subprocess.STDOUT,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       creationflags=subprocess.CREATE_NO_WINDOW,timeout=165,check=True)
    result=json.loads((out/'result.json').read_bytes())
    assert result['passed'] and result['commits']==(7 if stop else 8) and result['last_status']==(0xe4 if stop else 1)
    for g in range(905,912 if stop else 913):
        name=f'frame-{g}.rgb'
        assert (out/name).read_bytes()==(ref/name).read_bytes()
    if stop:
        assert (out/'retained.rgb').read_bytes()==(ref/'frame-911.rgb').read_bytes()
        assert not (out/'frame-912.rgb').exists()
        return dict(phase=phase,stop=result['last_status'],retained=911)
    observed=read_csv(out,'window.csv')
    before=lambda data:[r for r in data if int(r['clock'])<int(seal['clock'])]
    prefix_equal=before(window)==before(observed)
    if policy=='baseline':
        assert prefix_equal
    if not target and policy=='baseline':
        assert observed==window and read_csv(out,'seal528.csv')==read_csv(ref,'seal528.csv')
    rows=[r for r in observed if (r['g'],r['op'])==('912','3')]
    starts=[r for r in rows if r['event']=='ppu_dma']
    ends=[r for r in rows if r['event']=='ppu_last']
    commands=[r for r in read_csv(out,'seal528.csv') if r['g']=='912' and r['event']=='dma' and
              int(r['clock'])>=int(rows[0]['clock'])]
    jobs=[]
    for start,last,cmd in zip(starts,ends,commands,strict=True):
        assert start['clock']==cmd['clock'] and start['value']==cmd['bytes']
        assert start['frame']==last['frame'] and 225<=int(start['line'])<=int(last['line'])<=261
        port=int(cmd['port'])
        kind={4:'OAM',34:'CGRAM'}.get(port)
        if kind is None:
            assert port==24
            kind='raw' if int(cmd['dst']) in (0x5000,0x5010,0x5020,0x9000,0x9010,0x9020) else 'VRAM'
        jobs.append([kind,int(cmd['bytes']),int(start['frame']),int(start['line']),int(last['line'])])
    def mark(event):
        r,=[r for r in rows if r['event']==event]
        return [int(r['frame']),int(r['line']),int(r['clock'])]
    summary=dict(phase=phase,target=target,policy=policy,prefix_equal=prefix_equal,seal=mark('load'),
                 jobs=jobs,show=mark('reveal'),ack=mark('ack'),ROM=hashlib.sha256(rom.read_bytes()).hexdigest())
    (out/'summary.json').write_text(json.dumps(summary)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('phase',type=int,choices=(1,2))
    parser.add_argument('lines',nargs='*',type=int)
    parser.add_argument('--policy',choices=('baseline','group','edge'),default='baseline')
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--joint',choices=('warm','cold'),help='run the ARM with live credit and ROM contention')
    args=parser.parse_args()
    if args.joint:
        from unittest.mock import patch
        import nes_window924
        from prepare_nes_trial925 import WORK
        if args.lines or args.stop or args.policy!='edge':
            parser.error('the closed-loop comparison uses --policy edge and the original offer schedule')
        parent=args.temp/f'nes-tile821-obj-jointmirror-p{args.phase}-925final-warm-pair/client.sfc'
        rom=candidate_client(args.out.resolve()/'edge928',parent,'edge')
        with patch.object(nes_window924,'client',return_value=rom.parent):
            nes_window924.replay(args.temp,'objheader',args.phase,args.joint=='cold',arm=WORK,
                                 edition=925,tag='928edge')
    elif args.lines:
        for target in args.lines:
            print(json.dumps(run(args.temp,args.out,args.phase,target,args.policy,args.stop)),flush=True)
    else:
        parser.error('specify a target line or --joint')
