"""Submit completed left-page rows before section 5 on a long left-only update."""
import argparse
import re
from pathlib import Path

from nes_raw506 import once
from prepare_nes_scroll874 import gate_at_map_completion
from check_nes_strip869 import digest
from check_nes_game478 import crc


def prepare(base, patch, policy):
    name = 'nes_native_sink165.c'
    assert digest(base/'obj-nes-100/firmware.stm') == '486d0d8de20235c71073453850ee489a98d588c15c315895db6eb72eee5d5f01'
    source = gate_at_map_completion((base/name).read_text(), 'both-pages')
    if policy.startswith('raster'):
        patch.mkdir(parents=True)
        if policy=='raster-packed':
            source=once(source,'b[0]=(uint8_t)v;b[1]=(uint8_t)(v>>8);',
                        'uint16_t word=(uint16_t)v;memcpy(b,&word,sizeof word);')
        (patch/name).write_text(source,newline='\n')
        name='nes_native165.c'
        src=(base/name).read_text()
        old='''  for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }'''
        # The raster successor changes only bits 0..14. The compressed
        # header excludes raw lines and bounds the entire destination run.
        # Epoch, kind and generation therefore cannot vary within it.
        new='''  while(s->next_kind<4 && s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;
  if(s->next_kind!=4)return fail(s,9);
  if(((v>>44)&31)>=s->counts[5]/32u)return fail(s,12);
  for(unsigned i=0;i<n;i++){
   s->raster[start+i]=v;
   v=raster_next471(v);
  }
  s->at[4]+=n;s->records+=n;'''
        if policy!='raster':
            new='''  if(!logical_record(s,4,gen,start,v))return false;
  for(unsigned i=1;i<n;i++){
   v=raster_next471(v);
   s->raster[start+i]=v;
  }
  s->at[4]+=n-1;s->records+=n-1;'''
        (patch/name).write_text(once(src,old,new),newline='\n')
        compact_plan(base,patch)
        return
    anchor = ' if((((uint32_t)(map>>32))&0x7ffffu)==0x7ffffu){'
    source = once(source, anchor, ''' /* At this callback all BG slots and both pages are final. Send the
  * remaining left-page rows before OBJ only on a warm left-only long run.
  * The entry guard excludes an outstanding bulk. Each packet still
  * acquires checked credit, and map527 advances the real row cursor. */
 uint32_t right=(uint32_t)(map>>32);
 if(((right?right:(uint32_t)map)&0x7ffffu)==0x7ffffu){''')
    source=once(source,'if(fragments>112/4){','if(right && fragments>112/4){')
    source=once(source,'if((uint32_t)map && w &&','if(right && (uint32_t)map && w &&')
    # Existing wire fields are little endian on Cortex-M4. Use a fixed copy
    # so GCC can emit one unaligned store instead of the byte-shift loop.
    source = once(source,'for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));',
                  'memcpy(b+4,&s->serial,4);')
    source = once(source,'for(unsigned i=0;i<4;i++){b[4+i]=(uint8_t)(s->serial>>(8*i));b[8+i]=(uint8_t)(r->epoch>>(8*i));}',
                  'memcpy(b+4,&s->serial,4);memcpy(b+8,&r->epoch,4);')
    patch.mkdir(parents=True)
    (patch/name).write_text(source,newline='\n')
    # All D0 inquiries transmit exactly the same eight bytes. Only the
    # request construction is shared. Still issue and verify each reply.
    name='nes_native165.c'
    src=(base/name).read_text()
    query=bytes.fromhex('d000000000ff')
    wire=query+bytes([crc(query,8,7,0),0xa5])
    ref='static bool status('
    values=','.join(hex(x) for x in wire)
    src=once(src,ref,'static const uint8_t status_request875[8]={'+values+'};\n'+ref)
    src,count=re.subn(r'frame\(tx,0xd0,0,0\);\s*if\(!fn\(ctx,tx,',
                      'if(!fn(ctx,status_request875,',src)
    assert count==4
    (patch/name).write_text(src,newline='\n')
    compact_plan(base,patch)


def compact_plan(base,patch):
    # Keep the plan fault recorder out of each caller's successful path.
    name='nes_plan_service200.c'
    src=once((base/name).read_text(),'static bool fail(struct nes_plan200',
             'static __attribute__((cold,noinline)) bool fail(struct nes_plan200')
    (patch/name).write_text(src,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('patch',type=Path)
    p.add_argument('--policy',choices=('left','raster','raster-first','raster-packed'),default='left')
    args=p.parse_args()
    prepare(args.base,args.patch,args.policy)
