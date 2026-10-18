# SPDX-License-Identifier: MIT
"""Actual231 C packets and actual23265816 on30 reference scenes, not hardware."""
import test_nes_repeat227_snes as prior
import nes_sparse232
from nes_delta231 import materialize,once


def prepare232(common):materialize(common)


def body232(body):
 s=prior.body227(body)
 s='#include "nes_delta231.h"\nstatic struct nes_dirty231 dirty;\n'+s
 s=once(s,' source(variant<8?variant:2,gen);',' if(gen==2&&(!strcmp(mode,"raw_align")||!strcmp(mode,"missing_raw")))variant=3;\n source(variant<8?variant:2,gen);')
 s=s.replace('nes_native_video211_plan(&input,lut,&candidate,&cache)','nes_native_video231_plan(&input,lut,&candidate,&cache,&dirty)')
 s=s.replace('nes_sink212_seal(&sink,&candidate,&cache)','nes_sink231_seal(&sink,&candidate,&cache,&dirty)')
 s=once(s,'cache.map_upload&=~(UINT64_C(1)<<63);','dirty.stale[cache.target][31]&=127;')
 s=once(s,' if(gen==1&&!strcmp(mode,"pressure")){',' if(gen==2&&!strcmp(mode,"missing_raw"))dirty.stale[cache.target][36]&=254;\n if(gen==2&&!strcmp(mode,"missing_palette"))memset(dirty.stale[cache.target]+32,0,4);\n if(gen==1&&!strcmp(mode,"pressure")){')
 return once(s,'nes_resident211_reset(&cache);','nes_resident211_reset(&cache);nes_dirty231_reset(&dirty);')


s=prior.s
s=once(s,'prepare227(common)','prepare232(common)')
s=once(s,'body=body227(', 'body=body232(')
s=once(s,"  nes_sink212.prepare(d)\n  if typ=='candidate':sink227(d)","  # common already contains231 candidate sources")
s=once(s,"'nes_sink_trace168.c']","'nes_sink_trace168.c','nes_delta231.c']")
s=once(s,"nes_repeat227.build(out/'client')","nes_sparse232.build(out/'client')")
s=once(s,'tracked=[',"tracked=[prior.ROOT/'tools/nes_sparse232.py',")
s=once(s," lua=once(lua,needle,injection+needle)", """ lua=once(lua,needle,injection+needle)
 lua=once(lua,\"  if pb(0)==3 and MODE=='missing_slot' then\",\"\"\"  if pb(0)==3 and MODE=='bad_dirty' then b[185]=b[185]~1 end
  if pb(1)==5 and pb(0)==2 and pw(10)>=1121 and MODE=='raw_align' then b[11]=b[11]~1 end
  if pb(1)==3 and pw(10)>0 and MODE=='duplicate_cgram' then b[11]=0;b[12]=0 end
  if pb(0)==3 and MODE=='missing_slot' then\"\"\")""")
ns=dict(prior.ns);ns.update(__file__=__file__,__doc__=__doc__,prior=prior,prepare232=prepare232,body232=body232,nes_sparse232=nes_sparse232)
exec(compile(s,'sparse232-snes','exec'),ns)
if __name__=='__main__':ns['main']()
