# SPDX-License-Identifier: MIT
"""Publish section 5 on a completed single plan batch using the normal guarded transport."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once,sha


def prepare(base,out,mode):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='d4ea668a8a30c9dbc4b3858a51379abddb2efc3b36e35024f3c7b8531901693a'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    path=out/'src/nes_native_sink165.c'
    s=once(path.read_text(),'''  if(!((mask>>g)&1)){g++;continue;}
  unsigned first=g++,count=1;while(g<64&&count<3&&((mask>>g)&1)){g++;count++;}''','''  unsigned bits=(unsigned)(mask>>g);
  if(!(bits&1)){g++;continue;}
  unsigned first=g,count=(bits&7)==7?3:(bits&3)==3?2:1;
  g+=count;''')
    if mode!='control':
        map_start=s.index(' if(!map527(s,p,r->map_upload,false))')
        pack=s.index('  /* Canonical raw',map_start)
        pal=s.index(' if(!span(s,3,0',pack)
        scroll=s.index(' if(!oam227',pal)
        end=s.index(' uint8_t descriptor[168]',scroll)
        section=once(s[scroll:end],'if(!oam227(s,p->oam)||!span','if(!span')
        helper='''static bool section627(struct nes_native_sink165 *s,struct nes_native_video165 *p,
 const uint8_t *raw,unsigned packed,uint16_t *extent){
'''+once(section,'size[5]=','*extent=')+' return true;\n}\n'
        maps=s[map_start:pack]
        pack_block=s[pack:pal]
        ordinary=s[pal:scroll]+' if(!oam227(s,p->oam))return false;\n'
        early=''' /* END is already on the bus in the only submitted batch. Every packet
  * still services ready bulk and checked credit before enqueue. */
 bool early=p->patch_count==2 && s->plan && s->plan->sent==1 && !s->plan->count;
 if(early && !section627(s,p,raw,packed,&size[5]))return false;
'''
        normal=' if(!early && !section627(s,p,raw,packed,&size[5]))return false;\n'
        order=pack_block+early+maps if mode=='before' else maps+pack_block+early
        s=s[:map_start]+order+ordinary+normal+s[end:]
        s=once(s,'bool nes_sink212_seal(',helper+'bool nes_sink212_seal(')
    if mode in ('after-small','after-fit'):
        # Both span callers already do these two dry runs on immutable bytes.
        # Keep the strict tie policy and the cost returned to OAM selection.
        first=s.index(' unsigned oldcost=0,newcost=0;')
        end=s.index(' /* Synchronous immutable',first)
        loops=s[first:end]
        s=s[:first]+' bool split=choose627(b,n,0);\n'+s[end:]
        s=once(s,'if(newcost<oldcost)count','if(split)count')
        helper='static bool choose627(const uint8_t *b,unsigned n,unsigned *cost){\n'+loops+''' if(cost)*cost=newcost<oldcost?newcost:oldcost;
 return newcost<oldcost;
}
'''
        s=once(s,'static bool span(',helper+'static bool span(')
        first=s.index(' unsigned old=0,split=0;')
        end=s.index('\n}',first)
        s=s[:first]+' unsigned cost;choose627(b,n,&cost);return cost;'+s[end:]
        if mode=='after-fit':
            s=once(s,'(first?span_cost227(b,first):0)','span_cost227(b,first)')
    if mode=='after-native':
        s=once(s,'''  uint8_t tail[6];for(unsigned i=0;i<3;i++)put16(tail+i*2,p->patch.size[i]);
  if(!packet(s,2,5,offset,tail,6))return false;''','''  _Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__ && sizeof(p->patch.size)==6,
                 "HDMA lengths must exactly match the wire layout");
  if(!packet(s,2,5,offset,(const uint8_t *)p->patch.size,6))return false;''')
    path.write_bytes(s.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('mode',choices=('before','after','after-small','after-fit','after-native','control'))
    a=p.parse_args()
    prepare(a.base,a.out,a.mode)
