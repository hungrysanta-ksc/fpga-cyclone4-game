"""Replay an idle 65816 DMA continuation against the original ROM calendar."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_window924
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_banks933 import ORIGINAL, QueuedPages
from nes_oam934 import arm, beam_monitor
from nes_raw506 import sha
from nes_return920 import ORIGIN, client


def output(variant='chain'):
    return ORIGINAL.parent/'nes-chain935'/variant


def fit_arm():
    return ORIGINAL.parent/'nes-chain935'/'arm-final'


def prepare_arm():
    link = fit_arm()/'link'
    assert sha(arm('window')/'link/src/obj-nes-100/firmware.stm')=='0f848e2ccfd558eb84f022d4c613f3c1c28b3fbbb6e5b6c066b131967dd920f0'
    shutil.copytree(arm('window')/'link',link)
    path = link/'src/nes_menu_diagnostic.c'
    source = path.read_text()
    start = source.index(' if(!strcmp(name,"NES START 925.nh1"))')
    end = source.index('\n}',start)
    # Menu-only. Keep the six names exact, including the case and suffix.
    # Compare the version once and store each mode just once.
    replacement = r''' static const char modes[]="MMC3\0START\0BOOT\0EARLY\0LATE\0CONTROL";
 static const unsigned char geometry_delta[]={0,1,2,26,27,28};
 if(strncmp(name,"NES ",4))return 0;
 name+=4;
 for(unsigned i=0,off=0;i<sizeof geometry_delta;i++){
  const char *a=name,*b=modes+off;
  while(*b && *a==*b){a++;b++;}
  if(!*b && !strcmp(a," 925.nh1"))return 384+geometry_delta[i];
  while(*b)b++;
  off=(unsigned)(b-modes)+1;
 }
 return 0;'''
    source = source[:start]+replacement+source[end:]
    # Packed append propagates a failed cursor. Successful appends here
    # always add a nonempty literal and leave a bounded NUL-terminated line.
    assert source.count('if(n>0&&(size_t)n<4096){')==2
    source=source.replace('if(n>0&&(size_t)n<4096){','{')
    source=source.replace('static unsigned marker_geometry(', 'static __attribute__((noipa)) unsigned marker_geometry(')
    path.write_text(source,newline='\n')


def prepare(variant):
    gated=variant=='gated'
    bounded=variant=='bounded'
    fused=variant in ('fused','gated','bounded')
    destination=output(variant)
    if fused:
        variant='burst'
    base = client('first')
    assert sha(base/'body.bin')=='945ab35516f5b3526c30758ebf5da8df46e19cb188d98f946217a68c52cce4b9'
    labels = json.loads((base/'labels.json').read_bytes())
    body = bytearray((base/'body.bin').read_bytes())
    head = body.index(bytes.fromhex('ae5212ec5012'), labels['prefix523']-ORIGIN)
    site = labels['dma_retired680']-ORIGIN
    assert body[site:site+6] == bytes.fromhex('68c90050d009')
    c = Code(ORIGIN+len(body))
    c.labels.update(labels)
    c.label('continue935')
    # A map still publishes its progress event. For tiles the last-byte
    # service checks STOP before trying another already admitted range.
    c.emit(0x68,0xc9,0,0x50)
    c.branch(0xd0,'tile935')
    c.absolute(0x4c,(ORIGIN+site+6)&65535)
    c.label('tile935')
    c.absolute(0x20,labels['service']&65535)
    c.branch(0xf0,'running935')
    c.jump('stop523')
    c.label('running935')
    if gated:
        # Small initial admissions retain ordinary queue/pad arbitration.
        c.emit(0xc0,64,0)
        c.branch(0x90,'early_exit935')
    if variant!='burst':
        c.emit(0xe2,0x20)
        c.absolute(0xad,0x6000)
        c.emit(0x4a)
        c.branch(0x90,'nohead935')
        c.jump('skip8_523')
        c.label('nohead935')
        c.emit(0xc2,0x20)
    if variant=='chain':
        c.absolute(0x4c,(ORIGIN+head)&65535)
    else:
        # The previous synchronous VRAM write left DMAP/BBAD, source bank
        # and VMAIN programmed. No callback here can change those registers.
        # Check the source class once, then limit the length before each DMA.
        c.absolute(0xae,0x1252)
        c.absolute(0xec,0x1250)
        if variant=='burst':
            c.branch(0xd0,'scan935')
            c.label('early_exit935')
            if bounded:
                c.emit(0x38,0x60)
            else:
                c.jump('skip523')
        else:
            c.branch(0xf0,'done935')
        c.label('scan935')
        if bounded:
            # Bound the time before the next bus priority check. A long
            # queue returns immediately to the normal arbitration loop.
            c.emit(0xa0,4,0)
        c.label('class935')
        c.long(0xbf,0x7e4000)
        c.emit(0x29,0,0x70,0xc9,0,0x40)
        c.branch(0xd0,'early_exit935' if variant=='burst' else 'done935')
        c.emit(0x8a,0x18,0x69,8,0,0xaa)
        c.absolute(0xec,0x1250)
        if bounded:
            c.branch(0xb0,'scanned935')
            c.emit(0x88);c.branch(0xd0,'class935');c.branch(0x80,'early_exit935')
            c.label('scanned935')
        else:
            c.branch(0x90,'class935')
        c.absolute(0xae,0x1252)
        c.long(0xbf,0x7e4004)
        c.emit(0xc9,0x81,1)
        c.branch(0xb0,'early_exit935' if variant=='burst' else 'done935')
        c.emit(0xa8,0xe2,0x20)
        # Use the same latch handshake and lower/upper line cutoffs.
        if variant=='burst':
            c.label('next935')
            call(c,'beam935')
            c.branch(0x90,'beamvalid935')
            c.jump('skip8_523')
            c.label('beamvalid935')
            c.branch(0x80,'setup935')
            c.label('beam935')
        c.label('latch935')
        fail='invalid935' if variant=='burst' else 'head935'
        c.absolute(0xad,0x4212);c.branch(0x10,fail)
        c.absolute(0xad,0x213f);c.absolute(0xad,0x213f)
        c.emit(0x89,0x40);c.branch(0xd0,fail)
        c.absolute(0xad,0x2137);c.absolute(0xad,0x213f)
        c.emit(0x89,0x40);c.branch(0xf0,fail)
        c.absolute(0xad,0x213d);c.emit(0xeb);c.absolute(0xad,0x213d)
        c.emit(0x29,1);c.branch(0xd0,fail)
        c.emit(0xeb,0xc9,225);c.branch(0x90,fail)
        c.label('limit935')
        c.emit(0xc9,253);c.branch(0xb0,fail)
        if variant=='burst':
            c.emit(0x18,0x60)
            c.label('invalid935')
            c.emit(0x38,0x60)
            c.label('setup935')
        c.absolute(0x8d,0x103e)
        c.emit(0xc2,0x20)
        c.long(0xbf,0x7e4000);c.absolute(0x8d,0x4302)
        c.emit(0x98);c.absolute(0x8d,0x4305)
        c.long(0xbf,0x7e4002);c.emit(0x4a);c.absolute(0x8d,0x2116)
        c.emit(0xe2,0x20);c.absolute(0xad,0x4212);c.branch(0x10,'head935')
        if variant=='direct':
            c.jump('priority524')
        else:
            # Only the head is issued and only its full length. The DMA
            # instruction returns after the last write. No interior list
            # move, partial range bookkeeping or map progress is due.
            c.absolute(0xad,0x6001);c.branch(0x30,'cancel935')
            c.absolute(0xad,0x6000);c.emit(0x4a);c.branch(0xb0,'head935')
            c.label('grant935')
            c.store(0x420b,1)
            c.emit(0xc2,0x20,0x8a,0x18,0x69,8,0)
            if bounded:
                c.emit(0xaa);c.absolute(0x8e,0x1252)
                c.label('verify935')
                c.absolute(0xec,0x1250);c.branch(0xd0,'length935')
                c.absolute(0x9c,0x1250);c.absolute(0x9c,0x1252);c.branch(0x80,'done935')
            else:
                c.absolute(0xcd,0x1250);c.branch(0xd0,'more935')
                c.absolute(0x9c,0x1250);c.emit(0xa9,0,0)
                c.label('more935')
                c.absolute(0x8d,0x1252)
                c.label('verify935')
                if not fused:
                    c.absolute(0x20,labels['service']&65535)
                    c.branch(0xd0,'stopped935')
                c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xf0,'done935')
            c.label('length935')
            c.long(0xbf,0x7e4004);c.emit(0xc9,0x81,1);c.branch(0xb0,'done935')
            c.emit(0xa8,0xe2,0x20)
            c.jump('next935')
            c.label('cancel935')
            assert body[labels['priority524']-ORIGIN+5:labels['priority524']-ORIGIN+10]==bytes.fromhex('a9018d3612')
            c.absolute(0x4c,(labels['priority524']+5)&65535)
            if not fused:
                c.label('stopped935');c.jump('stop523')
        c.label('done935')
        if bounded:
            c.emit(0x38,0x60)
        else:
            c.jump('skip523')
    c.label('head935')
    c.jump('skip8_523')
    target = c.labels['continue935']&65535
    body[site:site+3] = bytes((0x4c,))+target.to_bytes(2,'little')
    if variant=='burst':
        start=labels['selected526']-ORIGIN
        end=body.index(bytes.fromhex('8d3e10'),start)
        hook=Code(ORIGIN+start);hook.labels.update(c.labels)
        hook.emit(0xe2,0x20);call(hook,'beam935');hook.branch(0xb0,'defer_beam')
        hook.absolute(0x4c,(ORIGIN+end)&65535)
        body[start:end]=hook.finish().ljust(end-start,b'\xea')
        # Eight independent word comparisons in the idle history checker.
        # Preserve both indices on match and mismatch, including the original
        # cursor advancement and the 0x200 -> 0x270 discontinuity.
        at=labels['compare635']-ORIGIN+3
        old=body[at:at+80]
        for index in range(8):
            assert old[10*index:10*index+9]==bytes((0xbf,index*2,0x60,0x7f,0xdf,index*2,0xe0,0x7f,0xd0))
        loop=Code(ORIGIN+at);loop.labels.update(labels)
        loop.emit(0xda,0x5a,0xa0,8,0)
        loop.label('word935')
        loop.long(0xbf,0x7f6000);loop.long(0xdf,0x7fe000)
        loop.branch(0xd0,'unequal935')
        loop.emit(0xe8,0xe8,0x88);loop.branch(0xd0,'word935')
        loop.emit(0x7a,0xfa);loop.absolute(0x4c,(ORIGIN+at+80)&65535)
        loop.label('unequal935');loop.emit(0x7a,0xfa);loop.jump('unequal635')
        body[at:at+80]=loop.finish().ljust(80,b'\xea')
    body.extend(c.finish())
    build(base,destination,bytes(body),c.labels)


def replay(temp, mode, phase, cache, variant, *, work_arm=None, tag=None):
    base_monitor=beam_monitor(nes_window924.trace)
    def monitor(source,scene):
        lua=base_monitor(source,scene)
        labels=json.loads((output(variant)/'labels.json').read_bytes())
        if 'grant935' in labels:
            verify=labels['verify935'] if 'verify935' in labels else labels['more935']+3
            for old,new in [('grant524',labels['grant935']),('retired526',verify)]:
                end=f'end),emu.callbackType.exec,{labels[old]})'
                last=lua.index(end)+len(end)
                start=lua.rindex('checkedMem527(verify526(function()',0,last)
                callback=lua[start:last].replace(end,f'end),emu.callbackType.exec,{new})')
                lua=lua[:last]+'\n'+callback+lua[last:]
        if 'limit935' in labels:
            site=labels.get('grant935',labels['grant524'])
            hook=f"""checkedMem527(function() capture934('limit935') end,emu.callbackType.exec,{labels['limit935']})
checkedMem527(function() capture934('grant935') end,emu.callbackType.exec,{site})
"""
            lua=lua.replace('local function loaded()',hook+'local function loaded()',1)
        return lua
    target = work_arm or (fit_arm() if mode=='final' else ORIGINAL if mode=='base' else arm(mode))
    with patch.object(nes_window924,'client',lambda _:output(variant)), patch.object(nes_window924,'trace',monitor), patch.object(nes_window924,'LeadingRecord',QueuedPages):
        nes_window924.replay(temp,'objheader',phase,cache=='cold',arm=target,
                             edition=925,tag=tag or '935'+('' if variant=='chain' else variant)+mode,trace_last=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','arm','replay','proof','guards'))
    p.add_argument('temp',type=Path)
    p.add_argument('mode',nargs='?',default='window')
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    p.add_argument('--variant',choices=('chain','direct','burst','fused','gated','bounded'),default='bounded')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.variant)
    elif a.action=='arm':
        prepare_arm()
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',
            fit_arm(),925,short_header=True)
    elif a.action=='guards':
        import nes_obj923
        import nes_return920
        tag='935'+a.variant+'final'
        with patch.object(nes_obj923,'client',lambda _:output(a.variant)), patch.object(nes_return920,'client',lambda _:output(a.variant)):
            nes_return920.guards(a.temp,'first',tag=tag,destination=output(a.variant)/'final-guards.json')
            nes_obj923.obj_stops(a.temp,'first',tag=tag,destination=output(a.variant)/'final-stops.json')
    else:
        replay(a.temp,a.mode,a.phase,a.cache,a.variant)
