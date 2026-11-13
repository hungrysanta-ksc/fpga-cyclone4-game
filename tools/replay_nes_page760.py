# SPDX-License-Identifier: MIT
"""Measure one checked warm map-page command in the 753 receiver replay."""
import argparse
import json
from hashlib import sha256
import struct
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from replay_nes_delta738 import checksum
from trace_nes_owner739 import observe

OFFSET = 2048
SIZE = 1536
GROUP = 4
RECEIVER = '74818b9f1ff02db6be843f4355f74ad57d42d99ea6f4cefbbbe9ba643e16b693'


def encode(old, new, serial, indexed):
    assert len(old) == len(new) == SIZE and serial
    mask = bytearray(SIZE // GROUP // 8)
    changes = bytearray()
    offsets = bytearray()
    for at in range(0, SIZE, GROUP):
        if old[at:at+GROUP] != new[at:at+GROUP]:
            i = at // GROUP
            mask[i//8] |= 1 << (i % 8)
            changes.extend(new[at:at+GROUP])
            offsets.extend(struct.pack('<H', at) + new[at:at+GROUP])
    payload = offsets if indexed else mask + changes
    return struct.pack('<IHH', serial, *checksum(new)) + payload


def receiver(labels, base, indexed):
    """One bounded bitmap pass, then a word-unrolled independent WRAM readback."""
    c = Code(base)
    c.labels.update(labels)
    # Free diagnostic scratch outside the original 751 body and target banks.
    bits, source, last, count, first, second = range(0x1a80, 0x1a8c, 2)
    def imm(op, value):
        c.emit(op)
        c.word(value)
    def require(op):
        c.emit(op, 3)
        c.jump('bad_packet')
    def stop():
        call(c, 'service')
        c.absolute(0xad, 0x1236)
        c.emit(0xf0, 3)
        c.jump('stop_packet')

    # Enter with the actual frame, FIFO length, sequence and generation already
    # checked by 751. Route only this map opcode; OAM follows its original entry.
    c.absolute(0xad, 0x1200)
    imm(0xc9, 0x0209)
    c.emit(0xf0, 3)
    c.jump('reuse635')
    for addr, value in ((0x120a, OFFSET), (0x120e, SIZE)):
        c.absolute(0xad, addr)
        imm(0xc9, value)
        require(0xf0)
    c.absolute(0xad, 0x120c)
    imm(0xc9, 14 if indexed else 56)
    require(0xb0)
    if not indexed:
        imm(0x89, 3)
        require(0xf0)
    c.emit(0x18)
    imm(0x69, 16)
    c.absolute(0x8d, last)
    c.absolute(0xad, 0x1034)
    c.absolute(0xcd, 0x1032)
    require(0xd0)
    c.emit(0x0a, 0x0a, 0xaa)
    c.long(0xaf, 0x400010)
    c.long(0x0f, 0x400012)
    require(0xd0)
    for i in (0, 2):
        c.long(0xaf, 0x400010+i)
        c.absolute(0xdd, 0x14d0+i)
        require(0xf0)

    c.absolute(0xad, 0x1020)
    c.emit(0x18)
    imm(0x69, 0x5000+OFFSET)
    c.emit(0x85, 0x7a, 0xe2, 0x20)
    c.store(0x7c, 0x7f)
    c.emit(0xc2, 0x20)
    if indexed:
        # Each tuple contains one aligned byte offset and two literal words.
        # A monotonically increasing frontier rejects duplicates and overlap.
        c.absolute(0x9c, bits)
        imm(0xa2, 24)
        c.label('next_index760')
        stop()
        c.emit(0x8a, 0x18)
        imm(0x69, 6)
        c.absolute(0xcd, last)
        c.branch(0x90, 'index_fits760')
        require(0xf0)
        c.label('index_fits760')
        c.long(0xbf, 0x400000)
        imm(0x89, 3)
        require(0xf0)
        imm(0xc9, SIZE)
        require(0x90)
        c.absolute(0xcd, bits)
        require(0xb0)
        c.emit(0xa8, 0x18)
        imm(0x69, 4)
        c.absolute(0x8d, bits)
        c.long(0xbf, 0x400002)
        c.emit(0x97, 0x7a, 0xc8, 0xc8)
        c.long(0xbf, 0x400004)
        c.emit(0x97, 0x7a, 0x8a, 0x18)
        imm(0x69, 6)
        c.emit(0xaa)
        c.absolute(0xec, last)
        c.branch(0xd0, 'next_index760')
    else:
        imm(0xa9, 16+56)
        c.absolute(0x8d, source)
        imm(0xa0, 0)
        c.label('next_mask760')
        stop()
        c.emit(0x98)
        for _ in range(5):
            c.emit(0x4a)
        c.emit(0xaa)
        c.long(0xbf, 0x400018)  # one 16-bit mask for 64 bytes
        c.absolute(0x8d, bits)
        imm(0xa9, 16)
        c.absolute(0x8d, count)
        c.label('group760')
        c.absolute(0x4e, bits)
        c.branch(0x90, 'skip760')
        c.absolute(0xae, source)
        c.emit(0x8a, 0x18)
        imm(0x69, 4)
        c.absolute(0xcd, last)
        c.branch(0x90, 'copy760')
        require(0xf0)
        c.label('copy760')
        c.absolute(0x8d, source)
        c.long(0xbf, 0x400000)
        c.emit(0x97, 0x7a, 0xc8, 0xc8)
        c.long(0xbf, 0x400002)
        c.emit(0x97, 0x7a, 0xc8, 0xc8)
        c.branch(0x80, 'group_done760')
        c.label('skip760')
        c.emit(0xc8, 0xc8, 0xc8, 0xc8)
        c.label('group_done760')
        c.absolute(0xce, count)
        c.branch(0xd0, 'group760')
        imm(0xc0, SIZE)
        c.branch(0xd0, 'next_mask760')
        c.absolute(0xad, source)
        c.absolute(0xcd, last)
        require(0xf0)

    # Read the destination, including every omitted group. Keep the first sum
    # in A, unroll eight words, and service STOP once per row.
    c.absolute(0x9c, first)
    c.absolute(0x9c, second)
    c.absolute(0xae, 0x1020)
    imm(0xa0, SIZE//64)
    c.label('check_row760')
    stop()
    imm(0xa9, 4)
    c.absolute(0x8d, count)
    c.label('check_words760')
    c.absolute(0xad, first)
    for i in range(0, 16, 2):
        c.emit(0x18)
        c.long(0x7f, 0x7f5800+i)  # ADC long,X
        c.absolute(0x8d, first)
        c.emit(0x18)
        c.absolute(0x6d, second)
        c.absolute(0x8d, second)
        if i != 14:
            c.absolute(0xad, first)
    c.emit(0x8a, 0x18)
    imm(0x69, 16)
    c.emit(0xaa)
    c.absolute(0xce, count)
    c.emit(0xf0, 3)
    c.jump('check_words760')
    c.emit(0x88, 0xf0, 3)
    c.jump('check_row760')
    for i, addr in ((0, first), (2, second)):
        c.long(0xaf, 0x400014+i)
        c.absolute(0xcd, addr)
        require(0xf0)
    stop()
    # Register coverage and the real DMA descriptor only after all checks.
    imm(0xa9, SIZE)
    c.absolute(0x8d, 0x120c)
    imm(0xa9, OFFSET+SIZE)
    c.absolute(0x8d, 0x1084)
    imm(0xa2, 4)
    call(c, 'mark212')
    require(0xb0)
    c.jump('accepted')
    return c.finish(), c.labels


def run(a):
    a.frames = 53
    assert sha(a.client/'body.bin') == RECEIVER
    labels = json.loads((a.client/'labels.json').read_text())
    body = (a.client/'body.bin').read_bytes()
    # Patch the JMP to the OAM dispatch, after generic queue/identity checks.
    signature = bytes.fromhex('c90900d0034c') + struct.pack('<H', labels['reuse635'] & 65535)
    assert body.count(signature) == 1
    jump = 0x2000 + body.index(signature) + 5
    base = 0x7e2000 + len(body)
    code, points = receiver(labels, base, a.indexed)
    entry = 'next_index760' if a.indexed else 'next_mask760'
    assert base + len(code) <= 0x7e4000
    report = {}

    def edit(s):
        # A longer head may hold the last credit beyond the old arrival.
        # Keep the FIFO limit and retry at the next poll after a real ACK.
        s=once(s,"  assert(sent-retired<4,'queue overflow')",
               "  if sent-retired>=4 then return end")
        path = a.out/'arrivals.tsv'
        rows = path.read_text().splitlines()
        packets = [bytes.fromhex(line.split('\t')[1]) for line in rows[:-1]]
        def word(b, index):
            return struct.unpack_from('<H', b, index)[0]
        ids = [i for i,b in enumerate(packets) if word(b,8)==957 and b[:2]==bytes((2,2))
               and OFFSET <= word(b,10) < OFFSET+SIZE]
        assert len(ids)==8 and ids==list(range(ids[0], ids[0]+8))
        assert [word(packets[i],10) for i in ids]==list(range(OFFSET,OFFSET+SIZE,192))
        new = b''.join(packets[i][16:] for i in ids)
        page = lambda g: (a.trace/f'map-{g}.bin').read_bytes()[OFFSET:OFFSET+SIZE]
        assert new==page(957)
        seal, = [b for b in packets if b[0]==3 and word(b,8)==955]
        old = page(955)
        compact = encode(old, new, int.from_bytes(seal[4:8],'little'), a.indexed)
        h = bytearray(packets[ids[0]][:16])
        h[0] = 9
        struct.pack_into('<HH',h,12,len(compact),SIZE)
        packet = h+compact
        assert len(packet)<=256
        report.update(wire_B=len(packet)+3, original_B=sum(len(packets[i])+3 for i in ids),
                      handler_B=len(code), changes=sum(new[i:i+4]!=old[i:i+4] for i in range(0,SIZE,4)), payload_SHA=sha256(compact).hexdigest())
        # Give the bundled head the first old packet's offer, optimistically.
        # Later packets keep the original producer release times and sequence
        # numbers are rebound to the replacement. This tests service in isolation.
        rows[ids[0]] = rows[ids[0]].split('\t')[0]+'\t'+packet.hex()+'\t'
        for i in range(ids[-1]+1,len(packets)):
            t,hx,tile = rows[i].split('\t')
            b = bytearray.fromhex(hx)
            struct.pack_into('<H',b,2,word(b,2)-7)
            rows[i] = '\t'.join((t,b.hex(),tile))
        del rows[ids[0]+1:ids[-1]+1]
        path.write_text('\n'.join(rows)+'\n',encoding='ascii',newline='\n')
        (a.out/'handler.bin').write_bytes(code)
        install = f"""if pw(8)==957 and pb(0)==9 and pb(1)==2 then
 local h=file('handler.bin')
 for i=1,#h do emu.write({base&65535}+i-1,h:byte(i),emu.memType.snesWorkRam) end
 for i,b in ipairs({{0x4c,{base&255},{(base>>8)&255}}}) do emu.write({jump}+i-1,b,emu.memType.snesWorkRam) end
 end"""
        if a.fault:
            s=once(s,"local MODE='normal'","local MODE='page_fault760'")
            s=once(s,'local FAULT=905','local FAULT=957')
            if a.fault=='retained':
                untouched=next(i for i in range(0,SIZE,GROUP) if old[i:i+GROUP]==new[i:i+GROUP])
                install=install.replace(" local h=file",f"""
 local target=0x15800+word(0x1020)+{untouched}
 emu.write(target,rd(target)~1,emu.memType.snesWorkRam)
 local h=file""")
            elif a.fault=='partial':
                s=once(s,' if a==0x6001 then',f""" if a==0x6001 then
  if packet and pw(8)==957 and pb(0)==9 and pb(1)==2 and word(0x1a80)=={a.stop_after} then return 128 end""")
        s=once(s,' if pb(0)==7 then tile=tilePayload',install+'\n if pb(0)==7 then tile=tilePayload')
        s=once(s,'(pb(0)==2 or pb(0)==4) then','(pb(0)==2 or pb(0)==4 or pb(0)==9) then')
        times='\n'.join(f"checkedMem527(function() if packet and pb(0)==9 and pb(1)==2 then sample516('{name}') end end,emu.callbackType.exec,{points[name]})"
                        for name in (entry,'check_row760'))
        return once(s,'local function loaded()',times+'\nlocal function loaded()')

    def measure(before,after):
        index=next(int(r['index']) for r in after if r['g']=='957' and r['op']=='9' and r['section']=='2')
        assert [r for r in before if int(r['index'])<index]==[r for r in after if int(r['index'])<index]
        events=[r for r in after if int(r['index'])==index]
        def clocks(event):
            return [int(r['clock']) for r in events if r['event']==event]
        load,=clocks('load')
        ack,=clocks('ack')
        masks,checks=clocks(entry),clocks('check_row760')
        assert len(checks)==24 and len(masks)==(report['changes'] if a.indexed else 24)
        report.update(head_clock=load,ack_clock=ack,entry_clocks=masks[0]-load,
                      restore_clocks=checks[0]-masks[0],check_and_reply_clocks=ack-checks[0],
                      service_clocks=ack-load)
        return report
    if a.fault=='partial':
        assert a.indexed
        old=(a.trace/'map-955.bin').read_bytes()
        new=(a.trace/'map-957.bin').read_bytes()
        a.stop_after=4+next(i for i in range(0,SIZE,4) if old[OFFSET+i:OFFSET+i+4]!=new[OFFSET+i:OFFSET+i+4])
    with patch.object(replay,'observe',observe):
        try:
            replay.run(a,edit_script=edit,compare_trace=measure)
        except AssertionError:
            if not a.fault:
                raise
            result=json.loads((a.out/'result.json').read_text())
            assert result['passed'] and result['commits']==52
            assert result['last_status']==(0xe4 if a.fault=='partial' else 0xe0)
            assert sha(a.out/'retained.rgb')==sha(a.trace/'frame-956.rgb')
            report.update(fault=a.fault,commits=52,status=result['last_status'],retained_RGB=sha(a.out/'retained.rgb'))
        else:
            assert not a.fault, 'fault accepted'
    (a.out/'cost760.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','mesen','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--indexed',action='store_true')
    p.add_argument('--fault',choices=('retained','partial'))
    run(p.parse_args())
