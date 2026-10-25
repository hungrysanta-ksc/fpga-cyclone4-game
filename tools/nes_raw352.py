# SPDX-License-Identifier: MIT
"""Changed groups tracked while the checked decoder updates source history."""
from nes_delta231 import once
from nes_read336 import native as previous

def decoder():
    from nes_delta231 import ROOT
    s=(ROOT/'tools/nes_decode280.c').read_text()
    s=once(s,'State receiver280;', 'State receiver280;\nuint32_t source_groups352;')
    s=once(s,'s->last=-1;s->phase=1;take=ci=20;', 'source_groups352=s->raw_cold?UINT32_MAX:0;\n   s->last=-1;s->phase=1;take=ci=20;')
    s=once(s,'     base[at+i]=value;', '     if(s->phase==2&&base[at+i]!=value)source_groups352|=UINT32_C(1)<<(((index-68)*8+i/8)%32);\n     base[at+i]=value;')
    s=once(s,'receiver280.valid=0;receiver280.phase=3;', 'source_groups352=UINT32_MAX;receiver280.valid=0;receiver280.phase=3;')
    s=once(s,'void reset280(void){', 'void reset280(void){source_groups352=UINT32_MAX;')
    return s

def native(d):
    previous(d)
    (d/'nes_decode280.c').write_text(decoder(),newline='\n')
    p=d/'nes_planner285.c';s=p.read_text()
    s='extern void invalidate352(void),publish352(void);\n'+s
    s=once(s,'void reset285(void){','void reset285(void){invalidate352();')
    s=once(s,' return nes_dirty231_commit(', ' unsigned ok=nes_dirty231_commit(')
    s=once(s,'nes_resident211_commit(&resident285,resident285.serial,resident285.generation,resident285.target,true)&&commit289();',
        'nes_resident211_commit(&resident285,resident285.serial,resident285.generation,resident285.target,true)&&commit289();\n if(ok)publish352();else invalidate352();return ok;')
    p.write_text(s,newline='\n')
    p=d/'nes_input286.inc';s=p.read_text()
    s=once(s,'unsigned expansion_error286;', '''unsigned expansion_error286;
/* No duplicate raw cache: decoder tracks changes before history writes.
 * The source base must be the last successfully displayed frame, not merely
 * the last received frame. Keep both banks' stale bits untouched on a skip. */
uint32_t raw_groups352,display_epoch352,display_serial352,display_count352;
void invalidate352(void){raw_groups352=UINT32_MAX;display_epoch352=0;}
void publish352(void){
 if(!receiver280.valid||receiver280.phase||dirty285.open||!dirty285.valid||
    resident285.open||!resident285.displayed||dirty285.fault||resident285.fault){invalidate352();return;}
 display_epoch352=receiver280.epoch;display_serial352=receiver280.serial;
 display_count352=receiver280.raw_count;
}
uint32_t groups352(const struct nes_dirty231 *d,const struct nes_native165 *s){
 if(d!=&dirty285||s!=&input285||s->state!=NES_NATIVE165_COMMITTED||
    !receiver280.valid||receiver280.phase||receiver280.cold||receiver280.raw_cold||
    !d->valid||!resident285.displayed||d->epoch!=resident285.epoch||
    d->serial!=resident285.serial)return UINT32_MAX;
 return raw_groups352;
}''')
    s=once(s,' memcpy(input285.raw_pixels,history286+4398,input285.patch_count*256u);', ''' raw_groups352=UINT32_MAX;
 if(!receiver280.cold&&!receiver280.raw_cold&&display_epoch352==receiver280.epoch&&
    display_serial352!=UINT32_MAX&&display_serial352+1==receiver280.serial&&
    display_count352==receiver280.raw_count&&dirty285.valid&&!dirty285.open&&!dirty285.fault&&
    resident285.displayed&&resident285.open&&!resident285.fault&&
    dirty285.epoch==resident285.epoch&&dirty285.serial+1==resident285.serial){
  raw_groups352=source_groups352;
 }
 memcpy(input285.raw_pixels,history286+4398,input285.patch_count*256u);''')
    s=once(s,'void stop286(void){','void stop286(void){invalidate352();')
    p.write_text(s,newline='\n')
    p=d/'nes_delta231.c';s=p.read_text()
    s=once(s,'#include <string.h>','#include <string.h>\nextern uint32_t groups352(const struct nes_dirty231 *,const struct nes_native165 *);')
    s=once(s,' for(unsigned at=0;at<2048;at+=16){', ''' uint32_t groups=groups352(d,s);
 for(unsigned at=0;at<2048;at+=16){
  if(!(groups&(UINT32_C(1)<<(at/64))))continue;''')
    p.write_text(s,newline='\n')
