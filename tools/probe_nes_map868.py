"""Time an ACK-history sparse map receiver on the real 65816 ISA with MMC866 inputs."""
import argparse
import csv
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from build_nes_trace_replay import Code

SPAN = 23 * 64
CLOCK = 21477272


def word(data, at):
    return int.from_bytes(data[at:at+2], 'little')


def receiver(strip=False):
    c = Code(0x8000)

    def imm(op, value):
        c.emit(op)
        c.word(value)

    def reject_if(branch):
        c.emit(branch ^ 0x20, 3)
        c.jump('bad')

    def stop():
        c.emit(0xe2, 0x20)
        c.long(0xaf, 0x006050)
        c.emit(0xc2, 0x20)
        imm(0x29, 1)
        reject_if(0xd0)

    c.emit(0x78, 0x18, 0xfb, 0xc2, 0x30)
    imm(0xa2, 0x1fff)
    c.emit(0x9a, 0xe2, 0x20)
    c.store(0x4200, 0)
    c.store(0x2100, 0x80)
    c.emit(0xa9, 0x7f, 0x48, 0xab)
    c.label('poll')
    c.long(0xaf, 0x00607d)
    c.emit(0xc2, 0x20)
    stop()
    # DP $10/$12 are the validated physical target and peer pointers.
    # DP $14 holds the page relative to the start of a 4 KiB map.
    for offset, dp in ((0, 0x20), (2, 0x22), (4, 0x14)):
        c.long(0xaf, 0x400010 + offset)
        c.emit(0xc5, dp)
        reject_if(0xd0)
    c.emit(0xa5, 0x24)
    reject_if(0xf0)  # both banks have published histories in this epoch
    if strip:
        # Word 6 is the even byte column. Packet length selects one or two columns.
        c.long(0xaf, 0x400016)
        c.emit(0x85, 0x28, 0x89, 1, 0)
        reject_if(0xd0)
        imm(0xc9, 64)
        reject_if(0xb0)
        c.emit(0xa5, 0x26)
        imm(0xc9, 54)
        c.branch(0xf0, 'one')
        imm(0xc9, 100)
        reject_if(0xd0)
        c.emit(0xa5, 0x28)
        imm(0xc9, 62)
        reject_if(0xb0)
        c.emit(0x1a, 0x1a)
        c.branch(0x80, 'limit')
        c.label('one')
        c.emit(0xa5, 0x28)
        c.label('limit')
        c.emit(0x1a, 0x1a, 0x85, 0x2a)
        imm(0xa2, 8)
        c.emit(0x86, 0x2c, 0x64, 0x2e)
        c.label('column')
        stop()
        c.emit(0xa5, 0x2e, 0xc5, 0x28)
        c.branch(0x90, 'omit')
        c.emit(0xc5, 0x2a)
        c.branch(0xb0, 'omit')
        c.emit(0xa8, 0xa6, 0x2c)
        c.label('write_cell')
        c.long(0xbf, 0x400010)
        c.emit(0x91, 0x10, 0xd1, 0x10)
        reject_if(0xd0)
        c.emit(0xe8, 0xe8, 0x98, 0x18)
        imm(0x69, 64)
        c.emit(0xa8)
        imm(0xc9, SPAN)
        c.branch(0x90, 'write_cell')
        c.emit(0x86, 0x2c)
        c.jump('next_column')
        c.label('omit')
        c.emit(0x18, 0x65, 0x14, 0xaa)
        for row in range(23):
            c.absolute(0xbd, 0x4000+64*row)
            c.absolute(0xdd, 0xc000+64*row)
            if row % 8 == 7 or row == 22:
                c.branch(0xf0, f'next{row}')
                c.label(f'fault{row//8}')
                c.jump('bad')
                c.label(f'next{row}')
            else:
                c.branch(0xd0, f'fault{row//8}')
        c.label('next_column')
        c.emit(0xe6, 0x2e, 0xe6, 0x2e, 0xa5, 0x2e)
        imm(0xc9, 64)
        c.branch(0xf0, 'done')
        c.jump('column')
        c.label('done')
        stop()
    else:
        scalar(c, imm, reject_if, stop)
    return finish(c, imm)


def scalar(c, imm, reject_if, stop):
    c.long(0xaf, 0x400016)
    reject_if(0xf0)
    imm(0xc9, 59)
    reject_if(0xb0)
    c.emit(0x0a, 0x0a, 0x18)
    imm(0x69, 8)
    c.emit(0xc5, 0x26)
    reject_if(0xd0)
    # Normalize only listed words to the peer for the exact omission check.
    for name in ('normalize', 'patch'):
        imm(0xa2, 8)
        c.emit(0x64, 0x28)
        c.label(name)
        c.long(0xbf, 0x400010)
        imm(0xc9, SPAN)
        reject_if(0xb0)
        c.emit(0x89, 1, 0)
        reject_if(0xd0)
        c.emit(0xc5, 0x28)
        reject_if(0x90)
        c.emit(0xa8, 0x1a, 0x85, 0x28)
        if name == 'normalize':
            c.emit(0xb1, 0x12)
        else:
            c.long(0xbf, 0x400012)
        c.emit(0x91, 0x10)
        if name == 'patch':
            c.emit(0xd1, 0x10)
            reject_if(0xd0)
        stop()
        c.emit(0xe8, 0xe8, 0xe8, 0xe8, 0xe4, 0x26)
        c.branch(0xd0, name)
        if name == 'normalize':
            c.emit(0xa6, 0x14)
            imm(0xa0, 23)
            c.label('row')
            for group in range(4):
                for off in range(16*group, 16*group+16, 2):
                    c.absolute(0xbd, 0x4000+off)
                    c.absolute(0xdd, 0xc000+off)
                    c.branch(0xd0, f'damage{group}')
                c.branch(0x80, f'pass{group}')
                c.label(f'damage{group}')
                c.jump('bad')
                c.label(f'pass{group}')
            stop()
            c.emit(0x8a, 0x18)
            imm(0x69, 64)
            c.emit(0xaa, 0x88)
            c.branch(0xf0, 'checked')
            c.jump('row')
            c.label('checked')


def finish(c, imm):
    imm(0xa9, 1)
    c.branch(0x80, 'return')
    c.label('bad')
    c.emit(0x64, 0x24)
    imm(0xa9, 0)
    c.label('return')
    c.emit(0xe2, 0x20)
    c.long(0x8f, 0x00607e)
    c.jump('poll')
    body = c.finish()
    rom = bytearray([255]) * 32768
    rom[:len(body)] = body
    rom[0x7fc0:0x7fd5] = b'MAP868 RECEIVER PROBE'.ljust(21)
    rom[0x7fd5:0x7fdc] = bytes((0x20, 0, 5, 0, 1, 0, 0))
    for pos in range(0x7fe0, 0x8000, 2):
        struct.pack_into('<H', rom, pos, 0x8000)
    return rom, len(body)


def phase_cases(folder, strip):
    ranges = defaultdict(list)
    packets = (folder/'packets.jsonl').read_text().splitlines()
    events = [e for e in json.loads((folder/'events.json').read_bytes()) if e.get('opcode') == '0xe1']
    window = {}
    with (folder/'window.csv').open() as f:
        for row in csv.DictReader(f):
            if row['event'] in ('load', 'ack'):
                window[int(row['index']), row['event']] = int(row['clock'])
    banks = {}
    for i, (record, e) in enumerate(zip(packets, events, strict=True), 1):
        _, when, payload, _ = json.loads(record)
        b = bytes.fromhex(payload)
        g = word(b, 8)
        assert len(b)+3 == e['bytes'] and abs(e['clock']-when) <= 1
        if b[0] == 1:
            banks[g] = b[18]
        if g < 907 or b[1] != 2 or b[0] not in (2, 4, 9):
            continue
        assert b[0] in (2, 4), 'unexpected baseline column receiver'
        at = word(b, 10)
        size = len(b)-16 if b[0] == 2 else word(b, 14)
        ranges[g].append((at, size, len(b)+3, window[i,'ack']-window[i,'load']))
    cases, records = [], []
    for g in range(907, 967):
        a, b, goal = [(folder/f'map-{j}.bin').read_bytes() for j in range(g-2, g+1)]
        assert len(a) == len(b) == len(goal) == 4096 and banks[g] == banks[g-2] != banks[g-1]
        parts = ranges[g]
        for page in (0, 2048):
            group = [p for p in parts if page <= p[0] and p[0]+p[1] <= page+SPAN]
            if not group:
                continue
            if sorted(x for at,n,_,_ in group for x in range(at,at+n)) != list(range(page,page+SPAN)):
                continue
            offsets = [i for i in range(page,page+SPAN,2)
                       if goal[i:i+2] != a[i:i+2] or goal[i:i+2] != b[i:i+2]]
            if not 0 < len(offsets) <= 58:
                continue
            data = struct.pack('<IHH',g-2,page,len(offsets)) + b''.join(
                struct.pack('<H',i-page)+goal[i:i+2] for i in offsets)
            if strip:
                cols=sorted({(i-page)%64 for i in offsets})
                if len(cols) not in (1,2) or cols[-1]-cols[0]!=2*(len(cols)-1):
                    continue
                if len(offsets)!=23*len(cols):
                    continue
                data=struct.pack('<IHH',g-2,page,cols[0])+b''.join(
                    goal[j+col:j+col+2] for col in cols for j in range(page,page+SPAN,64))
            pos = slice(page,page+SPAN)
            cases.append(dict(g=g, bank=banks[g], page=page, old=a[pos].hex(), peer=b[pos].hex(),
                              goal=goal[pos].hex(), data=data.hex()))
            records.append(dict(g=g,page=page,old_wire=sum(p[2] for p in group),new_wire=len(data)+19,
                                old_service=sum(p[3] for p in group),old_packets=len(group)))
    return cases, records


LUA = r'''
local index=0; local c; local start; local checks; local dst; local peer
local writable=emu.memType.snesWorkRam
local function put16(i,v) emu.write(i,v&255,writable); emu.write(i+1,(v>>8)&255,writable) end
local function copy(i,h) for j=1,#h,2 do emu.write(i+(j-1)//2,tonumber(h:sub(j,j+1),16),writable) end end
local function match(i,h) for j=1,#h,2 do assert(emu.read(i+(j-1)//2,writable)==tonumber(h:sub(j,j+1),16)) end end
local log=assert(io.open(OUT,'w'))
emu.addMemoryCallback(function()
  index=index+1; c=CASES[index]; if not c then log:close(); emu.stop(0); return 0 end
  dst=0x4000+c.bank*0x8000+c.page;peer=(dst~0x8000)
  copy(0x10000+dst,c.old); copy(0x10000+peer,c.peer)
  put16(0x10,dst);put16(0x12,peer);put16(0x14,c.page);put16(0x20,c.g-2);put16(0x22,0)
  put16(0x24,c.valid or 1);put16(0x26,c.length or #c.data//2)
  checks=0;start=emu.getState().masterClock;return 1
end,emu.callbackType.read,0x607d)
emu.addMemoryCallback(function(a)
 local i=(a-0x400010)*2+1
 assert(i+1<=#c.data);return tonumber(c.data:sub(i,i+1),16)
end,emu.callbackType.read,0x400010,0x4000ff)
emu.addMemoryCallback(function() checks=checks+1;return c.stop==checks and 1 or 0 end,emu.callbackType.read,0x6050)
emu.addMemoryCallback(function(_,v)
 assert(v==(c.want or 1),'status '..index..' got '..v)
 match(0x10000+peer,c.peer)
 if v==1 then match(0x10000+dst,c.goal) else assert(emu.read(0x24,writable)==0) end
 log:write(index..','..(emu.getState().masterClock-start)..'\n');log:flush()
end,emu.callbackType.write,0x607e)
'''


def guards(case, strip):
    data = bytes.fromhex(case['data'])
    if strip:
        col=word(data,6)
        offsets=[row*64+x for row in range(23) for x in range(col,col+(len(data)-8)//23,2)]
    else:
        offsets = [word(data,j) for j in range(8,len(data),4)]
    hole = next(i for i in range(0,SPAN,2) if i not in offsets)
    def flip(h, i):
        b = bytearray.fromhex(h)
        b[i] ^= 1
        return b.hex()
    for side in ('old','peer'):
        yield dict(case, **{side:flip(case[side],hole)}, want=0)
    for extra in (dict(valid=0), dict(length=len(data)-1), dict(stop=3),
                  dict(stop=12 if strip else len(offsets)+6), dict(stop=33 if strip else len(offsets)+26),
                  dict(data=flip(case['data'],0)),
                  dict(data=(data[:6]+b'\xff\x00'+data[8:] if strip else data[:12]+data[8:12]+data[16:]).hex())):
        yield dict(case, **extra, want=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--strip',action='store_true')
    for arg in ('temp','mesen','work','out'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=False)
    rom,size=receiver(a.strip)
    (a.work/'kernel.sfc').write_bytes(rom)
    phases=[]
    for n in (1,2):
        phases.append(phase_cases(a.temp/f'nes-tile821-demo-jointmirror-p{n}-866-on',a.strip))
    cases=phases[0][0]
    assert cases == phases[1][0] and len(cases)>0
    all_cases=cases+list(guards(cases[0],a.strip))
    rows=['{'+','.join(k+'='+json.dumps(v) for k,v in case.items())+'}' for case in all_cases]
    output_dir=tempfile.TemporaryDirectory(prefix='nes-map868-')
    csv_file=Path(output_dir.name)/'cpu.csv'
    script='local CASES={'+',\n'.join(rows)+'}\nlocal OUT='+json.dumps(csv_file.as_posix())+'\n'+LUA
    (a.work/'bench.lua').write_text(script,encoding='utf-8')
    env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet')
    with (a.work/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen.resolve()),'--testRunner',str((a.work/'bench.lua').resolve()),
                        str((a.work/'kernel.sfc').resolve()),'--timeout=60',
                        '--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],
                       cwd=a.work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90,check=True)
    (a.work/'cpu.csv').write_bytes(csv_file.read_bytes())
    output_dir.cleanup()
    measured=list(csv.reader((a.work/'cpu.csv').read_text().splitlines()))
    assert [int(i) for i,t in measured]==list(range(1,len(all_cases)+1))
    results=dict(kernel_bytes=size,kernel_sha256=hashlib.sha256(rom).hexdigest(),
                 passed_guards=len(all_cases)-len(cases),sample_frames=60,phases=[])
    for _,records in phases:
        for row,(_,t) in zip(records,measured):
            row['new_service']=int(t)
        results['phases'].append(dict(frames=records, totals={k:sum(row[k] for row in records)
            for k in ('old_wire','new_wire','old_service','new_service','old_packets')}))
    a.out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
