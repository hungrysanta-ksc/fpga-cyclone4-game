"""Observe group admission in the linked 65816 with the original ARM arrivals."""
import argparse
import json
from math import ceil
from pathlib import Path
from subprocess import CalledProcessError

from analyze_nes_map830 import load,window
from check_nes_wram859 import replay_arrivals
from prepare_nes_trial802 import PROBES


def guards(temp):
    from check_nes_seal858 import coverage
    from guard_nes_output852 import run as run_guard
    from nes_raw506 import once
    folder=temp/'nes-tile821-demo-jointmirror-p1-861-855-128-high-tail864'
    client=PROBES/'nes-column854/client-e'
    results={}
    for name in ('full-middle','table-entry','bad-width'):
        path=folder/('guard-'+name)/'result.json'
        # Existing fixture runners require a fresh output directory.
        if not path.exists():coverage(temp,folder,client,name)
        proof=load(path)
        assert proof['passed'] and proof['commits']==1 and proof['last_status']==224
        results[name]=proof['last_status']
    def inject(lua,labels):
        lua=once(lua,'if not injected852 then','if not injected852 and packet and pw(8)==906 and pb(0)==3 then')
        return once(lua,'end,emu.callbackType.exec,'+str(labels['column_service'])+')',
                    'end,emu.callbackType.exec,'+str(labels['coverage212'])+')')
    stop=run_guard(temp,folder,'stop',column_client=client,edit_seal=lambda b,g,k:(b,g==906),
                   adapt_lua=inject)
    restart=run_guard(temp,folder,'restart',folder/'guard-stop/canceled.bin',client)
    (PROBES/'nes-tail864/guards.json').write_text(json.dumps(dict(rejected=results,stop=stop,restart=restart)))


def pack_tail(folder,mode):
    """Timing envelope. Preserve E1 service costs and the four-slot queue.

    This assumes immutable data is prepared and non-E1 work can be removed
    or overlapped. It is not an execution of a faster ARM implementation.
    """
    records=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    tx=[r for r in load(folder/'events.json') if r.get('opcode')=='0xe1']
    assert len(tx)==len(records)
    acks={r['index']:r['clock'] for r in window(folder) if r['event']=='ack'}
    payloads=[bytes.fromhex(row[2]) for row in records]
    target=[i for i,b in enumerate(payloads) if int.from_bytes(b[8:10],'little')==942]
    last=target[-1]
    assert payloads[last][0]==3
    first=last if mode=='seal' else next(i for i in target if payloads[i][:2]==bytes((4,5))
                                        and int.from_bytes(payloads[i][10:12],'little')==1121)
    starts={}
    for i in range(first,last+1):
        assert abs(records[i][1]-tx[i]['clock'])<1
        # i is zero based. To issue packet i+1 the receipt for i-3
        # must have returned. Check actual retire clocks again after replay.
        starts[i+1]=max(records[i-1][1],acks[i-3])
        records[i][1]=ceil(starts[i+1]+tx[i]['clock']-tx[i]['start'])
        assert records[i][1]<=ceil(tx[i]['clock'])+1
    return records,starts


def run(temp,arm,phase,consumer,mode):
    if mode=='guards':
        assert arm==consumer==855 and phase==1
        guards(temp)
        return
    client=PROBES/('nes-column854/client-e' if consumer==855 else 'nes-seal858/client-e')
    labels=load(client/'labels.json')
    body=(client/'body.bin').read_bytes()
    base=labels['group538']
    code=body[base-0x7e2000:base-0x7e2000+80]
    points={k:labels[k] for k in ('group538','one618','fresh618','budget538','group_ready538',
                                  'raw_dispatch489','wait169','final212','borrow516','fresh516')}
    # Observe only instructions present in the linked client. $7e4004,x is
    # the charged descriptor size, which can exceed the physical PPU bytes.
    for name,signature in [('test_size','c9 81 01 b0'),('test_raw_bank0','c9 00 50 f0'),
                           ('test_raw_bank1','c9 00 90 f0')]:
        points[name]=base+code.index(bytes.fromhex(signature))
    def hook(name,pc):
        return f"""checkedMem527(function()
 if packet and pb(0)==3 then
  local cur=word(0x1252)
  local st=emu.getState()
  branches:write(string.format('%d,%s,%d,%d,%d,%d,%d,%d,%d\\n',pw(8),'{name}',st.masterClock,
    st.frameCount,st['ppu.scanline'],cur,word(0x1250),word(0x4002+cur),word(0x4004+cur)))
 end
end,emu.callbackType.exec,{pc})
"""
    hooks="local branches=assert(io.open(ROOT..'/branches.csv','w'))\n"+''.join(hook(k,v) for k,v in points.items())
    folder=temp/f'nes-tile821-demo-jointmirror-p{phase}-861-{arm}-128-high'
    if arm!=consumer:folder=folder.with_name(folder.name+f'-cpu{consumer}-864')
    assert (folder/'client.sfc').read_bytes()==(client/'sink165.sfc').read_bytes()
    if mode=='failed-gate':
        assert 'assertion failed' in (folder/'map-error.txt').read_text()
        template=(folder/'capture.lua').read_text()
        gate='assert(beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount)'
        assert template.count(gate)==1
        template=template.replace(gate,gate[:-1]+""",string.format(
            'beam864 gen=%d actual=%d/%d latched=%d/%d h=%d software=%d bytes=%d',
            word(0x1226),st.frameCount,st['ppu.scanline'],beam685.frame,beam685.line,beam685.h,rd(0x103e),n))""")
        out=folder/'failed-beam864'
        records=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
        # frameRelease is used solely for the aborted run's reporting fields.
        try:
            replay_arrivals(temp,folder,out,hooks,records,dict.fromkeys(range(905,967),0),template)
        except CalledProcessError:
            error=(out/'map-error.txt').read_text()
            assert 'beam864 gen=' in error,error
        else:
            raise AssertionError('map guard did not reproduce')
        def prior(location):
            return [(r['index'],r['event'],r['clock']) for r in window(location)
                    if r['event'] in ('load','ack','reveal') and r['g']<963]
        assert prior(folder)==prior(out)
        return
    out=folder/('branches864' if mode=='observed' else 'budget864-'+mode)
    if mode=='observed':
        replay_arrivals(temp,folder,out,hooks)
        return
    assert arm==consumer==855
    records,starts=pack_tail(folder,mode)
    replay_arrivals(temp,folder,out,hooks,records)
    w=window(out)
    acks={r['index']:r['clock'] for r in w if r['event']=='ack'}
    assert all(acks[i-4]<=clock for i,clock in starts.items())
    ref=window(folder)
    def prefix(rows):
        return [(r['clock'],r['event']) for r in rows if 0<r['index']<min(starts)
                and r['event'] in ('load','reveal','ack')]
    assert prefix(w)==prefix(ref)
    assert all((out/f'frame-{g}.rgb').read_bytes()==(folder/f'frame-{g}.rgb').read_bytes() for g in range(905,967))
    (out/'timing.json').write_text(json.dumps(dict(starts=starts,first=min(starts),last=max(starts),
        seal_available=records[max(starts)-1][1],all_prior_credits_checked=True)))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('temp',type=Path)
    p.add_argument('arm',type=int,choices=(855,860))
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('consumer',type=int,choices=(855,860))
    p.add_argument('--mode',choices=('observed','seal','raw-tail','failed-gate','guards'),default='observed')
    run(**vars(p.parse_args()))
