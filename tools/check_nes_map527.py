# SPDX-License-Identifier: MIT
"""Exercise map admission on the linked MCU, including wrapped credits and a ready bulk descriptor."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc,sha


class MapEndpoint(Endpoint):
    def exchange(self,tx,clock):
        if tx[0]==0xe1 and tx[1] in (2,4):
            self.calls.append(tx.hex())
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            return bytes(len(tx))
        return super().exchange(tx,clock)


def exercise(src,mode):
    m=ARM(src,mode)
    m.endpoint=MapEndpoint(mode);m.setup()
    m.endpoint.calls.clear()  # Exclude the initial E0 window handshake.
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    v=m.video+m.layout['nes_native_video165']['map']
    mask=m.resident+m.layout['nes_resident211']['map_stale']
    m.u.mem_write(mask+8,((1<<5)|(1<<7)|(1<<10)).to_bytes(8,'little'))
    m.put(m.resident,'nes_resident211','target',1,1)
    m.put(m.video,'nes_native_video165','map_dirty',1<<6,8)
    raw=(bytes(range(256))*16) if mode!='RLE' else b'\x51\xa6'*2048
    if mode=='empty':
        m.u.mem_write(mask+8,bytes(8))
        m.put(m.video,'nes_native_video165','map_dirty',0,8)
    elif mode=='last_row':
        m.u.mem_write(mask+8,(1<<63).to_bytes(8,'little'))
        m.put(m.video,'nes_native_video165','map_dirty',0,8)
    m.u.mem_write(v,raw)
    if mode=='three_credits':
        m.put(m.w,'nes_sink_window184','sent',1,2)
        m.put(m.w,'nes_sink_window184','retired',65534,2)
    if mode=='bulk':
        m.endpoint.jobs=[(0,0,16,1)]
    if mode=='STOP':
        m.endpoint.mode='STOP_after_E9';m.endpoint.accepted=1
    args=[m.s,m.video,m.resident]
    ok=m.call('nes_sink527_early',args)
    assert bool(ok)==(mode not in ('STOP','bad_E8_CRC','ambiguous_E1')),mode
    tx=[bytes.fromhex(v) for v in m.endpoint.calls]
    maps=[b[1:-2] for b in tx if b[0]==0xe1 and b[1] in (2,4)]
    if mode in ('DATA','RLE','ambiguous_E1'):
        b,=maps
        assert b[1]==2 and int.from_bytes(b[10:12],'little')==320
        assert (b[16:]==raw[320:512] and b[0]==2) or (b[0]==4 and int.from_bytes(b[14:16],'little')==192 and b[16:]==raw[:2])
    elif mode=='last_row':
        b,=maps
        assert b[0]==2 and int.from_bytes(b[10:12],'little')==4032 and b[16:]==raw[4032:]
    else:assert not maps
    if mode=='bulk':assert [b[1] for b in tx if b[0]==0xe1]==[7]
    if mode in ('three_credits','STOP'):assert not tx
    cursor=m.get(m.s,'nes_native_sink165','map_next',1)
    assert cursor==({'DATA':8,'RLE':8,'last_row':64}.get(mode,128))
    if ok:
        old=list(m.endpoint.calls);assert m.call('nes_sink527_early',args) and old==m.endpoint.calls
    return dict(case=mode,ok=ok,cursor=cursor,operations=[hex(b[0]) for b in tx])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows=[exercise(a.arm,n) for n in ('DATA','RLE','empty','last_row','three_credits','bulk','STOP','bad_E8_CRC','ambiguous_E1')]
    a.out.write_text(json.dumps(dict(sha256=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows),indent=2)+'\n',newline='\n')
