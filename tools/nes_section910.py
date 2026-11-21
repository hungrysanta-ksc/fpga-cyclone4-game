"""Preassemble the immutable section-5 bytes without reserving an output sequence."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch as replace_monitor

from prepare_nes_trial907 import PROBES, WORK as BASE
from nes_raw506 import once, sha
import replay_nes_peer906 as peer

WORK = PROBES/'nes-section910'
FRAMED = PROBES/'nes-section910-framed'
DIRECT = PROBES/'nes-section910-direct'


def trace_tail(source,scene):
    source=base_monitor(source,scene)
    labels=json.loads((peer.CLIENT/'labels.json').read_bytes())
    dma=labels['literal_length227']
    body=(peer.CLIENT/'body.bin').read_bytes()
    assert body[dma-0x7e2000:dma-0x7e2000+7]==bytes.fromhex('e2 20 a9 01 8d 0b 42')
    points=dict(data_check=labels['data'],literal=labels['literal1814'],
                trigger=dma+4,after_trigger=dma+7,accepted=labels['accepted'],reply=labels['reply'])
    hooks=[f"checkedMem527(function() if packet and pb(0)==2 and pb(1)==5 and pw(12)==240 then sample516('s910_{name}') end end,emu.callbackType.exec,{pc})"
           for name,pc in points.items()]
    return once(source,'local function loaded()', '\n'.join(hooks)+'\nlocal function loaded()')


base_monitor=peer.monitor


def check_rows(work):
    from check_nes_tail735 import emit
    spans=[]
    for count in range(8):
        spans.append(emit(work/'link/src',21,count,2))
    spans.append(emit(work/'link/src',21,2,66,reject=True))
    output=(WORK/'proof/rows910-reference.json') if work==BASE else (work/'proof/rows910.json')
    output.parent.mkdir(exist_ok=True)
    result=dict(firmware=sha(work/'link/src/obj-nes-100/firmware.stm'),spans=spans)
    output.write_text(json.dumps(result)+'\n')


def prepare():
    assert sha(BASE/'link/src/obj-nes-100/firmware.stm')=='dba9d47853d5c470a85b7041019d396bd0abf70939c14ff7751ccf2e3cbcfe74'
    name='nes_native_sink165.c'
    source=(BASE/'link/src'/name).read_text()
    layout=source[source.index('  /* Read the enclosing object representation'):source.index('  /* One contiguous wire image')]
    copy=source[source.index('  uint8_t *joined='):source.index('  if(!packet(s,2,5,offset,joined,201))')]
    source=once(source,layout,'')
    source=once(source,copy,'')
    early=layout+'''  uint8_t *joined=(uint8_t *)p->bg_keys+6144;
  _Static_assert(sizeof p->bg_keys>=6144+441,"section-5 scratch bounds");
  /* The planner is done; the map service and bulk callbacks use no BG keys.
   * Do not allocate a sequence or reuse a queue credit during preparation. */
  if(p->patch_count){
   memcpy(joined,raw+packed-192,192);
   memcpy(joined+192,tables,243);
   memcpy(joined+435,p->patch.size,6);
  }
'''
    source=once(source,' bool same=same635(s,p);',early+' bool same=same635(s,p);')
    patch=WORK/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    (patch/name).write_text(source,newline='\n')
    # Fixed fields can be assembled with the payload. Sequence ownership
    # starts only after prior bulk service, inside packet_wire.
    source=once(source,'uint8_t *joined=(uint8_t *)p->bg_keys+6144;',
                'uint8_t *head=(uint8_t *)p->bg_keys+6144,*joined=head+16;')
    source=once(source,'6144+441','6144+16+441')
    source=once(source,'   memcpy(joined,raw+packed-192,192);','''   head[0]=2;head[1]=5;
   memcpy(head+4,&s->serial,4);put16(head+8,s->generation);
   put16(head+10,1121+packed-192);put16(head+12,201);put16(head+14,0);
   memcpy(joined,raw+packed-192,192);''')
    source=once(source,'packet(s,2,5,offset,joined,201)','packet(s,27,5,offset,head,201)')
    source=once(source,'uint8_t b[256],ack[12]={0};','uint8_t local[256],*b=local,ack[12]={0};')
    source=once(source,' b[0]=(uint8_t)op;', ''' if(op==27){
  /* Writable private section-5 scratch. No sequence was reserved early. */
  b=(uint8_t *)data;put16(b+2,s->sequence);
 }else{
 b[0]=(uint8_t)op;''')
    source=once(source,' s->state=NES_SINK165_BUSY; /* arm',' }\n s->state=NES_SINK165_BUSY; /* arm')
    patch=FRAMED/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    (patch/name).write_text(source,newline='\n')
    # The first 192 bytes are already contiguous for both representations.
    # Canonical CHR is immediately followed by mode. In compact scratch only
    # the first nine mode bytes have to be appended before OAM.
    source=(BASE/'link/src'/name).read_text()
    source=once(source,'   raw=out;', '''   memcpy(out+packed,p->patch.mode,9);
   raw=out;''')
    source=once(source,copy,'''  _Static_assert(__builtin_offsetof(struct nes_native_video165,patch.mode)==
                 __builtin_offsetof(struct nes_native_video165,patch.chr)+2048,"canonical CHR and mode");
  uint8_t *joined=(uint8_t *)p->bg_keys+6144;
''')
    source=once(source,'  if(!packet(s,2,5,offset,joined,201))return false;\n  if(!packet(s,2,5,offset+201,joined+201,240))return false;',
                '''  /* Access the entire enclosing object for the canonical CHR/mode span. */
  const uint8_t *first=p->patch_count<=2?raw+prefix:
      (const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.chr)+prefix;
  if(!packet(s,2,5,offset,first,201))return false;
  memcpy(joined,tables+9,234);
  memcpy(joined+234,p->patch.size,6);
  if(!packet(s,2,5,offset+201,joined,240))return false;''')
    patch=DIRECT/'patch'
    patch.mkdir(parents=True,exist_ok=True)
    (patch/name).write_text(source,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('patch')
    sub.add_parser('rows').add_argument('variant',choices=('ref','payload','framed','direct'))
    guards=sub.add_parser('guards')
    guards.add_argument('game',type=Path)
    gv=guards.add_mutually_exclusive_group()
    gv.add_argument('--framed',action='store_true')
    gv.add_argument('--direct',action='store_true')
    replay=sub.add_parser('replay')
    replay.add_argument('temp',type=Path)
    replay.add_argument('phase',type=int,choices=(1,2))
    replay.add_argument('--cold',action='store_true')
    rv=replay.add_mutually_exclusive_group()
    rv.add_argument('--framed',action='store_true')
    rv.add_argument('--direct',action='store_true')
    rv.add_argument('--reference',action='store_true')
    args=parser.parse_args()
    if args.action=='patch':
        prepare()
    elif args.action=='rows':
        check_rows(dict(ref=BASE,payload=WORK,framed=FRAMED,direct=DIRECT)[args.variant])
    elif args.action=='guards':
        from check_nes_supply905_arm import run
        run(args.game,DIRECT if args.direct else FRAMED if args.framed else WORK,907)
    else:
        work,tag=(FRAMED,'910b') if args.framed else (WORK,'910')
        if args.direct:
            work,tag=DIRECT,'910c'
        if args.reference:
            work,tag=BASE,'910ref'
        with replace_monitor.object(peer,'monitor',trace_tail):
            peer.compare(args.temp,args.phase,args.cold,True,edition=907,work_arm=work,run_id=tag)
