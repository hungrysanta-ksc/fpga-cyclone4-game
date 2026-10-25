# SPDX-License-Identifier: MIT
"""Fuse checked compact geometry loads with the existing required-tile pass."""
from nes_delta231 import once
from nes_raw352 import native as previous

def native(d):
    previous(d)
    p=d/'nes_input286.inc';s=p.read_text()
    s=once(s, "Every planner-visible array below\n  * is written completely; packet receiver bookkeeping is not its lifetime.", "Only validated active array prefixes are planner-visible.\n  * Inactive tails are never used; receiver bookkeeping is not their lifetime.")
    start=s.index(' memcpy(s->maps,p,2112);')
    end=s.index(' unsigned raw=0,palettes=',start)
    s=s[:start]+''' /* Load each active compact record once, validate, store and mark its tile.
  * Byte loads avoid alignment and effective-type assumptions on history. */
 memcpy(s->rows,p+2112,224);memcpy(s->palette,p+4321,64);
 memset(s->required,0,sizeof s->required);
 for(unsigned i=0;i<s->counts[0];i++){
  unsigned v=u16(p+i*2);if(v&0x8000)return bad286(3);
  s->maps[i]=(uint16_t)v;need286(v&8191,1);
 }
 for(unsigned i=0;i<s->counts[2];i++){
  const uint8_t *q=p+2336+i*8;
  uint32_t lo=(uint32_t)u16(q)|((uint32_t)u16(q+2)<<16);
  uint32_t hi=(uint32_t)u16(q+4)|((uint32_t)u16(q+6)<<16);
  if(hi>>17)return bad286(4);
  s->objects[i]=(uint64_t)lo|((uint64_t)hi<<32);need286(lo&8191,2);
 }
 for(unsigned i=0;i<s->counts[3];i++){
  const uint8_t *q=p+3360+i*4;
  uint32_t v=(uint32_t)u16(q)|((uint32_t)u16(q+2)<<16);
  s->exceptions[i]=v;need286(v>>19,1);
 }
'''+s[end:]
    p.write_text(s,newline='\n')
