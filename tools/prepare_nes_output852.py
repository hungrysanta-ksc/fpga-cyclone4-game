"""Transfer 36 literal bytes per map row when its acknowledged 28-byte tail stays zero."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from pack_nes_static751 import pack
from prepare_nes_longrun694 import codec
from prepare_nes_map828 import PROBES
from nes_report828 import reports


def arm(out):
    src=PROBES/'nes-poll849/link02/src'
    reference=json.loads((Path(__file__).resolve().parents[1]/'analysis/comparison851-results.json').read_bytes())
    assert sha(src/'obj-nes-100/firmware.stm')==reference['demo']['phases']['1']['runs']['849']['firmware']
    out.mkdir(parents=True,exist_ok=False)
    name='nes_native_sink165.h'
    header=once((src/name).read_text(),'uint32_t ack635[2];','''uint32_t tail_rows[2],tail_epoch,pending_rows;
 uint32_t ack635[2];''')
    (out/name).write_text(header)
    name='nes_native_sink165.c'
    s=(src/name).read_text()
    s=once(s,' uint8_t b[12];put16(b,0x4891);',''' if(!r->displayed || s->tail_epoch!=r->epoch){
  memset(s->tail_rows,0,sizeof s->tail_rows);s->tail_epoch=r->epoch;
 }
 s->pending_rows=s->tail_rows[r->target];
 uint8_t b[12];put16(b,0x4891);''')
    s=once(s,' commit635(s,p,bank,same);',''' s->tail_rows[bank]=s->pending_rows;
 commit635(s,p,bank,same);''')
    # Capture the row extent before the original repeated-word encoder shortens n.
    s=once(s,' if(op==2 && n>=4',' unsigned map_size=n;\n if(op==2 && n>=4')
    s=once(s,' put16(b+12,n);if(n){',''' if(op==2 && section==2 && at<2048 && at+map_size>2048)
  s->pending_rows&=~((1u<<((at+map_size-2048)/64))-1);
 if(op==2 && section==2 && at>=2048 && !(at&63) && map_size && map_size<=192 && !(map_size&63) && at+map_size<=4096){
  static const uint8_t zeros[28]={0};
  unsigned bank=(s->serial-1)&1;
  uint32_t base=s->serial-2;
  bool reuse=b[0]==2 && s->serial>2;
  for(unsigned pos=0;pos<map_size;pos+=64){
   uint32_t bit=UINT32_C(1)<<((at+pos-2048)/64);
   if(!(s->tail_rows[bank]&bit))reuse=false;
   if(!data || !memcmp(data+pos+36,zeros,28))s->pending_rows|=bit;
   else {s->pending_rows&=~bit;reuse=false;}
  }
  if(reuse){
   memcpy(b+16,&base,4);
   unsigned used=4;
   for(unsigned pos=0;pos<n;pos+=64){memcpy(b+16+used,data+pos,36);used+=36;}
   b[0]=9;put16(b+14,n);n=used;
  }
 }
 put16(b+12,n);if(n && !(b[0]==9 && section==2)){''')
    s=once(s,'s->plan->window->last[0]==2 &&','(s->plan->window->last[0]==2 || s->plan->window->last[0]==9) &&')
    (out/name).write_text(s)
    reports(src,out)


def dma_rows(c):
    c.emit(0xc2,0x20,0xa9,0,0x80);c.absolute(0x8d,0x4300)
    c.emit(0xe2,0x20);c.store(0x4304,0x40)
    c.emit(0xc2,0x20,0xa2,20,0,0xa4,0x7a);c.absolute(0xad,0x120c)
    c.label('row852');c.emit(0x48);c.absolute(0x8c,0x2181);c.absolute(0x8e,0x4302)
    c.emit(0xa9,36,0);c.absolute(0x8d,0x4305)
    c.emit(0xe2,0x20);c.store(0x420b,1)
    c.emit(0x8b,0xa9,0x7f,0x48,0xab,0xc2,0x20)
    c.branch(0x80,'check_tail852');c.label('bad_prefix852');c.jump('bad_row852')
    c.label('check_tail852');c.label('prefix852')
    for off in (0,2,4):
        c.long(0xbf,0x400000+off);c.absolute(0xd9,off);c.branch(0xd0,'bad_prefix852')
    for take,save in ((0x8a,0xaa),(0x98,0xa8)):
        c.emit(take,0x18,0x69,6,0,save)
    c.emit(0x29,63,0,0xc9,36,0);c.branch(0xd0,'prefix852')
    c.emit(0xa9,0,0)
    for off in range(0,28,2):
        c.absolute(0x19,off)
    c.branch(0xd0,'bad_row852');c.emit(0xab,0x98,0x18,0x69,28,0,0xa8)
    call(c,'service');c.branch(0xf0,'continue852');c.emit(0x68);c.jump('stop_packet')
    c.label('bad_row852');c.emit(0xab,0x68);c.jump('bad_packet')
    c.label('continue852');c.emit(0x68,0x38,0xe9,64,0);c.branch(0xf0,'done852');c.jump('row852')
    c.label('done852');c.jump('accepted')


def client(out,fast=False):
    parent=PROBES/'nes-output815/client'
    assert sha(parent/'sink165.sfc')=='3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1'
    body=bytearray((parent/'body.bin').read_bytes())
    c=Code(0x7e2000+len(body))
    c.labels.update(json.loads((parent/'labels.json').read_bytes()))
    def hook(pc,original,label):
        index=pc-0x2000
        assert body[index:index+3]==bytes.fromhex(original)
        body[index:index+3]=b'\x4c'+(c.labels[label]&65535).to_bytes(2,'little')
    c.label('header852');hook(0x224c,'4cd434','header852')
    c.absolute(0xad,0x1200);c.emit(0xc9,9,2);c.branch(0xf0,'map852');c.jump('reuse635')
    c.label('map852')
    c.absolute(0xad,0x120a);c.emit(0xc9,0,8);c.branch(0x90,'reject852')
    c.absolute(0xad,0x1034);c.emit(0x0a,0x0a,0xaa)
    c.long(0xaf,0x400010);c.long(0x0f,0x400012);c.branch(0xf0,'reject852')
    for i in (0,2):
        c.long(0xaf,0x400010+i);c.absolute(0xdd,0x14d0+i);c.branch(0xd0,'reject852')
    if fast:
        c.absolute(0xad,0x120e);c.branch(0xf0,'reject852')
        c.emit(0xc9,193,0);c.branch(0xb0,'reject852');c.emit(0x89,63,0);c.branch(0xd0,'reject852')
        c.emit(0x4a);c.absolute(0x8d,0x1260);c.emit(0x4a,0x4a,0x4a,0x18)
        c.absolute(0x6d,0x1260);c.emit(0x69,4,0);c.absolute(0xcd,0x120c);c.branch(0xd0,'reject852')
        c.absolute(0xad,0x120e);c.absolute(0x8d,0x120c);c.jump('data')
    else:
        for count in (1,2,3):
            c.absolute(0xad,0x120c);c.emit(0xc9,4+36*count,0);c.branch(0xd0,f'next852_{count}')
            c.absolute(0xad,0x120e);c.emit(0xc9,64*count,0);c.branch(0xd0,'reject852')
            c.absolute(0x8d,0x120c);c.jump('data');c.label(f'next852_{count}')
    c.label('reject852');c.jump('bad_packet')
    c.label('literal852');hook(0x252f,'4cdb25','literal852')
    c.emit(0xc9,9);c.branch(0xd0,'other852');c.emit(0xe0,4,0);c.branch(0xf0,'restore852')
    c.label('other852');c.jump('literal1814')
    c.label('restore852')
    if fast:
        dma_rows(c)
    else:
        literal_rows(c)
    body.extend(c.finish())
    with patch.object(codec,'pack',pack):
        codec.build(PROBES/'nes-reuse635/client04',out,edit_body=lambda *_:bytes(body),allow_extension=True,
                    prefix_sizes=[128,64,16,2],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    info=json.loads((out/'build.json').read_bytes())
    assert info['physical_free_B']==5056-320-info['prefix_B']-info['encoded_B']
    (out/'labels.json').write_text(json.dumps(c.labels)+'\n')


def literal_rows(c):
    c.emit(0xc2,0x20,0xa2,20,0,0xa4,0x7a);c.absolute(0xad,0x120c)
    c.label('row852');c.emit(0x48,0x8b,0xda,0x5a,0xa9,35,0,0x54,0x7f,0x40)
    # DBR now selects destination WRAM. Y points to the retained tail.
    c.emit(0xa9,0,0);c.label('check_tail852')
    for off in range(0,28,2):
        c.absolute(0x19,off)
    c.emit(0x7a,0xfa,0xc9,0,0);c.branch(0xd0,'bad_row852')
    # Independently compare every written prefix word against the bus aperture.
    c.label('prefix852');c.long(0xbf,0x400000);c.absolute(0xd9,0);c.branch(0xd0,'bad_row852')
    c.emit(0xe8,0xe8,0xc8,0xc8,0x98,0x29,63,0,0xc9,36,0);c.branch(0xd0,'prefix852')
    c.emit(0x98,0x18,0x69,28,0,0xa8,0xab)
    call(c,'service');c.branch(0xf0,'continue852');c.emit(0x68);c.jump('stop_packet')
    c.label('bad_row852');c.emit(0xab,0x68);c.jump('bad_packet')
    c.label('continue852');c.emit(0x68,0x38,0xe9,64,0);c.branch(0xf0,'done852');c.jump('row852')
    c.label('done852');c.jump('accepted')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('arm','client','dma'));p.add_argument('out',type=Path)
    a=p.parse_args()
    if a.mode=='dma':
        client(a.out,True)
    else:
        {'arm':arm,'client':client}[a.mode](a.out)
