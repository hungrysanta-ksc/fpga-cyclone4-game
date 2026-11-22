"""Receive the terminal input block while SEAL still owns the display."""
import argparse
import shutil
from unittest.mock import patch
from pathlib import Path

from nes_prefetch912 import BASE, OUT, LeadingRecord, monitor, peer
from nes_raw506 import once


def work(mode):
    return BASE.parent / ('nes-overlap913-' + mode)


def prepare(mode):
    directory=work(mode)/'link'
    shutil.copytree(BASE/'link',directory)
    path=directory/'src/nes_native_runtime165.c'
    source=path.read_text()
    if mode in ('extra','joint','checked','paired','idle','ordinary'):
        source=once(source,'s->prefetch_left=16;reason=2;', 's->prefetch_left=17;reason=2;')
    elif mode=='short':
        # Only one more offered short block after sixteen paid reads. Keep the
        # previous capacity for data, and leave PREPARE/COMMIT to normal step.
        old='--s->prefetch_left;progress=true;'
        source=once(source,old,old+'''
   if(reason==2 && !s->prefetch_left && r->ready183 &&
      r->state==NES_NATIVE165_RECEIVING && r->status183[5]==0 &&
      r->status183[6]==24) {
    if(!check(ctx) || !nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
   }''')
    path.write_text(source,encoding='utf8',newline='\n')
    if mode in ('idle','ordinary'):
        # poll() has two 259-byte SPI arrays. Let that stack unwind before
        # allocating the 224-line independent OBJ depth check.
        path.write_text(once(source,'--s->prefetch_left;progress=true;', '''--s->prefetch_left;progress=true;
   if(reason==2 && r->state==NES_NATIVE165_COMPLETE)nes_native913_classify(r);'''),newline='\n')
        hdr=directory/'src/nes_native165.h'
        h=once(hdr.read_text(),'bool ready183;', 'bool ready183; uint8_t obj_check913;')
        hdr.write_text(once(h,'void nes_native165_reset(', 'void nes_native913_classify(struct nes_native165 *);\nvoid nes_native165_reset('),newline='\n')
        path=directory/'src/nes_native165.c'
        body=once(path.read_text(),'static bool logical_record(','''void nes_native913_classify(struct nes_native165 *s){
 if(!s->obj_check913)s->obj_check913=1u+obj_overflow807(s);
}
static bool logical_record(''')
        path.write_text(once(body,'bool skip=accept&&obj_overflow807(s);','if(accept)nes_native913_classify(s);\n bool skip=accept&&s->obj_check913==2;'),newline='\n')
    if mode in ('checked','paired'):
        hdr=directory/'src/nes_native165.h'
        hdr.write_text(once(hdr.read_text(),'bool ready183;', 'bool ready183, obj_overflow913;'),newline='\n')
        path=directory/'src/nes_native165.c'
        body=once(path.read_text(),'  s->state=NES_NATIVE165_COMPLETE;return true;', '''
  /* The checked geometry and all raw records are complete. The decision
   * belongs to this receiver until reset. Only prepare may authorize D3. */
  s->obj_overflow913=obj_overflow807(s);
  s->state=NES_NATIVE165_COMPLETE;return true;''')
        path.write_text(once(body,'accept&&obj_overflow807(s)','accept&&s->obj_overflow913'),newline='\n')
    if mode in ('order','joint','paired','ordinary'):
        path=directory/'src/nes_native_sink165.c'
        body=path.read_text()
        a=body.index('  /* Canonical raw CHR remains intact;')
        b=body.index(' bool same=same635(s,p);',a)
        compact=body[a:b]
        body=body[:a]+body[b:]
        body=once(body,'  /* Read the enclosing object representation',compact+'  /* Read the enclosing object representation')
        path.write_text(body,encoding='utf8',newline='\n')


def replay(temp,mode,phase,cold):
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        peer.compare(temp,phase,cold,True,edition=907,work_arm=work(mode),run_id='913'+mode)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','replay','guards'])
    p.add_argument('mode',choices=['extra','short','order','joint','checked','paired','idle','ordinary'])
    p.add_argument('path',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=[1,2],nargs='?')
    p.add_argument('--cold',action='store_true')
    args=p.parse_args()
    if args.action=='prepare':
        prepare(args.mode)
    elif args.action=='guards':
        from check_nes_supply905_arm import run
        run(args.path,work(args.mode),907)
    else:
        replay(args.path,args.mode,args.phase,args.cold)
