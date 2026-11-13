# SPDX-License-Identifier: MIT
"""Optimize checked BG lookups/map writes, optionally offer completed right-page ranges."""
import argparse
from pathlib import Path
from nes_raw506 import once,sha
from prepare_nes_rows757 import prepare as right_page


def prepare(base,out,mode):
    assert sha(base/'obj-nes-100/firmware.stm')=='192cf5becb19bb58ede0be25be73d91e4c1fee1f836eadabcb9999ac2af929a6'
    if mode in ('word','compact'):
        out.mkdir(parents=True,exist_ok=False)
    else:
        right_page(base,out,'page')
        name='nes_native_sink165.c'
        if mode=='tail':
            p=out/name
            p.write_text(once(p.read_text(),'for(unsigned i=0;i<finished && i<8;i++){',
                              'for(unsigned i=6;i<finished && i<8;i++){'),newline='\n')
    name='nes_planner211.c'
    target=out/name
    src=target if target.exists() else base/name
    s=src.read_text()
    start=s.index(' if(p->map[at]')
    end=s.index('\n}',start)
    s=s[:start]+''' /* Cortex-M4 MAP cells are 16-bit little endian. memcpy keeps byte-array aliasing valid. */
 uint16_t old,cell=(uint16_t)word;
 memcpy(&old,p->map+at,sizeof(old));
 if(old!=cell)p->map_dirty|=UINT64_C(1)<<(at/64);
 memcpy(p->map+at,&cell,sizeof(cell));'''+s[end:]
    s=once(s,' unsigned next_offer=3;', ''' /* Current frame only. A used BG slot cannot be evicted before commit/abort.
  * Only ordinary shape slots reach this cache after independent tag validation. */
 uint32_t recent[8]={0};
 unsigned next_offer=3;''')
    s=once(s,'  if(x>=2 && !exceptional', '''  unsigned tag=cell&8191u;
  uint32_t cached=recent[tag&7];
  if(!exceptional && (cached>>16)==tag+1){
   slot=(uint16_t)cached;
  }else if(x>=2 && !exceptional''')
    s=once(s,'  if(slot>=1024)return fail(p,7);','''  if(slot>=1024)return fail(p,7);
  if(!exceptional)recent[tag&7]=((tag+1)<<16)|slot;''')
    if mode=='compact':
        # The eight validated entries subsume the two-column special case.
        i=s.index('  }else if(x>=2 && !exceptional')
        end=s.index('  }else{',i)
        s=s[:i]+s[end:]
        s=once(s,'  unsigned previous_slot=0,older_slot=0;','')
        s=once(s,'  older_slot=previous_slot;previous_slot=slot;','')
        s=once(s,'static void map_word185','static void __attribute__((noinline)) map_word185')
    target.write_text(s,encoding='utf8',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('mode',choices=('word','tail','burst','compact'))
    a=p.parse_args()
    prepare(a.base,a.out,a.mode)
