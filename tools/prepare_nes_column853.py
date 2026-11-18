"""Build the ACK-bound 23-row map packet and its independently checking consumer."""
import argparse
import json
import re
from unittest.mock import patch
from pathlib import Path

from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import once, sha
from nes_report828 import reports
from pack_nes_static751 import pack
from prepare_nes_longrun694 import codec
from prepare_nes_map828 import PROBES

PROBE = PROBES / 'nes-column853'


def arm(out,lazy=True):
    base = PROBES / 'nes-poll849/link02/src'
    record=Path(__file__).resolve().parents[1]/'analysis/comparison851-results.json'
    expected=json.loads(record.read_bytes())['demo']['phases']['1']['runs']['849']['firmware']
    assert sha(base/'obj-nes-100/firmware.stm')==expected
    out.mkdir(parents=True)
    head = 'nes_native_sink165.h'
    (out/head).write_text(once((base/head).read_text(), 'uint32_t ack635[2];',
        'uint32_t column_epoch, column_serial[2]; uint8_t disable_column;\n uint32_t ack635[2];'))
    name = 'nes_native_sink165.c'
    source = (base/name).read_text()
    source = once(source, 'static const uint8_t zero[2]', '''/* One physical runtime. Validity is owned by its resettable sink and epoch. */
static uint8_t column_map[2][19*36];
static const uint8_t zero_tail[28];
static const uint8_t zero[2]''')
    source = once(source, ' uint8_t b[12];put16(b,0x4891);', ''' if(!r->displayed || s->column_epoch!=r->epoch){
  memset(s->column_serial,0,sizeof s->column_serial);s->column_epoch=r->epoch;
 }
 uint8_t b[12];put16(b,0x4891);''')
    source = once(source, ' commit635(s,p,bank,same);', ''' bool valid=true;
 if(!s->column_serial[bank] || ((uint32_t)(r->map_upload>>32)&0x7fffff)){
  const uint8_t *row=p->map+2048;
  /* Represent the first five equal rows once. Reject any loss of information. */
  if(memcmp(row,row+64,4*64))valid=false;
  for(unsigned i=0;i<19;i++){
   const uint8_t *v=row+(i+4)*64;
   if(memcmp(v+36,zero_tail,28)){valid=false;break;}
   memcpy(column_map[bank]+i*36,v,36);
  }
 }
 s->column_serial[bank]=valid?s->serial:0;
 commit635(s,p,bank,same);''')
    source = once(source,'op!=24 && op!=25','op!=24 && op!=25 && op!=26')
    source = once(source,' if(op==25)op=5;', ' if(op==26)op=9;\n if(op==25)op=5;')
    source = once(source,'section==2&&op==2?', 'section==2?')
    source = once(source, 'bool map527(', '''/* Both committed banks must agree with the new map outside the column.
 * The consumer independently reads both WRAM banks. No comparison hash. */
static bool column853(struct nes_native_sink165 *s,const uint8_t *map,bool *sent,unsigned early){
 unsigned bank=(s->serial-1)&1;
 const uint8_t *old=column_map[bank], *peer=column_map[bank^1];
 unsigned col=0;
 while(col<36 && !memcmp(old+col,map+col,2))col+=2;
 if(col==36)return true;
 uint8_t payload[52];
 memcpy(payload,&s->column_serial[bank],4);
 put16(payload+4,col);
 for(unsigned i=0;i<23;i++,map+=64){
  unsigned index=(i>4?i-4:0)*36; old=column_map[bank]+index;peer=column_map[bank^1]+index;
  if(memcmp(map+36,zero_tail,28) || !memcmp(old+col,map+col,2))return true;
  for(unsigned j=0;j<36;j+=2){
   uint16_t want,a,b;
   memcpy(&want,map+j,2);memcpy(&a,old+j,2);memcpy(&b,peer+j,2);
   if(j!=col && (a!=want || b!=want))return true;
  }
  memcpy(payload+6+i*2,map+col,2);
 }
 *sent=true;
 return packet(s,early==3?26:9,2,2048,payload,sizeof payload);
}
bool map527(''')
    source = once(source, ' bool pairable=early!=1', ''' /* Before the complete BG plan, rows can still be rewritten. */
 if((s->map_next&127)<=32 && mask==(UINT64_C(0x7fffff)<<32) && !s->disable_column &&
    s->serial>2 && s->column_serial[(s->serial-1)&1]==s->serial-2 &&
    s->column_serial[s->serial&1]==s->serial-1){
  if(early==1 || early==2)return true;
  bool sent=false;
  if(!column853(s,p->map+2048,&sent,early))return false;
  if(sent){s->map_next=55;s->map_pair683=false;return true;}
 }
 bool pairable=early!=1''')
    if lazy:
        source=once(source,'bool valid=true;\n if(!s->column_serial[bank] || ((uint32_t)(r->map_upload>>32)&0x7fffff)){',
                    'bool valid=s->column_serial[bank]!=0;\n if((uint32_t)(r->map_upload>>32)&0x7fffff){')
        source=once(source,'if(memcmp(row,row+64,4*64))valid=false;\n  for(unsigned i=0;i<19;i++){',
                    'valid=!memcmp(row,row+64,4*64);\n  for(unsigned i=0;valid && i<19;i++){')
        # An all-zero suffix equals its one-byte shift and begins with zero.
        source=source.replace('static const uint8_t zero_tail[28];','')
        for row in ('map','v'):
            source=once(source,f'memcmp({row}+36,zero_tail,28)',
                        f'{row}[36] || memcmp({row}+36,{row}+37,27)')
    (out/name).write_text(source)
    reports(base,out)
    # The formatter runs after STOP. Walk its NUL-delimited dictionary instead
    # of reserving a second offset table in Flash for random access.
    report=out/'nes_budget210.c'
    fmt=report.read_text()
    fmt,count=re.subn(r' static const uint16_t offsets\[\] = \{[\d,]+\};\n','',fmt)
    assert count==1
    report.write_text(once(fmt,'const char *word = words + offsets[symbol-128];',
                           'const char *word=words; while(symbol-->128){while(*word++){} }'))


def client(out,grouped=True):
    base=PROBES/'nes-output815/client'
    assert sha(base/'sink165.sfc')=='3ca9aaefd9efad64a3cb63b59b627314f9f6b8e87fb79e236ba7e7d01fa856e1'
    body=bytearray((base/'body.bin').read_bytes())
    c=Code(0x7e2000+len(body))
    c.labels.update(json.loads((base/'labels.json').read_bytes()))

    def hook(pc,old,label):
        i=pc-0x2000
        assert body[i:i+3]==bytes.fromhex(old)
        c.label(label)
        body[i:i+3]=bytes([0x4c])+int(c.labels[label]&65535).to_bytes(2,'little')

    hook(0x224c,'4cd434','column_header')
    c.absolute(0xad,0x1200);c.emit(0xc9,9,2);c.branch(0xf0,'column_identity');c.jump('reuse635')
    c.label('column_identity')
    for addr,expected in [(0x120a,2048),(0x120c,52),(0x120e,0)]:
        c.absolute(0xad,addr);c.emit(0xc9);c.word(expected);c.branch(0xd0,'bad_column')
    c.long(0xaf,0x400014);c.emit(0xc9,63,0);c.branch(0xb0,'bad_column')
    c.emit(0x4a);c.branch(0xb0,'bad_column')
    c.absolute(0xad,0x1034);c.emit(0x0a,0x0a,0xaa)
    c.long(0xaf,0x400010);c.long(0x0f,0x400012);c.branch(0xf0,'bad_column')
    for off in (0,2):
        c.long(0xaf,0x400010+off);c.absolute(0xdd,0x14d0+off);c.branch(0xd0,'bad_column')
    # BEGIN checked displayed serial and selected the opposite target.
    c.emit(0x8a,0x49,4,0,0xaa)
    for off in (0,2):
        c.absolute(0xad,0x1248+off);c.absolute(0xdd,0x14d0+off);c.branch(0xd0,'bad_column')
    c.emit(0xa9);c.word(1472);c.absolute(0x8d,0x120c);c.jump('data')
    c.label('bad_column');c.jump('bad_packet')
    hook(0x252f,'4cdb25','column_literal')
    c.emit(0xc9,9);c.branch(0xd0,'other_column');c.emit(0xe0,4,0);c.branch(0xf0,'column_write')
    c.label('other_column');c.jump('literal1814')
    if grouped:
        c.label('column_write')
        # Relative X scans both fixed map areas. Y stays on the one patched cell.
        # Normalize only that writable cell to its peer. Every omitted word is
        # compared exactly. Install and read back the packet word before service.
        c.emit(0xc2,0x20,0xa9,22,0,0x85,0x60,0xa5,0x7a,0x49,0,0x80,0x85,0x74)
        c.long(0xaf,0x400014);c.emit(0x85,0x68,0xa2,0,0)
        c.label('column_row')
        c.emit(0x8a,0x18,0x69,64,0,0x85,0x62,0x8a,0x18,0x65,0x68,0xa8)
        c.emit(0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20,0xb1,0x74,0x91,0x7a)
        c.label('column_compare')
        for off in range(0,16,2):
            c.absolute(0xbd,0x5800+off);c.absolute(0xdd,0xd800+off);c.branch(0xd0,'column_damage')
        c.emit(0x8a,0x18,0x69,16,0,0xaa,0xe4,0x62);c.branch(0xd0,'column_compare')
        c.emit(0xda,0xa6,0x60);c.long(0xbf,0x400000);c.emit(0xfa,0x91,0x7a)
        c.label('column_written');c.emit(0xd1,0x7a);c.branch(0xd0,'column_damage')
        c.emit(0xe6,0x60,0xe6,0x60)
        c.label('column_service');c.emit(0xab);call(c,'service');c.branch(0xf0,'column_next');c.jump('stop_packet')
        c.label('column_next');c.emit(0xa5,0x60,0xc9,68,0);c.branch(0xf0,'column_done');c.jump('column_row')
        c.label('column_done');c.jump('accepted')
        c.label('column_damage');c.emit(0xab);c.jump('bad_packet')
    else:
        c.label('column_write')
        # DP 60..6a scratch is free after common mark212 registration.
        c.emit(0xc2,0x20,0xa9,22,0,0x85,0x60,0xa6,0x7a,0x8a,0x49,0,0x80,0xa8)
        c.label('column_row')
        c.emit(0x8a,0x18,0x69,64,0,0x85,0x62,0x8a,0x18);c.long(0x6f,0x400014);c.emit(0x85,0x64)
        c.emit(0x8b,0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20)
        c.label('column_prefix');c.emit(0xe4,0x64);c.branch(0xf0,'column_word')
        call(c,'check_word853');c.branch(0x80,'column_prefix')
        c.label('column_word');c.emit(0xda,0xa6,0x60);c.long(0xbf,0x400000);c.emit(0xfa)
        c.absolute(0x9d,0);c.absolute(0xdd,0);c.branch(0xd0,'column_damage')
        c.emit(0xe6,0x60,0xe6,0x60,0xe8,0xe8,0xc8,0xc8)
        c.label('column_suffix');c.emit(0xe4,0x62);c.branch(0xf0,'column_service')
        call(c,'check_word853');c.branch(0x80,'column_suffix')
        c.label('check_word853');c.absolute(0xbd,0);c.absolute(0xd9,0);c.branch(0xd0,'column_mismatch')
        c.emit(0xe8,0xe8,0xc8,0xc8,0x60)
        c.label('column_mismatch');c.emit(0x68)  # discard JSR return
        c.label('column_damage');c.emit(0xab);c.jump('bad_packet')
        c.label('column_service');c.emit(0xab);call(c,'service');c.branch(0xf0,'column_next');c.jump('stop_packet')
        c.label('column_next');c.emit(0xa5,0x60,0xc9,68,0);c.branch(0xd0,'column_row');c.jump('accepted')
    body.extend(c.finish())
    with patch.object(codec,'pack',pack):
        codec.build(PROBES/'nes-reuse635/client04',out,edit_body=lambda *_:bytes(body),allow_extension=True,
                    prefix_sizes=[128,64,16,2],medium_pages=True,boot_bytes=320,fast_backrefs=True)
    (out/'labels.json').write_text(json.dumps(c.labels)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('arm','eager','client','scalar'))
    parser.add_argument('out',type=Path)
    options=parser.parse_args()
    {'arm':arm,'eager':lambda out:arm(out,False),'client':client,'scalar':lambda out:client(out,False)}[options.mode](options.out)
