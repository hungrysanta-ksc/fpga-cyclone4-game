# SPDX-License-Identifier: MIT
"""Explicit 2KiB workset, separate from live raw pixels and allocation keys."""
from nes_delta231 import once


def patch(s):
    s=once(s,'static const struct nes_native165_tile *tile(', 'static uint8_t workset288[2048];\nstatic const struct nes_native165_tile *tile(')
    a=s.index(' unsigned lo=0,hi=s->ntiles;');b=s.index('\nstatic bool patched',a)
    s=s[:a]+''' if(tag>=8192)return NULL;
 unsigned bits=(workset288[tag/4]>>((tag%4)*2))&3;
 /* Callers test membership only; no tile descriptor is dereferenced. */
 return (bits&kind)?s->tiles:NULL;
}
'''+s[b:]
    s=once(s,' unsigned palettes=s->counts[5]/32;', ''' /* Geometry owns this temporary index until the last group and OBJ step.
  * Raw pixels and BG allocation keys are still live in their unions.
  * Never trust an inherited or caller-supplied bitmap. The sorted
  * authoritative tile entries above are checked before rebuilding it. */
 memset(workset288,0,sizeof workset288);
 for(unsigned i=0;i<s->ntiles;i++){
  unsigned tag=s->tiles[i].tag;
  workset288[tag/4]|=(uint8_t)(s->tiles[i].kind<<((tag%4)*2));
 }
 unsigned palettes=s->counts[5]/32;''')
    s=once(s,'   if(cell>>15||(word&0xfc00)', '   if(cell>>15||!tile(s,cell&8191,1)||(word&0xfc00)')
    return s
