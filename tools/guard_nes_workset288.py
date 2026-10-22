# SPDX-License-Identifier: MIT
"""Prove index rebuild, kind rejection, union separation and warm reuse gate."""
import argparse,binascii,ctypes,json,struct
from pathlib import Path
from probe_nes_planner285 import Planner
from probe_nes_decode280 import records,chunks
from nes_delta231 import BASE,sha


class Tile(ctypes.Structure):
    _fields_=[('tag',ctypes.c_uint16),('kind',ctypes.c_uint8)]
class Native(ctypes.Structure):
    _fields_=[('maps',ctypes.c_uint16*1056),('rows',ctypes.c_uint8*224),('palette',ctypes.c_uint8*64),
              ('objects',ctypes.c_uint64*128),('raster',ctypes.c_uint64*224),('exceptions',ctypes.c_uint32*128),
              ('tiles',Tile*512),('raw',ctypes.c_uint8*2048),('generation',ctypes.c_uint16),
              ('counts',ctypes.c_uint16*6),('at',ctypes.c_uint16*6),('records',ctypes.c_uint16),
              ('bytes',ctypes.c_uint16),('ntiles',ctypes.c_uint16)]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);elf=a.arm/'planner.elf';arm=Planner(elf,None)
    arm.call('reset285',[]);arm.call('reset280',[]);arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    checks=[];base=arm.symbols['input285'];index=arm.symbols['workset288'];v=arm.symbols['video285']
    assert Native.tiles.offset==5728 and Native.raw.offset==7776
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save()
    def restore(s):arm.uc.mem_write(0x20000000,s[0]);arm.uc.context_restore(s[1])
    def prepare(f):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        assert arm.call('expand286',[]) and arm.call('begin285',[])
    def start():
        for n in ('geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(n,[]),n
    def steps():
        for _ in range(34):
            ok=arm.call('next_step286',[])
            if ok!=1:return ok
        raise AssertionError('unbounded planner')
    def exact(f):
        assert steps()==2
        out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')))
        assert out==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()
        layout=[arm.call('layout285',[i]) for i in range(3)]
        material=b''.join(bytes(arm.uc.mem_read(v+off,n)) for off,n in [(layout[0],4096),(layout[1],512),(layout[2],544),(layout[1]+512,1121),(0,2291),(2292,6)])
        assert material==(BASE/f'probes/nes-wholepath247/jointdecode-test02/run/expected-{f-904}.bin').read_bytes()
    def native():return Native.from_buffer_copy(bytes(arm.uc.mem_read(base,ctypes.sizeof(Native))))
    prepare(905);snap=save();n=native();expected=bytearray(2048)
    for t in n.tiles[:n.ntiles]:expected[t.tag//4]|=t.kind<<((t.tag%4)*2)
    arm.uc.mem_write(index,b'\xff'*2048);before=bytes(arm.uc.mem_read(base,ctypes.sizeof(Native)))
    assert arm.call('geometry_plan286',[]) and bytes(arm.uc.mem_read(index,2048))==expected
    assert bytes(arm.uc.mem_read(base,ctypes.sizeof(Native)))==before
    for name in ('h2early286','input_commit286','begin_step286'):assert arm.call(name,[])
    assert bytes(arm.uc.mem_read(base+Native.raw.offset,512))==bytes(arm.uc.mem_read(arm.symbols['history286']+4398,512))
    exact(905);checks.append('poison rebuilt, native input unchanged, raw512 and plan/metadata exact')
    for label,offset,value in [('invalid kind',Native.tiles.offset+2,b'\x04'),('duplicate tag',Native.tiles.offset+4,struct.pack('<H',n.tiles[0].tag))]:
        restore(snap);arm.uc.mem_write(base+offset,value);assert not arm.call('geometry_plan286',[]) and not arm.word('calls285');checks.append(label+' rejected before callbacks')
    for label,tag,kind in [('missing BG kind',n.maps[0]&8191,2),('missing OBJ kind',n.objects[0]&8191,1)]:
        restore(snap);i=next(i for i,t in enumerate(n.tiles[:n.ntiles]) if t.tag==tag)
        arm.uc.mem_write(base+Native.tiles.offset+i*4+2,bytes([kind]));start();assert steps()==0;checks.append(label+' cannot complete')
    restore(snap);arm.uc.mem_write(index,b'\xff'*2048);arm.uc.mem_write(base+Native.ntiles.offset,b'\0\0');start();assert not any(arm.uc.mem_read(index,2048)) and steps()==0;checks.append('empty workset clears stale valid bits and rejects BG')
    restore(snap);start();arm.call('stop286',[]);arm.uc.mem_write(index,b'\xff'*2048);assert not arm.call('next_step286',[]);checks.append('STOP cannot be revived by index contents')
    restore(snap);start();exact(905);assert arm.call('commit285',[])
    prepare(906);start();exact(906);assert arm.call('commit285',[])
    prepare(907);warm=save();n=native();tag=n.maps[0]&8191;i=next(i for i,t in enumerate(n.tiles[:n.ntiles]) if t.tag==tag)
    arm.uc.mem_write(base+Native.tiles.offset+i*4+2,b'\x02');start();assert steps()==0;checks.append('warm retained map cannot bypass missing BG membership')
    restore(warm);start();exact(907);checks.append('valid warm29 reused rows exact after restored index lifecycle')
    result=dict(passed=True,checks=checks,ELF_sha256=sha(elf),script_sha256=sha(Path(__file__)),extra_ARM_RAM=2048)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
