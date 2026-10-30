# SPDX-License-Identifier: MIT
"""496: coalesced bulk ownership in the existing conditional65816 schedule.
Actual RTL append rule, not RTL execution or actual ARM/IRQ/ROM clock.
"""
import json,struct,runpy,shutil
from pathlib import Path
import test_nes_output489_snes as base
original=base.prepare

def prepare(a,d,compact):
    raw=d/'uncoalesced';raw.mkdir();total=original(a,raw,compact)
    output=[];token=0;seq=0;generation=None;oldtiles=[]
    for i in range(1,total+1):
        b=bytearray((raw/f'req-{i:04d}.bin').read_bytes());tile=(raw/f'tile-{i:04d}.bin')
        data=tile.read_bytes() if tile.exists() else None
        if data is not None:oldtiles.append((b[1],struct.unpack_from('<H',b,8)[0],struct.unpack_from('<H',b,10)[0],data))
        if data is not None and output and output[-1][1] is not None:
            p,v=output[-1]
            same=p[1]==b[1] and p[8:10]==b[8:10]
            contiguous=struct.unpack_from('<H',p,10)[0]+len(v)==struct.unpack_from('<H',b,10)[0]
            if same and contiguous and len(v)+len(data)<=2048:
                output[-1]=(p,v+data);struct.pack_into('<H',p,14,len(v)+len(data));continue
        output.append((b,data))
    rebuilt=[];chunks=0
    for i,(b,data) in enumerate(output,1):
        g=struct.unpack_from('<H',b,8)[0]
        if generation!=g:generation=g;seq=0
        struct.pack_into('<H',b,2,seq);seq+=1
        if data is not None:
            assert 0<len(data)<=2048
            struct.pack_into('<I',b,16,token);token+=1;chunks+=1
            size=32 if b[1] else 16;offset=struct.unpack_from('<H',b,10)[0]
            for at in range(0,len(data),size):rebuilt.append((b[1],g,offset+at,data[at:at+size]))
            (d/f'tile-{i:04d}.bin').write_bytes(data)
        (d/f'req-{i:04d}.bin').write_bytes(b)
    assert rebuilt==oldtiles,'coalescing changed tile order/destination/bytes'
    for p in raw.glob('expected-*.bin'):shutil.copyfile(p,d/p.name)
    (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b,_ in output))
    (d/'coalescing496.json').write_text(json.dumps({'old_packets':total,'packets':len(output),'tile_plans':len(oldtiles),'tile_chunks':chunks,'tile_bytes':sum(len(x[3])for x in oldtiles),'ordered_tiles_equal':True},indent=2)+'\n')
    return len(output)

if __name__=='__main__':
    base.prepare=prepare
    runpy.run_path(str(Path(__file__).with_name('test_nes_status495_schedule.py')),run_name='__main__')
