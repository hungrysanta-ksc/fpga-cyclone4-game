# SPDX-License-Identifier: MIT
"""Execute warm row fallback, stale hints, independent identity and STOP."""
import argparse,json,struct,binascii
from pathlib import Path
from probe_nes_planner285 import Planner
from probe_nes_decode280 import records,chunks
from nes_delta231 import BASE,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);arm=Planner(a.arm/'planner.elf',None)
    arm.call('reset285',[]);arm.call('reset280',[]);arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    def begin(f):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(name,[]),name
    def finish(f):
        for _ in range(34):
            ok=arm.call('next_step286',[]);assert ok
            if ok==2:break
        else:raise AssertionError('step limit')
        out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')))
        assert out==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()
        v=arm.symbols['video285'];layout=[arm.call('layout285',[i]) for i in range(3)]
        meta=b''.join(bytes(arm.uc.mem_read(v+at,n)) for at,n in [(layout[0],4096),(layout[1],512),(layout[2],544),(layout[1]+512,1121),(0,2291),(2292,6)])
        assert meta==(BASE/f'probes/nes-wholepath247/jointdecode-test02/run/expected-{f-904}.bin').read_bytes()
    begin(905);finish(905);assert arm.call('commit285',[]);begin(906)
    memory=bytes(arm.uc.mem_read(0x20000000,0x40000));context=arm.uc.context_save();checks=[]
    def restore():arm.uc.mem_write(0x20000000,memory);arm.uc.context_restore(context)
    v=arm.symbols['video285'];r=arm.symbols['resident285'];map_at=v+arm.call('layout285',[0])
    assert arm.call('context_size286',[])==124
    ctx=arm.symbols['ctx286'];groups=arm.uc.mem_read(ctx+116,1)[0];first=arm.uc.mem_read(ctx+20,32)
    # Compact raster low6 bits are exactly column225 after canonical expansion.
    history=arm.symbols['history286'];positions=[]
    for g in range(groups):
        start=int.from_bytes(arm.uc.mem_read(history+3872+first[g]*2,2),'little')&63
        for x in range(33):
            col=(start+x)&63;positions.append(((col//32)*1024+g*32+col%32)*2)
    assert len(set(positions))==groups*33
    for label,mask in [('invalid slot hint',0x3ff),('stale attribute hint',0x400)]:
        restore();data=bytearray(arm.uc.mem_read(map_at,4096))
        for i in positions:data[i:i+2]=(int.from_bytes(data[i:i+2],'little')^mask).to_bytes(2,'little')
        arm.uc.mem_write(map_at,bytes(data));finish(906);checks.append(label+' exact full fallback')
    restore()
    # Struct starts with uint16 bg[1024]; inspect an occupied retained slot.
    bg=struct.unpack('<1024H',arm.uc.mem_read(r,2048));slot=next(i for i in range(1,1024) if bg[i]<8192)
    assert arm.call('nes_resident287_can',[r,v,slot,bg[slot]])
    for s,tag in [(0,bg[slot]),(1024,bg[slot]),(slot,bg[slot]^1)]:assert not arm.call('nes_resident287_can',[r,v,s,tag])
    checks.append('slot bounds and retained tag mismatch')
    # used[] follows BG, OBJ and both bank residency bitmaps (144 bytes each).
    at=r+2048+512+288+slot//8;arm.uc.mem_write(at,bytes([arm.uc.mem_read(at,1)[0]|1<<(slot%8)]))
    arm.uc.mem_write(v+slot*8,b'\x00'*8)
    assert not arm.call('nes_resident287_can',[r,v,slot,bg[slot]]);checks.append('same-frame wrong exact key rejected')
    restore();arm.call('stop286',[]);assert not arm.call('nes_resident287_can',[r,v,slot,bg[slot]]) and not arm.call('next_step286',[]);checks.append('STOP rejects row reuse and execution')
    result=dict(passed=True,checks=checks,ELF_sha256=sha(a.arm/'planner.elf'),script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
