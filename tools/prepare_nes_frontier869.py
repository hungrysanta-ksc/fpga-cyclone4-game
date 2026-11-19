"""Materialize a whole-ARM size candidate with the guarded post-BG strip producer."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)


def prepare(base,out,right=False):
    ref=json.loads((ROOT/'analysis/trial866-package.json').read_bytes())
    assert hashlib.sha256((base/'obj-nes-100/firmware.stm').read_bytes()).hexdigest()==ref['ARM']
    out.mkdir(parents=True,exist_ok=False)
    def edit(name,pairs):
        text=(base/name).read_text()
        for old,new in pairs:text=replace(text,old,new)
        (out/name).write_text(text)
    if not right:
        edit('nes_native_video165.h',[('bool scroll_issued;', 'bool scroll_issued, strip_ready869;')])
        edit('nes_planner211.c',[('p->map_dirty=inherit?', 'p->strip_ready869=false;p->map_dirty=inherit?'),
            (' if(resident->offer_map && !resident->offer_map(resident->ctx,next_offer!=3))',
             ' p->strip_ready869=true;\n if(resident->offer_map && !resident->offer_map(resident->ctx,next_offer!=3))')])
    edit('nes_native_sink165.h',[('uint32_t column_epoch, column_serial[2];',
        'uint32_t column_epoch;' if right else 'uint32_t column_epoch; uint16_t strip_page, strip_col, strip_count;')])
    edit('nes_sink_window184.c',[('p[0]!=9&&p[0]!=7','(unsigned)(p[0]-9)>1&&p[0]!=7')])
    source=(base/'nes_native_sink165.c').read_text()
    source=replace(source,'static uint8_t column_map[2][19*36];',
        (ROOT/'tools/nes_history869.c').read_text()+'\nstatic struct history maps869;\n'
        '_Static_assert(__builtin_offsetof(struct nes_native_video165,map)%2==0,"map word alignment");')
    source=replace(source,' memset(s,0,sizeof(*s));',' stop869(&maps869);\n memset(s,0,sizeof(*s));')
    source=replace(source,'memset(s->column_serial,0,sizeof s->column_serial);','stop869(&maps869);')
    source=replace(source,' s->serial=r->serial;', ' s->strip_count=0; s->serial=r->serial;')
    source=replace(source,'if(op==26)op=9;','if(op==26)op=10;')
    source=replace(source,'b[0]==9||bulk_submit','(unsigned)(b[0]-9)<=1||bulk_submit')
    start=source.index('static bool column853(')
    end=source.index(' bool pairable=',start)
    source=source[:start]+'''bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,unsigned early){
 unsigned page=mask==UINT64_C(0x7fffff)?0:2048;
 if(mask==(UINT64_C(0x7fffff)<<(page/64)) && (s->map_next&127)<=page/64 && !s->disable_column &&
    s->serial>2 && maps869.serial[(s->serial-1)&1]==s->serial-2 && maps869.serial[s->serial&1]==s->serial-1){
  if(!p->strip_ready869 || early==2)return true;
  struct publication pub={.epoch=s->column_epoch,.serial=s->serial,.bank=(s->serial-1)&1,
                          .map=(const mapword869 *)p->map,.page=page};
  uint16_t payload[50];
  unsigned n=prepare869(&maps869,&pub,payload);
  if(n){
   if(!packet(s,early?26:10,2,page,(const uint8_t *)payload,n))return false;
   s->strip_page=page;s->strip_col=payload[3]/2;s->strip_count=n==54?1:2;
   s->map_next=page/64+23;s->map_pair683=false;
   return true;
  }
 }
'''+source[end:]
    start=source.index(' bool valid=s->column_serial[bank]')
    end=source.index(' commit635(',start)
    source=source[:start]+''' struct publication pub={.epoch=s->column_epoch,.serial=s->serial,.bank=bank,
  .map=(const mapword869 *)p->map,.page=s->strip_page,.col=s->strip_col,.count=s->strip_count,
  .mode=s->strip_count!=0,.other_rows={ (uint32_t)r->map_upload & 0x7fffff,
                                        (uint32_t)(r->map_upload>>32) & 0x7fffff }};
 if(s->strip_count)pub.other_rows[s->strip_page/2048]=0;
 (void)publish869(&maps869,&pub);
'''+source[end:]
    if right:
        begin=source.index('/* Bounded shadow')
        end=source.index('_Static_assert(__builtin_offsetof',begin)
        source=source[:begin]+(ROOT/'tools/nes_right869.c').read_text()+'\nstatic struct right869 maps869;\n'+source[end:]
        source=source.replace('stop869(&maps869);','maps869.keep=0;')
        start=source.index(' unsigned page=mask==')
        end=source.index('   if(!packet(s,early?',start)
        source=source[:start]+''' if(mask==(UINT64_C(0x7fffff)<<32) && (s->map_next&127)<=32 &&
    !s->disable_column && s->serial>2 && maps869.keep && maps869.differing!=UINT32_MAX){
  /* build211 clears hdma_size on entry. Its sole initial publication
   * follows the final BG row, before the final map offer. */
  if(!p->hdma_size || early==2)return true;
  uint16_t payload[50];
  unsigned n=right_packet869(&maps869,(const mapword869 *)(p->map+2048),s->serial,payload);
  unsigned page=2048;
  if(n){
'''+source[end:]
        source=replace(source,'   s->strip_page=page;s->strip_col=payload[3]/2;s->strip_count=n==54?1:2;','')
        start=source.index(' struct publication pub=')
        end=source.index(' commit635(',start)
        source=source[:start]+''' remember869(&maps869,(const mapword869 *)(p->map+2048),
             !((uint32_t)(p->map_dirty>>32)&0x7fffff));
'''+source[end:]
        source=source.replace(' s->strip_count=0;','')
    (out/'nes_native_sink165.c').write_text(source)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--right',action='store_true')
    prepare(**vars(p.parse_args()))
