# SPDX-License-Identifier: MIT
"""Execute candidate 65816 selections with frozen 740 packet arrival clocks."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from nes_raw506 import once, sha
from replay_nes_gap740 import schedule
from build_nes_trace_replay import Code


def replacements(client, variant):
    body=(client/'body.bin').read_bytes()
    assert sha(client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
    labels=json.loads((client/'labels.json').read_text())
    def addr(name):
        return (labels[name]&65535).to_bytes(2,'little')
    def jump(name):
        return b'\x4c'+addr(name)
    # X points to an independently accepted map, Y still holds the original
    # head tile length. Retain the original fallback on every other shape.
    out={}
    cave=0x2000+len(body)
    if variant in ('bg','obj','chainbg','chainobj','fastbg','fastobj'):
        site=labels['found_map680']&65535
        load=bytes.fromhex('bf04407e')
        assert body[site-0x2000:site-0x2000+4]==load
        limit=48 if variant.endswith('bg') else 288
        code=(load+bytes.fromhex('c90006d00dc0')+(limit+1).to_bytes(2,'little')+
              bytes.fromhex('b008ae5212e220')+jump('map_beam_ok526')+
              b'\x4c'+(site+4).to_bytes(2,'little'))
        assert len(code)==25 and code[22]==0x4c
        out[site]=b'\x4c'+cave.to_bytes(2,'little')
        out[cave]=code
        cave+=len(code)
    direct=variant in ('direct','fragment','edge','budget')
    if direct:
        site=(labels['budget685']&65535)-3
        assert body[site-8192:site-8192+3]==jump('late_map680')
        pad=(labels['map_beam_ok526']&65535)-13
        assert body[pad-8192:pad-8192+13]==bytes([0xea])*13
        out[site]=b'\x4c'+pad.to_bytes(2,'little')
        out[pad]=bytes.fromhex('c03100b003')+jump('map_beam_ok526')+jump('late_map680')
    if variant.startswith(('chain','fast')) or direct:
        # A completed synchronous DMA already called service. Let a ready queue
        # head take the next poll; otherwise re-enter the unmodified selector,
        # which re-latches the beam and checks both STOP and a new head.
        site=(labels['no_event680']&65535)+3
        assert body[site-0x2000:site-0x2000+3]==jump('retired_continue680')
        code=(bytes.fromhex('f003')+jump('stop523')+bytes.fromhex('e220ad00604a9003')+
              jump('skip8_523')+bytes.fromhex('c220')+jump('prefix523'))
        if direct:
            head=body.index(bytes.fromhex('ae5212ec5012'),(labels['prefix523']&65535)-8192)
            code=code[:-2]+(8192+head).to_bytes(2,'little')
        out[site]=b'\x4c'+cave.to_bytes(2,'little')
        out[cave]=code
        cave+=len(code)
    if variant.startswith('fast') or direct:
        # The idle poll (or previous DMA's retirement) has serviced STOP.
        # Keep its latch test and the live STOP/new-head tests at MDMAEN.
        site=labels['check523']&65535
        assert body[site-0x2000:site-0x2000+3]==b'\x20'+addr('service')
        out[site]=bytes.fromhex('ad3612')
        if variant in ('fastobj','fragment','edge','budget'):
            for label in ('prefix523','late_tile681'):
                start=(labels[label]&65535)-0x2000
                site=body.index(bytes.fromhex('c9a100'),start,start+80)
                out[site+0x2000]=bytes.fromhex('c92101')
    if variant in ('fragment','edge','budget'):
        # The old partial path hardcodes the map cap (1152). Advance by the
        # actual synchronous DMA length in Y for both map and OBJ fragments.
        start=(labels['dma_continue680']&65535)+9
        stop=labels['whole526']&65535
        assert body[start-8192:start-8192+4]==bytes.fromhex('bf00407e')
        code=bytes.fromhex('98187f00407e9f00407e98187f02407e9f02407e9849ffff387f04407e9f04407e')+jump('retired526')
        assert len(code)<=stop-start
        out[start]=code
        # Extend only an accepted OBJ by up to 64B on lines 253..257.
        # Both the ninth vertical bit and the low byte are checked. No map
        # or other tile enters this path and the normal STOP/head gate follows.
        base_site=labels['selected526']&65535
        def branch_site(pattern):
            return body.index(bytes.fromhex(pattern),base_site-8192,base_site-8192+90)+8192
        high=branch_site('d045ebc9e1')
        at=high-2
        assert body[at-8192:at-8192+8]==bytes.fromhex('2901d045ebc9e190')
        out[at]=b'\x4c'+cave.to_bytes(2,'little')
        c=Code(0x7e0000+cave)
        c.labels.update(labels)
        c.labels['ordinary741']=0x7e0000+branch_site('8d3e10')
        c.emit(0x29,1);c.branch(0xf0,'low741')
        c.emit(0xeb,0xc9,2);c.branch(0x90,'obj741');c.jump('defer_beam')
        c.label('low741');c.emit(0xeb,0xc9,225);c.branch(0xb0,'vblank741');c.jump('defer_beam')
        c.label('vblank741');c.emit(0xc9,253);c.branch(0xb0,'obj741');c.jump('ordinary741')
        c.label('obj741');c.long(0xbf,0x7e4001);c.emit(0x29,0x70,0xc9,0x40)
        c.branch(0xf0,'chunk741');c.jump('defer_beam')
        c.label('chunk741');c.emit(0xc0,65,0);c.branch(0x90,'ready741');c.emit(0xa0,64,0)
        c.label('ready741');c.jump('map_beam_ok526')
        out[cave]=c.finish()
        if variant=='edge':
            # One extra latch line for a complete map. Preserve the measured
            # grant and the last-PPU-write deadline as separate replay checks.
            site=(labels['budget685']&65535)+4
            assert body[site-8192]==249
            out[site]=bytes([250])
        if variant=='budget':
            # Extend the full-map path only for line 249 or the first 128
            # horizontal dots of line 250. Read both bytes of the same latch.
            cave+=len(out[cave])
            site=labels['budget685']&65535
            assert body[site-8192:site-8192+5]==bytes.fromhex('ad3e10c9f9')
            c=Code(0x7e0000+cave)
            c.labels.update(labels)
            c.labels['map_kind741']=labels['budget685']+7
            c.absolute(0xad,0x103e);c.emit(0xc9,250);c.branch(0x90,'long741');c.branch(0xd0,'cap741')
            c.absolute(0xad,0x213c);c.emit(0xeb);c.absolute(0xad,0x213c);c.emit(0x29,1)
            c.branch(0xd0,'cap741');c.emit(0xeb,0xc9,128);c.branch(0xb0,'cap741')
            c.label('long741');c.jump('map_kind741')
            c.label('cap741');c.jump('map_beam_ok526')
            out[site]=b'\x4c'+cave.to_bytes(2,'little')
            out[cave]=c.finish()
    return out


def run(a):
    base=a.trace.parent/f'nes-pair727-a{a.phase}'
    ref=a.trace
    a.trace=base
    seed='first' if a.calendar=='overlap' else a.calendar
    assert ref.name==f'nes-gap740-{seed}{a.phase}-trace'
    evidence=json.loads((Path(__file__).resolve().parents[1]/'analysis/gap740-verification.json').read_text())
    assert sha(ref/'arrivals.tsv')==evidence['phases'][str(a.phase)][seed]['pins']['arrivals.tsv']
    edits=replacements(a.client,a.variant)
    install='\n'.join(f' for i,v in ipairs({{{",".join(map(str,code))}}}) do emu.write({at}+i-1,v,emu.memType.snesWorkRam) end' for at,code in edits.items())
    real_run=replay.run
    def retimed(args, *, edit_script):
        def edit(s):
            s=edit_script(s)
            shutil.copyfile(ref/'arrivals.tsv',args.out/'arrivals.tsv')
            plan=schedule(base,a.phase,seed)
            advance=0
            if a.calendar=='overlap':
                # Use the measured cost of preparing D0 after E8 and returning
                # to status checking. E0 still starts at its original clock.
                trace=json.loads((base/'events.json').read_text())
                events=[e for e in trace if e['generation']==957 and e['event']=='SPI']
                e8=next(e for e in events if e['opcode']=='0xe8' and bytes.fromhex(e['reply'])[6:8]==bytes((1,1)) and int.from_bytes(bytes.fromhex(e['reply'])[14:18],'little')==120)
                receipt=plan['map_receipt'];service=plan['input_service']
                next_status=next(e for e in events if e['start']>=service['clock'])
                precheck=next(e for e in events if e['start']>=e8['clock'])
                assert precheck['opcode']=='0xe0' and next_status['opcode']=='0xe0'
                work=(e8['clock']-e8['start'] + precheck['start']-e8['clock'] +
                      service['clock']-receipt['clock'] + next_status['start']-service['clock'])
                assert plan['query_start']+work<=receipt['start']
                advance=round(service['clock']-receipt['clock'])
            pulse_shift=0
            if a.feedback:
                pulse_shift=int((a.feedback/'pulse741.txt').read_text().splitlines()[0])-plan['pulse']
            if advance or pulse_shift:
                old=(args.out/'arrivals.tsv').read_text().splitlines();new=[]
                previous=0
                for item in old:
                    t,h,b=item.split('\t');clock=int(t)
                    if h!='FINISH' and int.from_bytes(bytes.fromhex(h)[8:10],'little')==957 and bytes.fromhex(h)[:2] in (bytes((7,1)),bytes((9,4))) and clock>=plan['first']-plan['shift']:
                        clock-=advance
                    elif clock>=plan['scroll']-plan['tail_shift']:
                        clock+=pulse_shift
                    assert clock>=previous;previous=clock;new.append(f'{clock}\t{h}\t{b}')
                (args.out/'arrivals.tsv').write_text('\n'.join(new)+'\n',newline='\n')
            (args.out/'timing741.json').write_text(json.dumps(dict(advance=advance,pulse_shift=pulse_shift,
                feedback_sha=sha(a.feedback/'pulse741.txt') if a.feedback else None)))
            s=once(s,'local function loaded()',"""local patch741=false
local oam741=false
local pulses741=assert(io.open(ROOT..'/pulse741.txt','w'))
checkedMem527(function(_,v)
 if oam741 and v==0xa5 then pulses741:write(tostring(emu.getState().masterClock)..'\\n');pulses741:flush() end
end,emu.callbackType.write,0x601d)
local selectors741=assert(io.open(ROOT..'/select741.csv','w'))
selectors741:write('event,clock,frame,line,h,head,endp,src,bytes,nextsrc,nextbytes\\n')
local function select741(name)
 if not patch741 then return end
 local st=emu.getState();local line=st['ppu.scanline']
 if line<225 or line>261 then return end
 local head=word(0x1252);local finish=word(0x1250);local p=0x4000+head
 if finish<=head then return end
 selectors741:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',name,st.masterClock,st.frameCount,line,
  st['memoryManager.hClock'],head,finish,word(p),word(p+4),head+8<finish and word(p+8) or -1,head+8<finish and word(p+12) or -1))
end
local function loaded()""")
            if a.variant in ('fastobj','fragment','edge','budget'):
                s=once(s,'(i<tail or n<=160)','(i<tail or n<=(word(0x1226)==957 and 288 or 160))')
            if a.variant in ('fragment','edge','budget'):
                s=once(s,'n==word(0x4004+i) and n<=2048',
                       '(n==word(0x4004+i) or (word(0x1226)==957 and n==64 and word(0x4004+i)>64 and (src&0x7000)==0x4000)) and n<=2048')
                if a.variant=='edge':
                    s=once(s,'beam685.line<=248 and length<=1536','beam685.line<=(word(0x1226)==957 and 249 or 248) and length<=1536')
                elif a.variant=='budget':
                    s=once(s,'beam685.line<=248 and length<=1536',
                           '(beam685.line<=248 or (word(0x1226)==957 and (beam685.line==249 or (beam685.line==250 and beam685.h<512)))) and length<=1536')
            hook=''
            labels=json.loads((a.client/'labels.json').read_text())
            for name in ('selected526','found_map680','grant524','retired526','defer_beam'):
                hook+=f"checkedMem527(function()select741('{name}')end,emu.callbackType.exec,{labels[name]})\n"
            if a.lag_nops:
                assert a.variant=='budget' and 0<a.lag_nops<=16
                site=labels['selected526']&65535
                assert (a.client/'body.bin').read_bytes()[site-8192:site-8192+5]==bytes.fromhex('e220ad1242')
                trampoline=bytes([0xea])*a.lag_nops+bytes.fromhex('ad12424c')+(site+5).to_bytes(2,'little')
                hook+=f"""local lag741=false
checkedMem527(function()
 if patch741 and not lag741 and word(0x4004+word(0x1252))==1536 then
  lag741=true
  for i,v in ipairs({{{','.join(map(str,trampoline))}}}) do emu.write(0x3900+i-1,v,emu.memType.snesWorkRam) end
  for i,v in ipairs({{0x4c,0,0x39}}) do emu.write({site}+1+i,v,emu.memType.snesWorkRam) end
 end
end,emu.callbackType.exec,{labels['selected526']})
"""
            s=once(s,'local function loaded()',hook+'local function loaded()')
            s=once(s,' if pw(8)==957 then active739=true end',' if pw(8)==957 and not patch741 then\n'+install+'\n patch741=true end\n if pw(8)==957 and pb(0)==9 then oam741=true end\n if pw(8)==957 then active739=true end')
            if a.inject in ('before_bg','during_obj'):
                assert a.mode=='stop'
                s=once(s,"if pw(8)==957 and pb(0)==9 then stop739=true end","")
                if a.inject=='before_bg':
                    match="regs[0x4305]==48 and regs[0x4302]==0x40 and regs[0x4303]==8"
                    event=f"emu.callbackType.exec,{labels['priority524']}"
                else:
                    match="regs[0x4305]==64 and regs[0x4303]==0x4a"
                    event="emu.callbackType.write,0x2118"
                watch=f"""checkedMem527(function()
 if oam741 and not packet and not stop739 and {match} then
  stop739=true;local f=assert(io.open(ROOT..'/fault741.txt','w'))
  f:write(tostring(emu.getState().masterClock));f:close()
 end
end,{event})
"""
                s=once(s,'local function loaded()',watch+'local function loaded()')
            if a.inject=='head':
                assert a.mode=='trace'
                hook=f"""local inject741=false
checkedMem527(function()
 if oam741 and not inject741 and not packet and regs[0x4305]==48 and regs[0x4303]==8 then
  assert(b522~='FINISH' and unhex(b522):byte(2)==5)
  local now=emu.getState().masterClock
  local f=assert(io.open(ROOT..'/fault741.txt','w'));f:write(now,' ',target522);f:close()
  assert(now<target522)
  target522=now;inject741=true;rpc()
 end
end,emu.callbackType.exec,{labels['ready524']})
"""
                s=once(s,'local finished522=false',hook+'local finished522=false')
            return s
        def compare(old,new):
            assert [r for r in old if int(r['g'])<957]==[r for r in new if int(r['g'])<957]
            for event in ('load','ack','reveal'):
                def ids(rows):
                    return [(r['g'],r['index'],r['op'],r['section'],r['value']) for r in rows if r['event']==event]
                assert ids(old)==ids(new),event
            if a.variant=='control' and a.calendar!='overlap' and not a.feedback:assert sha(ref/'window.csv')==sha(args.out/'window.csv')
            return dict(prefix_events=sum(int(r['g'])<957 for r in old))
        return real_run(args,edit_script=edit,compare_trace=compare)
    with patch.object(replay,'run',retimed):
        owner.run(a)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','out','client','mesen'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phase',type=int,choices=(1,2),required=True)
    p.add_argument('--calendar',choices=('first','issued','checked','overlap'),default='first')
    p.add_argument('--variant',choices=('control','bg','obj','chain','chainbg','chainobj','fastbg','fastobj','direct','fragment','edge','budget'),required=True)
    p.add_argument('--lag-nops',type=int,default=0)
    p.add_argument('--feedback',type=Path)
    p.add_argument('--inject',choices=('none','before_bg','during_obj','head'),default='none')
    p.add_argument('--mode',choices=('trace','stop','stale'),default='trace')
    run(p.parse_args())
