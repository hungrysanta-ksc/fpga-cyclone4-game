# SPDX-License-Identifier: MIT
"""Run a second map offer after a successful prefix on the full linked ARM."""
import argparse
import json
from pathlib import Path
from check_nes_map527 import ARM, MapEndpoint, sha


def check(src, mode):
    m = ARM(src,'normal')
    m.endpoint = MapEndpoint()
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.resident,'nes_resident211','target',1,1)
    stale = m.resident+m.layout['nes_resident211']['map_stale']+8
    # Rows 5,6,7 finish first; the next three mix bank-stale and current dirty.
    m.u.mem_write(stale,((1<<5)|(1<<7)|(1<<12)|(1<<14)).to_bytes(8,'little'))
    m.put(m.video,'nes_native_video165','map_dirty',(1<<6)|(1<<13),8)
    raw = bytes(range(256))*16
    m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],raw)
    args = [m.s,m.video,m.resident]
    assert m.call('nes_sink527_early',args)
    assert m.get(m.s,'nes_native_sink165','map_next')==8
    m.endpoint.calls.clear()
    if mode=='three_credits':
        m.put(m.w,'nes_sink_window184','sent',1,2)
        m.put(m.w,'nes_sink_window184','retired',65534,2)
    elif mode=='old_bulk':
        m.put(m.p,'nes_plan200','bulk_pending',1,1)
        m.put(m.p,'nes_plan200','bulk_until',65534,2)
    elif mode=='tile_ready':
        m.endpoint.sent=1
        m.endpoint.jobs=[(0,0,16,1)]
    elif mode=='STOP':
        m.endpoint.mode='STOP_after_E9'
        m.endpoint.accepted=1
    else:
        m.endpoint.mode=mode
    ok=m.call('nes_sink527_early',args)
    calls=[bytes.fromhex(x) for x in m.endpoint.calls]
    maps=[b[1:-2] for b in calls if b[0]==0xe1 and b[2]==2]
    cursor=m.get(m.s,'nes_native_sink165','map_next')
    assert bool(ok)==(mode not in ('ambiguous_E1','STOP','bad_E8_CRC'))
    assert cursor==(15 if mode=='normal' else 8)
    assert len(maps)==int(mode in ('normal','ambiguous_E1'))
    if maps:
        b,=maps
        assert int.from_bytes(b[10:12],'little')==12*64 and b[16:]==raw[12*64:15*64]
    if mode in ('old_bulk','three_credits','STOP'):
        assert not calls
    if mode=='tile_ready':
        assert [b[1] for b in calls if b[0]==0xe1]==[7]
    assert not m.get(m.s,'nes_native_sink165','displayed') and not m.endpoint.rearmed
    return dict(mode=mode,ok=bool(ok),cursor=cursor,map_packets=len(maps))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src',type=Path)
    parser.add_argument('out',type=Path)
    a=parser.parse_args()
    cases=('normal','STOP','old_bulk','three_credits','tile_ready','bad_E8_CRC','ambiguous_E1')
    report=dict(firmware=sha(a.src/'obj-nes-100/firmware.stm'),cases=[check(a.src,k) for k in cases])
    a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
