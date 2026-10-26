# SPDX-License-Identifier: MIT
"""Keep current geometry first;fill unused seven-tag hint lanes in BG slot order."""
from nes_delta231 import once

def apply(d):
 p=d/'nes_decode280.c';s=p.read_text()
 s=once(s,'if(n&&n<3)for(unsigned i=r->bg_slots;i&&n<3;){\n  --i;unsigned tag=r->bg[i];',
  'if(n&&n<7)for(unsigned i=0;i<r->bg_slots&&n<7;i++){\n  unsigned tag=r->bg[i];')
 s=once(s,'n=add_tag367(tags,n,tag,3);','{unsigned before=n;n=add_tag367(tags,n,tag,7);if(n!=before)break;}')
 start=s.index(' /* Complete a small current frontier');end=s.index(' if(n&&n<7)',start)
 s=s[:start]+''' /* Current CRC-checked geometry keeps its priority. Fill the remaining
  * fixed seven lanes with the earliest prior displayed-bank deficit,then
  * additional missing tags in current CRC-checked geometry. Natural BG slot
  * order matches the retained planner's earliest immutable identity slots.
  * This is physical-ROM speculation only;current plans remain authoritative.
  * No mapper reads,register snapshots,future geometry or new cache are used. */
'''+s[end:]
 marker=' /* Current changed geometry wins the narrow ROM window.'
 extra=''' /* Fill the remaining fixed lanes from verified columns;this extends
  * the current one-tag-per-group frontier without acquiring future input.
  * The two-entry duplicate filter expires at each group/call. */
 if(n&&n<7&&geometry_groups367)for(unsigned g=0;g<32&&n<7;g++)if(geometry_groups367&(UINT32_C(1)<<g)){
  uint16_t checked[2]={65535,65535};
  for(unsigned i=0;i<33&&n<7;i++){
   unsigned word=u16(history286+66*g+2*i),tag=word&8191;
   if(word&32768)return 0;
   if(tag==checked[0]||tag==checked[1])continue;
   checked[1]=checked[0];checked[0]=(uint16_t)tag;
   if(!(target_tags367[tag>>5]&(UINT32_C(1)<<(tag&31))))n=add_tag367(tags,n,tag,7);
  }
 }
'''
 s=once(s,marker,extra+marker)
 p.write_text(s,newline='\n')
