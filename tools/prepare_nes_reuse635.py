# SPDX-License-Identifier: MIT
"""Emit a bank-reuse head only when both committed images match the desired bytes."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import once,sha


def prepare(base,out):
    assert sha(base/'src/obj-nes-100/firmware.stm')==json.loads((base.parent/'arm.json').read_text())['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    p=out/'src/nes_native_sink165.h'
    s=once(p.read_text(),'bool displayed;uint8_t map_next;', '''bool displayed;uint8_t map_next;
 uint32_t ack635[2];uint8_t palette635[512],tail635[432];''')
    p.write_text(s,newline='\n')
    p=out/'src/nes_sink_window184.c'
    p.write_text(once(p.read_text(),'p[0]!=8&&p[0]!=7','p[0]!=8&&p[0]!=9&&p[0]!=7'),newline='\n')
    p=out/'src/nes_native_sink165.c';s=p.read_text()
    s=once(s,'b[0]==8||bulk_submit','b[0]==8||b[0]==9||bulk_submit')
    s=once(s,'bool nes_sink212_seal(','''static bool __attribute__((noinline)) same635(const struct nes_native_sink165 *s,const struct nes_native_video165 *p){
 return (s->ack635[0]||s->ack635[1])&&!memcmp(s->palette635,p->cgram,512)&&!memcmp(s->tail635,p->oam+112,432);
}
static bool __attribute__((noinline)) send635(struct nes_native_sink165 *s,const struct nes_native_video165 *p,unsigned bank){
 uint8_t cmd[116];
 memcpy(cmd,p->oam,112);
 memcpy(cmd+112,&s->ack635[bank],4);
 return packet_wire(s,9,4,0,cmd,sizeof cmd,0);
}
static void __attribute__((noinline)) commit635(struct nes_native_sink165 *s,const struct nes_native_video165 *p,unsigned bank,bool same){
 if(!same){
  memcpy(s->palette635,p->cgram,512);memcpy(s->tail635,p->oam+112,432);
  s->ack635[0]=0;s->ack635[1]=0;
 }
 s->ack635[bank]=s->serial;
}
bool nes_sink212_seal(''')
    s=once(s,' if(!span(s,3,0,p->cgram,512))return false;', ''' bool same=same635(s,p);
 if(same&&s->displayed&&s->ack635[r->target]&&s->ack635[1-r->target]){
  if(!send635(s,p,r->target))return false;
 }else{
 if(!span(s,3,0,p->cgram,512))return false;''')
    s=once(s,'if(!oam227(s,p->oam)||!span(s,5,0,p->hdma,p->hdma_size))return false;',
           'if(!oam227(s,p->oam))return false;\n }\n if(!span(s,5,0,p->hdma,p->hdma_size))return false;')
    s=once(s,'if(!nes_resident211_commit(r,s->serial,s->generation,r->target,true))return fail(s,5);',
           'unsigned bank=r->target;\n if(!nes_resident211_commit(r,s->serial,s->generation,bank,true))return fail(s,5);\n commit635(s,p,bank,same);')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();prepare(a.base,a.out)
