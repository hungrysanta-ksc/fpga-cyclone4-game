# SPDX-License-Identifier: MIT
"""Execute a five-byte retained-section command in the 727 65816 replay.
The sender is a trace encoder. Its optimistic release is an experiment, not an ARM build.
"""
import argparse
import csv
import json
import struct
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from build_nes_trace_replay import Code
from nes_raw506 import once
from trace_nes_retained738 import observe

SIZE = 1754


def compact(path):
    b = path.read_bytes()
    assert len(b) == 3418
    raw = bytes(b[1121 + tile*64 + plane*16 + row*2 + lane]
                for plane in range(3) for row in range(2)
                for tile in range(32) for lane in range(2))
    return b[:1121] + raw + b[3169:]


def checksum(data):
    s = t = 0
    for (word,) in struct.iter_unpack('<H', data):
        s = (s + word) & 65535
        t = (t + s) & 65535
    return s, t


def receiver(labels, base):
    c = Code(base)
    c.labels.update(labels)
    # 8 WRAM scratch bytes, private to this diagnostic.
    first, second, previous, end = 0x1a80, 0x1a82, 0x1a84, 0x1a86
    def wordop(op, n):
        c.emit(op); c.word(n)
    def require(branch):
        c.emit(branch, 3); c.jump('bad_packet')
    def stop():
        c.emit(0x20); c.word(labels['service'] & 65535)
        c.absolute(0xad,0x1236); c.emit(0xf0,3); c.jump('stop_packet')
    # A reserved ordinary offset selects this entry in the replay.
    for address, value in ((0x1200,0x502),(0x120a,65535),(0x120c,23),(0x120e,0),(0x108a,0)):
        c.absolute(0xad,address); wordop(0xc9,value); require(0xf0)
    c.absolute(0xad,0x1034); c.absolute(0xcd,0x1032); require(0xd0)
    c.emit(0x0a,0x0a,0xaa)
    c.long(0xaf,0x400010); c.long(0x0f,0x400012); require(0xd0)
    for i in (0,2):
        c.long(0xaf,0x400010+i); c.absolute(0xdd,0x14d0+i); require(0xf0)
    stop()
    c.absolute(0x9c,previous)
    wordop(0xa2,0); c.label('entry738')
    c.long(0xbf,0x400018); wordop(0xc9,SIZE); require(0x90)
    c.absolute(0xcd,previous); require(0xb0)
    c.emit(0x1a); c.absolute(0x8d,previous); c.emit(0x3a,0x18)
    c.absolute(0x6d,0x1020); c.emit(0xa8)
    c.emit(0xe2,0x20); c.long(0xbf,0x40001a); c.emit(0xda,0xbb)
    c.long(0x9f,0x7f6500); c.emit(0xfa,0xc2,0x20)
    c.label('partial738'); c.emit(0xe8,0xe8,0xe8); wordop(0xe0,15); c.branch(0xd0,'entry738')
    c.absolute(0x9c,first); c.absolute(0x9c,second)
    c.absolute(0xad,0x1020); c.emit(0xaa,0x18); wordop(0x69,SIZE); c.absolute(0x8d,end)
    c.label('word738')
    c.long(0xbf,0x7f6500); c.emit(0x18); c.absolute(0x6d,first); c.absolute(0x8d,first)
    c.emit(0x18); c.absolute(0x6d,second); c.absolute(0x8d,second)
    c.emit(0xe8,0xe8); c.absolute(0xec,end); c.branch(0xf0,'end738')
    c.emit(0x8a); wordop(0x89,63); c.branch(0xd0,'word738'); stop(); c.jump('word738')
    c.label('end738'); stop()
    for i,src in enumerate((first,second)):
        c.long(0xaf,0x400014+i*2); c.absolute(0xcd,src); require(0xf0)
    wordop(0xa9,SIZE); c.absolute(0x8d,0x108a); c.jump('accepted194')
    return c.finish(), c.labels['partial738']


def run(a):
    a.frames=53
    def edit(s):
        path=a.out/'arrivals.tsv'
        rows=path.read_text().splitlines()
        ordinary=[]
        for i,line in enumerate(rows[:-1]):
            clk,h,_=line.split('\t'); h=bytes.fromhex(h)
            if h[:2]==b'\x03\0' and int.from_bytes(h[8:10],'little')==955:
                serial=h[4:8]
            if h[1]==5 and int.from_bytes(h[8:10],'little')==957:
                ordinary.append(i)
        old=compact(a.trace/'expected-955.bin'); new=compact(a.trace/'expected-957.bin')
        delta=[(i,y) for i,(x,y) in enumerate(zip(old,new)) if x!=y]
        assert len(delta)==5 and ordinary==list(range(len(rows)-10,len(rows)-2))
        original_wire=sum(3+len(bytes.fromhex(rows[i].split('\t')[1])) for i in ordinary)
        t,h,_=rows[ordinary[0]].split('\t'); h=bytearray.fromhex(h)[:16]
        h[10:16]=struct.pack('<HHH',65535,23,0)
        payload=serial+struct.pack('<HH',*checksum(new))+b''.join(struct.pack('<HB',i,y) for i,y in delta)
        _,seal,bulk=rows[-2].split('\t'); seal=bytearray.fromhex(seal)
        seal[2:4]=struct.pack('<H',int.from_bytes(h[2:4],'little')+1)
        # Allow an uninterrupted 187-byte SEAL transaction at the measured SPI clock.
        # Optimistic offer omits firmware/credit latency; the receiver is still serialized.
        seal_t=int(t)+(len(seal)+3)*8*21477272//2625000+1
        if a.mode=='restore':
            image=a.recovery_image.read_bytes() if a.recovery_image else bytes([0xa5])*SIZE
            assert len(image)==SIZE  # STOP may arrive after all five writes, before verification.
            (a.out/'interrupted.bin').write_bytes(image)
            return once(s,"  snap738('before957')",'''  local dirty=file('interrupted.bin'); for i=0,1753 do emu.write(target+i,dirty:byte(i+1),emu.memType.snesWorkRam) end
  snap738('before957')''')

        rows[ordinary[0]:-1]=[f'{t}\t'+(h+payload).hex()+'\t',f'{seal_t}\t'+seal.hex()+'\t'+bulk]
        path.write_text('\n'.join(rows)+'\n',newline='\n')
        labels=json.loads((a.client/'labels.json').read_text())
        data=(a.client/'body.bin').read_bytes();base=0x7e2000+len(data)
        code,partial=receiver(labels,base)
        if a.mode=='floor':
            # Optimistic sensitivity only. Skip the full independent pass after applying changes.
            jump=code.index(bytes([0x9c,0x80,0x1a,0x9c,0x82,0x1a]))
            end=code.rindex(bytes([0xa9,0xda,6,0x8d,0x8a,0x10]))
            code=code[:jump]+b'\x4c'+struct.pack('<H',(base+end)&65535)+code[jump+3:]
        assert base+len(code)<=0x7e3900
        (a.out/'handler.bin').write_bytes(code)
        # Mesen installs the alternate entry only at the reserved packet. This isolates
        # the packet and keeps the original boot time and all previous CPU clocks.
        entry=labels['data']&65535
        install=f"""if pb(0)==2 and pw(10)==65535 and pb(1)==5 then
 local code=file('handler.bin'); for i=1,#code do emu.write({base&65535}+i-1,code:byte(i),emu.memType.snesWorkRam) end
 for i,v in ipairs({{0x4c,{base&255},{(base>>8)&255}}}) do emu.write({entry}+i-1,v,emu.memType.snesWorkRam) end
 end"""
        s=once(s," if pb(0)==7 then tile=tilePayload",install+"\n if pb(0)==7 then tile=tilePayload")
        if a.mode in ('stale','corrupt','stop','partial'):
            s=once(s,"local FAULT=905","local FAULT=957")
            s=once(s,"local MODE='normal'",f"local MODE='{a.mode}'")
            if a.mode=='stale':
                s=once(s," local code=file('handler.bin');"," for i=0,3 do emu.write(0x14d0+4*word(0x1034)+i,0,emu.memType.snesWorkRam) end;local code=file('handler.bin');")
            if a.mode=='corrupt':
                s=once(s," local code=file('handler.bin');"," emu.write(target+36,rd(target+36)~1,emu.memType.snesWorkRam);local code=file('handler.bin');")
            if a.mode=='partial':
                # Malform the third offset after two writes. No partial coverage may be published.
                rows[ordinary[0]]=rows[ordinary[0]].replace((h+payload).hex(),(h+payload[:14]+bytes([255,255])+payload[16:]).hex())
                path.write_text('\n'.join(rows)+'\n',newline='\n')
            if a.mode=='stop':
                s=once(s,' if a==0x6001 then'," if a==0x6001 then\n  if packet and pw(10)==65535 and rd(target+1)==145 then return 128 end")
            s=once(s,"   local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb'", """   assert(word(0x108a)==0 and word(0x14d0)==0 and word(0x14d4)==0)
   assert(word(0x1248)==52 and word(0x124a)==0)
   assert(lastStatus==(MODE=='stop' and 0xe4 or 0xe0))
   snap738('rejected957')
   local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb'""")
        (a.out/'wire.json').write_text(json.dumps(dict(changes=delta,original_wire_B=original_wire,
            delta_wire_B=len(h+payload)+3,handler_B=len(code),checksum=checksum(new),
            seal_offer=seal_t,partial_pc=partial))+'\n')
        return s
    def compare(before,after):
        # Compare all events before the first substituted packet.
        boundary=next(int(r['index']) for r in before if r['g']=='957' and r['section']=='5')
        assert [r for r in before if int(r['index'])<boundary]==[r for r in after if int(r['index'])<boundary]
        return dict(last_ACK=int(next(r['clock'] for r in reversed(after) if r['event']=='ack')),
                    observed_events=len(after))
    with patch.object(replay,'observe',observe):
        if a.mode in ('normal','restore','floor'):
            replay.run(a,edit_script=edit,compare_trace=compare)
        else:
            try:
                replay.run(a,edit_script=edit,compare_trace=compare)
            except AssertionError:  # replay.run requires 53 commits for normal runs
                result=json.loads((a.out/'result.json').read_text())
                assert result['passed'] and result['commits']==52
                assert (a.out/'retained.rgb').read_bytes()==(a.trace/'frame-956.rgb').read_bytes()
            else:
                raise AssertionError('Fault accepted')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','out','mesen','client'):
        p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--mode',choices=('normal','floor','restore','stale','corrupt','stop','partial'),default='normal')
    p.add_argument('--recovery-image',type=Path,help='Section left by a separately canceled session; used in restore mode.')
    run(p.parse_args())
