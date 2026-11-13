# SPDX-License-Identifier: MIT
"""753 receiver microbenchmark. Build an ACK-bound row mirror, then re-read WRAM."""
import argparse
import csv
import json
import struct
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from replay_nes_page760 import SIZE, OFFSET, RECEIVER, encode, receiver
from trace_nes_owner739 import observe

# Diagnostic one-page WRAM allocation. No production ROM/WRAM-fit claim.
CODE = 0x7e8000
MIRROR = 0x7ea000
PAGE = 0x7f5800
STATE, CURSOR, BANK, START, END, EXPECT1, EXPECT2 = range(0x1aa0, 0x1aae, 2)
SUM1, SUM2 = 0x1aae, 0x1ab0
SERIAL = 0x1ab2  # 32-bit
ARMED, READY = 1, 2


def build(body, labels, floor):
    c = Code(CODE)
    c.labels.update(labels)
    hooks = []
    def imm(op, value):
        c.emit(op)
        c.word(value)
    def lda(a):
        c.absolute(0xad, a)
    def sta(a):
        c.absolute(0x8d, a)
    def zero(a):
        c.absolute(0x9c, a)
    def stop():
        call(c, 'service')
        lda(0x1236)
        c.emit(0xf0, 3)
        c.jump('stop_packet')
    def require_equal():
        c.emit(0xf0, 3)
        c.jump('bad_packet')
    def hook(site, original, target, op):
        at = site & 65535
        assert body[at-0x2000:at-0x2000+3] == bytes.fromhex(original)
        hooks.append((at, op, target))

    # Collect a reference directly from the eight admitted, immutable source
    # heads on the first complete page after instrumentation is armed.
    # Reject out-of-order/incomplete coverage by withholding the idle proof.
    c.label('capture761')
    lda(STATE)
    c.branch(0xd0,'accepted761')
    lda(0x1200)
    imm(0xc9,0x0202)
    c.branch(0xd0,'accepted761')
    lda(0x120a)
    c.emit(0x38)
    imm(0xe9,OFFSET)
    c.absolute(0xcd, CURSOR)
    c.branch(0xd0,'accepted761')
    imm(0xc9,SIZE-192+1)
    c.branch(0xb0,'accepted761')
    lda(0x120c)
    imm(0xc9,192)
    c.branch(0xd0,'accepted761')
    imm(0xa2,0)
    c.label('capture_word761')
    lda(SUM1)
    c.emit(0x18)
    c.long(0x7f,0x400010)
    sta(SUM1)
    c.emit(0x18)
    c.absolute(0x6d,SUM2)
    sta(SUM2)
    c.emit(0xe8,0xe8,0x8a)
    imm(0x89,63)
    c.branch(0xd0,'capture_word761')
    stop()
    imm(0xe0,192)
    c.branch(0xd0,'capture_word761')
    lda(CURSOR)
    c.emit(0x18)
    imm(0x69,192)
    sta(CURSOR)
    c.label('accepted761')
    lda(0x1200)
    c.absolute(0x4c,(labels['accepted']+3)&65535)
    hook(labels['accepted'],'ad0012','capture761',0x4c)

    # Actual successful SEAL ACK has already strobed. Keep the normal
    # per-bank serial publication, including its high word.
    c.label('publish761')
    c.absolute(0x9d,0x14d2)
    lda(STATE)
    c.branch(0xd0,'pub_return761')
    lda(CURSOR)
    imm(0xc9,SIZE)
    c.branch(0xf0,'full_page761')
    call(c,'burn761')
    c.emit(0x60)
    c.label('full_page761')
    lda(0x1020)
    c.branch(0xf0,'bank_ok761')
    call(c,'burn761')
    c.emit(0x60)
    c.label('bank_ok761')
    for src,dst in ((0x1222,SERIAL),(0x1224,SERIAL+2),(0x1020,BANK),(SUM1,EXPECT1),(SUM2,EXPECT2)):
        lda(src)
        sta(dst)
    for addr in (SUM1,SUM2,CURSOR):
        zero(addr)
    imm(0xa9,ARMED)
    sta(STATE)
    c.label('published761')
    c.emit(0x60)
    c.label('pub_return761')
    c.emit(0x60)
    hook(labels['nohistory635']-3,'9dd214','publish761',0x20)

    c.label('idle761')
    lda(STATE)
    imm(0xc9,ARMED)
    c.emit(0xf0,3)
    c.jump('idle_done761')
    # The caller already saw an empty head. Check STOP and newly arrived head
    # again; a 32-byte quantum bounds the following non-preemptible work.
    c.emit(0xe2,0x20)
    lda(0x6001)
    c.emit(0x10,3)
    c.jump('idle8_done761')
    lda(0x6000)
    c.emit(0x29,1)
    c.emit(0xf0,3)
    c.jump('idle8_done761')
    c.emit(0xc2,0x20)
    c.label('read_chunk761')
    lda(CURSOR)
    c.emit(0x18)
    c.absolute(0x6d,BANK)
    c.emit(0xaa)
    c.emit(0x18)
    imm(0x69,32)
    sta(END)
    c.label('idle_word761')
    # One saved page, bank 0 only. Both long-indexed accesses share X.
    for delta in (0,2,4,6):
        c.long(0xbf,PAGE+delta)
        c.long(0x9f,MIRROR+delta)
        c.emit(0x18)
        c.absolute(0x6d,SUM1)
        sta(SUM1)
        c.emit(0x18)
        c.absolute(0x6d,SUM2)
        sta(SUM2)
    c.emit(0x8a,0x18)
    imm(0x69,8)
    c.emit(0xaa)
    c.absolute(0xec,END)
    c.branch(0xd0,'idle_word761')
    c.absolute(0x8e,CURSOR)
    imm(0xe0,SIZE)
    c.branch(0xd0,'idle_yield761')
    for a,b in ((SUM1,EXPECT1),(SUM2,EXPECT2)):
        lda(a)
        c.absolute(0xcd,b)
        c.branch(0xd0,'invalidate_idle761')
    imm(0xa9,READY)
    sta(STATE)
    c.label('idle_complete761')
    c.emit(0xea)
    c.label('idle_yield761')
    c.branch(0x80,'idle_done761')
    c.label('invalidate_idle761')
    call(c,'burn761')
    c.branch(0x80,'idle_done761')
    c.label('idle8_done761')
    c.emit(0xc2,0x20)
    c.label('idle_done761')
    lda(0x1228)
    c.emit(0x60)
    hook(labels['poll']+19,'ad2812','idle761',0x20)

    c.label('clear761')
    # Stop/failure invalidates the page history as well as existing serials.
    for a in (STATE,CURSOR,SERIAL,SERIAL+2,SUM1,SUM2):
        zero(a)
    c.absolute(0x9c,0x14d0)
    c.absolute(0x4c,(labels['invalidate635']+3)&65535)
    hook(labels['invalidate635'],'9cd014','clear761',0x4c)

    # Ordinary map writes touching the saved page burn its reusable identity.
    c.label('ordinary_write761')
    lda(STATE)
    c.branch(0xf0,'ordinary_done761')
    imm(0xe0,4)
    c.branch(0xd0,'ordinary_done761')
    lda(0x1020)
    c.absolute(0xcd,BANK)
    c.branch(0xd0,'ordinary_done761')
    lda(0x120a)
    imm(0xc9,OFFSET+SIZE)
    c.branch(0xb0,'ordinary_done761')
    lda(0x1234)
    imm(0xc9,OFFSET+1)
    c.branch(0x90,'ordinary_done761')
    call(c,'burn761')
    c.label('ordinary_done761')
    lda(0x1234)
    c.emit(0x60)
    hook(labels['data_size_ok'],'ad3412','ordinary_write761',0x20)
    c.label('burn761')
    for a in (STATE,SERIAL,SERIAL+2,CURSOR,SUM1,SUM2):
        zero(a)
    c.emit(0x60)

    # Consume the proof exactly once, before the first changed word is stored.
    c.label('bind761')
    lda(STATE)
    imm(0xc9,READY)
    require_equal()
    lda(0x1020)
    c.absolute(0xcd,BANK)
    require_equal()
    lda(BANK)
    require_equal()  # single-page experiment binds bank 0
    for i in (0,2):
        c.long(0xaf,0x400010+i)
        c.absolute(0xcd,SERIAL+i)
        require_equal()
    call(c,'burn761')
    imm(0xa2,24)  # original LDX at indexed command entry
    c.emit(0x60)
    # Compare the live page to the saved reference, including omitted words.
    # Recompute both independent sums of the final data, also detecting a
    # corrupted packet even if its bad literal was written to both copies.
    c.label('verify761')
    verify1,verify2=0x1ab6,0x1ab8
    zero(verify1)
    zero(verify2)
    imm(0xa2,0)
    c.label('verify_row761')
    if floor:
        c.jump('finish761')
    stop()
    c.label('verify_words761')
    for off in range(0,16,2):
        c.long(0xbf,MIRROR+off)
        c.long(0xdf,PAGE+off)  # bank 0, explicitly checked in bind761
        c.emit(0xf0,3)
        c.jump('bad_packet')
        c.emit(0x18)
        c.absolute(0x6d,verify1)
        sta(verify1)
        c.emit(0x18)
        c.absolute(0x6d,verify2)
        sta(verify2)
    c.emit(0x8a,0x18)
    imm(0x69,16)
    c.emit(0xaa)
    imm(0xe0,SIZE)
    c.branch(0xf0,'compare_sums761')
    imm(0x89,63)  # A holds the advanced X byte offset
    c.emit(0xf0,3)
    c.jump('verify_words761')
    c.jump('verify_row761')
    c.label('compare_sums761')
    for i,addr in ((0,verify1),(2,verify2)):
        c.long(0xaf,0x400014+i)
        c.absolute(0xcd,addr)
        require_equal()
    c.label('finish761')
    stop()
    imm(0xa9,SIZE)
    sta(0x120c)
    imm(0xa9,OFFSET+SIZE)
    sta(0x1084)
    imm(0xa2,4)
    call(c,'mark212')
    c.emit(0xb0,3)
    c.jump('bad_packet')
    c.jump('accepted')
    support=c.finish()

    start=CODE+len(support)
    raw,points=receiver(labels,start,True)
    patchable=bytearray(raw)
    def change(seq,replacement):
        assert len(seq)==len(replacement) and patchable.count(seq)==1
        i=patchable.index(seq)
        patchable[i:i+len(seq)]=replacement
    def instr(op,name):
        return bytes([op])+struct.pack('<H',c.labels[name]&65535)
    change(bytes.fromhex('a21800'),instr(0x20,'bind761'))
    for mailbox in (2,4):
        original=bytes([0xbf,mailbox,0,0x40,0x97,0x7a])
        # For the second word there is no trailing INY. Keep all original
        # pointer/index increments in place, replacing LDA only.
        helper=Code(start+len(patchable))
        helper.long(0xbf,0x400000+mailbox)
        helper.emit(0xda,0xbb)
        helper.long(0x9f,MIRROR)
        helper.emit(0xfa,0x60)
        pc=helper.base & 65535
        change(original,bytes([0x20,pc&255,pc>>8,0xea,0x97,0x7a]))
        patchable.extend(helper.finish())
    after=patchable.index(bytes.fromhex('9c881a9c8a1a'))
    patchable[after:after+3]=instr(0x4c,'verify761')
    # Here the single-page capture binds only bank 0; reject any other bank.
    assert len(support)+len(patchable)<MIRROR-CODE
    pos=body.index(bytes.fromhex('c90900d0034c'))+5
    assert body[pos:pos+3]==bytes([0x4c])+struct.pack('<H',labels['reuse635']&65535)
    patches=[(at,bytes([op])+struct.pack('<H',c.labels[target]&65535)) for at,op,target in hooks]
    patches.append((0x2000+pos,bytes([0x4c])+struct.pack('<H',start&65535)))
    return support+patchable,patches,{**c.labels,'next_index760':points['next_index760']}


def run(a):
    a.frames=53
    assert sha(a.client/'body.bin') == RECEIVER
    labels=json.loads((a.client/'labels.json').read_text())
    code,hooks,points=build((a.client/'body.bin').read_bytes(),labels,a.floor)
    report={}
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
        compact = encode(old, new, int.from_bytes(seal[4:8],'little'), True)
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
        replacements='\n'.join(f" emu.write({at+i},{v},emu.memType.snesWorkRam)"
                               for at,h in hooks for i,v in enumerate(h))
        install=f"""if pw(8)==955 and pb(0)==1 then
 local blob=file('handler.bin')
 for i=1,#blob do emu.write({CODE&65535}+i-1,blob:byte(i),emu.memType.snesWorkRam) end
 for a={STATE},{SERIAL+3} do emu.write(a,0,emu.memType.snesWorkRam) end
 {replacements}
 end"""
        s=once(s,' if pb(0)==7 then tile=tilePayload',install+'\n if pb(0)==7 then tile=tilePayload')
        watches=['local log761=assert(io.open(ROOT..\'/idle761.csv\',\'w\'))',
                 "log761:write('event,clock,cursor,state,serial\\n')",
                 f"""local function watch761(name)
 log761:write(string.format('%s,%d,%d,%d,%d\\n',name,emu.getState().masterClock,word({CURSOR}),word({STATE}),word({SERIAL})));log761:flush()
 end"""]
        for name in ('capture_word761','read_chunk761','idle_complete761','bind761','next_index760',
                     'verify761','finish761','burn761','clear761','published761','idle_yield761'):
            watches.append(f"checkedMem527(function() watch761('{name}') end,emu.callbackType.exec,{points[name]})")
        s=once(s,'local function loaded()','\n'.join(watches)+'\nlocal function loaded()')
        s=once(s,'(pb(0)==2 or pb(0)==4) then','(pb(0)==2 or pb(0)==4 or pb(0)==9) then')
        s=once(s,'  lastStatus=ack[1];',f"""  if pw(8)==957 and pb(0)==9 and pb(1)==2 then
  assert(word({STATE})==0 and word({SERIAL})==0 and word({SERIAL+2})==0);watch761('ACK761')
 end
  lastStatus=ack[1];""")
        if a.fault:
            s=once(s,"local MODE='normal'","local MODE='fault761'")
            s=once(s,'local FAULT=905','local FAULT=957')
            first=next(i for i in range(0,SIZE,4) if old[i:i+4]!=new[i:i+4])
            last=next(i for i in reversed(range(0,SIZE,4)) if old[i:i+4]==new[i:i+4])
            if a.fault=='partial':
                s=once(s,' if a==0x6001 then',f""" if a==0x6001 then
 if packet and pw(8)==957 and pb(0)==9 and pb(1)==2 and word(0x1a80)=={first+4} then
  assert(word({STATE})==0 and word({SERIAL})==0);watch761('partial_STOP');return 128 end""")
            else:
                loc=(PAGE if a.fault=='retained' else MIRROR)-0x7e0000+last
                s=once(s,' if pb(0)==7 then tile=tilePayload',f""" if pw(8)==957 and pb(0)==9 and pb(1)==2 then
 assert(word({STATE})==2);watch761('flip_after_proof')
 emu.write({loc},rd({loc})~1,emu.memType.snesWorkRam) end
 if pb(0)==7 then tile=tilePayload""")
        return s

    def measure(before,after):
        first=next(int(r['index']) for r in after if r['g']=='955')
        assert [r for r in before if int(r['index'])<first]==[r for r in after if int(r['index'])<first]
        return dict(prefix_through=954)
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
            report.update(fault=a.fault,commits=52,status=result['last_status'],RGB956=sha(a.out/'retained.rgb'))
        else:
            assert not a.fault
            report['commits']=53
    with (a.out/'idle761.csv').open() as f:
        events=list(csv.DictReader(f))
    def at(name):
        return [int(r['clock']) for r in events if r['event']==name]
    def one(name):
        clock,=at(name)
        return clock
    assert len(at('capture_word761'))==768 and len(at('read_chunk761'))==48
    complete=one('idle_complete761')
    assert complete<one('bind761')<min(t for t in at('burn761') if t>one('bind761'))<one('ACK761')
    assert len(at('next_index760'))==(2 if a.fault=='partial' else 34)
    assert len(at('idle_yield761'))==48
    report.update(source_words=768,checked_rows=24,published_clock=one('published761'),
                  ready_clock=complete,bind_clock=one('bind761'),reply_clock=one('ACK761'))
    if a.fault:
        assert at('clear761') and (at('partial_STOP') if a.fault=='partial' else complete<one('flip_after_proof'))
    else:
        report.update(verify_clock=one('verify761'),finish_clock=one('finish761'),
                      verify_and_ACK_clocks=one('ACK761')-one('verify761'))
    (a.out/'cost761.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','mesen','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--fault',choices=('retained','mirror','partial'))
    parser.add_argument('--floor',action='store_true',help='diagnostic only: skip final WRAM checks')
    a=parser.parse_args()
    if a.floor and a.fault:
        parser.error('fault rejection requires the checked handler')
    run(a)
