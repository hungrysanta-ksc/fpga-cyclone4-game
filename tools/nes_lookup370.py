# SPDX-License-Identifier: MIT
"""Reuse two positive BG membership checks only within one immutable group."""
from nes_delta231 import once

HELPER='''/* The validated input is immutable during one group step. No cache survives
 * this call, an input change, generation change, STOP, or a failed lookup.
 * Call sites bound tags to13bits;0xffff is exclusively the empty sentinel. */
static inline __attribute__((always_inline)) bool bg_tile370(
 const struct nes_native165 *s,unsigned tag,uint16_t checked[2]){
 if(tag==checked[0]||tag==checked[1])return true;
 if(!tile(s,tag,1))return false;
 checked[1]=checked[0];checked[0]=(uint16_t)tag;return true;
}
'''

def apply(d):
 p=d/'nes_planner211.c';s=p.read_text()
 needle='static inline __attribute__((always_inline)) bool patched('
 s=once(s,needle,HELPER+needle)
 s=once(s,'  bool shaped286=false;','  uint16_t checked370[2]={65535,65535};\n  bool shaped286=false;')
 s=once(s,'if(!tile(s,cell&8191,1))','if(!bg_tile370(s,cell&8191,checked370))')
 s=once(s,'if(!tile(s,e>>19,1))','if(!bg_tile370(s,e>>19,checked370))')
 p.write_text(s,newline='\n')
