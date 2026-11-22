"""Defer the first ordinary OAM span following a checked, large OBJ descriptor."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_window924
from nes_banks933 import DeeperHead, QueuedPages, ORIGINAL, once


def arm(mode):
    return ORIGINAL.parent / ('nes-oam934-' + mode)


def beam_monitor(original):
    from nes_return920 import client
    consumer=client('first')
    labels=json.loads((consumer/'labels.json').read_bytes())
    body=(consumer/'body.bin').read_bytes()
    origin=0x7e2000
    start=labels['selected526']-origin
    cutoff=origin+body.index(bytes.fromhex('c9 fd b0'),start,labels['defer_beam']-origin)
    def monitor(source,scene):
        source=original(source,scene)
        hook="""local beam934=assert(io.open(ROOT..'/beam934.csv','w'))
local function capture934(event)
 if packet or word(0x1226)~=912 then return end
 local st=emu.getState()
 local line=st['ppu.scanline']
 if line<238 or st['cpu.y']~=32 then return end
 local x=st['cpu.x']
 beam934:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d\\n',event,st.masterClock,st.frameCount,
     line,word(0x4002+x),word(0x4004+x),rd(0x103e),st['cpu.a']%256))
 beam934:flush()
end
"""
        for name,addr in [('limit',cutoff),('defer',labels['defer_beam']),('grant',labels['grant524'])]:
            hook+=f"checkedMem527(function() capture934('{name}') end,emu.callbackType.exec,{addr})\n"
        anchor='local function loaded()'
        return once(source,anchor,hook+anchor)
    return monitor


def prepare(mode):
    link = arm(mode) / 'link'
    shutil.copytree(ORIGINAL / 'link', link)
    path = link / 'src/nes_native_sink165.c'
    if mode in ('tail','gap','burst','hot','window','overlap','lead'):
        # Service the existing two physical banks through the first short
        # successor of a large descriptor. A valid END also terminates this
        # wait, and the normal poll limit and guards remain active.
        plan = link/'src/nes_plan_service200.c'
        source = once(plan.read_text(),'  if(!poll(p,&flags,NES_PLAN215_FINISH))return false;',
                      '''  unsigned large=p->bulk[3];
  if(!poll(p,&flags,NES_PLAN215_FINISH))return false;''')
        source = once(source,'   if((mode==NES_MAP553 || mode==NES_ORDINARY553)',
                      '''   if(mode==NES_HDMA554 && large && p->bulk_pending &&
      p->bulk[1] && p->bulk[2]==32 && !p->bulk[3])return complete485(p);
   if((mode==NES_MAP553 || mode==NES_ORDINARY553)''')
        if mode in ('burst','hot','window','overlap','lead'):
            # through() already performed the IRQ/STOP service on this new
            # receipt. Requery immediately once, never on a stale descriptor.
            source = once(source,'   if((mode==NES_MAP553 || mode==NES_ORDINARY553)',
                          '''   if(mode==NES_HDMA554 && p->bulk_pending){
    if(!complete485(p))return false;
    continue;
   }
   if((mode==NES_MAP553 || mode==NES_ORDINARY553)''')
        if mode in ('window','overlap','lead'):
            # Earlier DMA may already have set the progress bit. Keep the
            # head free for the remaining verified ranges after this receipt.
            source=once(source,'p->bulk[2]==32 && !p->bulk[3])return complete485(p);',
                        '''p->bulk[2]==32 && !p->bulk[3]){
    uint8_t ack[12];
    if(!complete485(p))return false;
    for(unsigned i=0;i<12;i++)
     if(!nes_window184_drain(p->window,ack))return fail(p,5);
    return true;
   }''')
        if mode=='overlap':
            # E8 is an observation only. The new descriptor path still calls
            # complete485 before submission; an empty END does so as well.
            source=once(source,'if(p->bank_history==2 && !complete485(p))',
                        'if(p->bank_history==2 && !(p->tile_service && phase==NES_PLAN215_FINISH) && !complete485(p))')
            source=once(source,'    if(phase==NES_PLAN215_FINISH&&!complete485(p))',
                        '''    if(p->tile_service && phase==NES_PLAN215_FINISH && p->bulk_pending){
     *flags=0;return true;
    }
    if(phase==NES_PLAN215_FINISH&&!complete485(p))''')
            source=once(source,'''if(mode==NES_HDMA554 && p->bulk_pending){
    if(!complete485(p))return false;
    continue;
   }''','if(mode==NES_HDMA554 && p->bulk_pending)continue;')
        if mode=='lead':
            # Arm the short receipt cadence from the first encoded E9,
            # before the initial BG and short OBJ transactions. This flag
            # only selects polling; it never confers ownership or a receipt.
            source=once(source,' b[0]=0xe9;', ''' if(!p->sent)p->tile_service=n>=27 && b[4]==0x82 && b[7]==0x81 &&
    b[14]!=255 && b[15]==0x81 && b[22]==255 && b[23]==0x81 && b[30]==255;
 b[0]=0xe9;''')
            source=once(source,'p->sent=0;p->finished=false;', 'p->tile_service=false;p->sent=0;p->finished=false;')
        plan.write_text(once(source,'}else if(mode!=NES_FINAL553){',
                             '}else if(mode!=NES_FINAL553 && mode!=NES_HDMA554){'),newline='\n')
        wait = ' || !wait_map880(s->plan->window,12)' if mode=='gap' else ''
        anchor = ' /* Synchronous immutable source:'
        source = once(path.read_text(),anchor,''' if(fixed && s->plan->bulk[2]==32 && !s->plan->bulk[3] &&
    (!nes_plan200_progress(s->plan,NES_HDMA554)'''+wait+'''))return false;
'''+anchor)
        if mode in ('hot','window','overlap','lead'):
            header=link/'src/nes_plan_service200.h'
            header.write_text(once(header.read_text(),'uint8_t obj_start;',
                                   'uint8_t obj_start;bool tile_service;'),newline='\n')
            source=once(source,'''if(fixed && s->plan->bulk[2]==32 && !s->plan->bulk[3] &&
    (!nes_plan200_progress(s->plan,NES_HDMA554)))return false;''','''if(fixed && s->plan->bulk[2]==32 && !s->plan->bulk[3]){
  s->plan->tile_service=true;
  bool ok=nes_plan200_progress(s->plan,NES_HDMA554);
  s->plan->tile_service=false;
  if(!ok)return false;
 }''')
            runtime=link/'src/nes_native_runtime165.c'
            runtime.write_text(once(runtime.read_text(),'84u*96u : 84u*128u',
                                    '84u*96u : s->plan.tile_service ? 0 : 84u*128u'),newline='\n')
            if mode=='lead':
                source=once(source,'if(fixed && s->plan->bulk[2]==32 && !s->plan->bulk[3]){\n  s->plan->tile_service=true;',
                            'if(fixed && s->plan->tile_service && s->plan->bulk[2]==32 && !s->plan->bulk[3]){')
        path.write_text(source,newline='\n')
        return
    if mode in ('stream','quiet','credit','reserve','head','park'):
        drain = 'section==4&&!at'
        source = path.read_text()
        if mode in ('credit','reserve'):
            # The 232-byte palette span otherwise bypasses checked bulk
            # arbitration while a short OBJ descriptor is outstanding.
            source = once(source,'(at>=128 && age<3)',
                          '(at>=128 && age<3 && (at!=128 || s->plan->bulk[2]!=64))')
            if mode=='reserve':
                drain = '(('+drain+') || (section==3 && at==128))'
        source = once(source, 'section==2?NES_MAP553:NES_ORDINARY553',
                      'section==2?NES_MAP553:'+drain+'?NES_HDMA554:NES_ORDINARY553')
        if mode=='quiet':
            source = once(source,'if(op==8 && s->plan && s->plan->window &&',
                          'if((op==8 || (section==4 && !at)) && s->plan && s->plan->window &&')
        if mode in ('head','park'):
            # On the fixed palette path the first OBJ has already been
            # validated. Service its successor before starting the large span.
            anchor = ' /* Synchronous immutable source:'
            policy = 'NES_HDMA554' if mode=='head' else 'NES_FINAL553'
            source = once(source,anchor,''' if(fixed && s->plan->bulk[2]==32 && !s->plan->bulk[3] &&
    !nes_plan200_progress(s->plan,'''+policy+'''))return false;
'''+anchor)
        path.write_text(source,newline='\n')
        return
    # The original progress call can submit the large OBJ before the ordinary
    # packet has a sequence number. Wait only on checked outstanding work.
    anchor = ' /* Let an already submitted OBJ return before issuing the OAM fill.'
    condition = ''' if(section==4 && !at && op==2 && s->plan &&
    s->plan->bulk_pending && s->plan->bulk[1] && s->plan->bulk[3]){
'''
    service = {
        'return': '  if(!wait_map880(s->plan->window,1))return fail(s,5);',
        'follow': '''  if(!nes_plan200_progress(s->plan,NES_ORDINARY553) ||
     !wait_map880(s->plan->window,12))return fail(s,5);''',
        'end': '  if(!nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);',
    }[mode]
    path.write_text(once(path.read_text(), anchor, condition + service + '\n }\n' + anchor), newline='\n')


def run(args):
    if args.action=='prepare':
        prepare(args.mode)
        return
    storage = {'depth': DeeperHead, 'fair': QueuedPages}[args.storage]
    tag = '934' + args.mode + args.storage
    if args.action in ('replay','beam'):
        monitor=nes_window924.trace
        if args.action=='beam':
            monitor=beam_monitor(monitor)
            tag+='beam'
        with patch.object(nes_window924,'LeadingRecord',storage), patch.object(nes_window924,'trace',monitor):
            nes_window924.replay(args.temp,'objheader',args.phase,args.cache=='cold',
                                 arm=arm(args.mode),edition=925,tag=tag,trace_last=True)
    elif args.action=='proof':
        from check_nes_supply905_arm import run as prove
        prove(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',
              arm(args.mode),925,short_header=True)
    else:
        from nes_obj923 import obj_stops
        from nes_return920 import guards
        guards(args.temp,'first',tag=tag,destination=arm(args.mode)/'final-guards.json')
        obj_stops(args.temp,'first',tag=tag,destination=arm(args.mode)/'final-stops.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','beam','proof','guards'))
    parser.add_argument('mode',choices=('return','follow','end','stream','quiet','credit','reserve','head','park','tail','gap','burst','hot','window','overlap','lead'))
    parser.add_argument('temp',type=Path)
    parser.add_argument('storage',choices=('depth','fair'),default='fair',nargs='?')
    parser.add_argument('phase',type=int,choices=(1,2),nargs='?')
    parser.add_argument('cache',choices=('cold','warm'),nargs='?')
    run(parser.parse_args())
