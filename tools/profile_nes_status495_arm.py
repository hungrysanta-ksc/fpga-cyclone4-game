# SPDX-License-Identifier: MIT
"""Read-only493 linked receive/planner instruction attribution on pinned905..907.

SPI and tile writer are stubs; counts are not hardware cycles or full RUN time.
"""
import argparse,bisect,json,re,struct
from collections import Counter
from pathlib import Path
from check_nes_game478 import Machine,ELFFile,encode,sha

class Profile(Machine):
    def __init__(self,src,palette):
        self.stage=None;self.counts={};super().__init__(src,palette)
        with (src/'obj-nes-100/sd2snes.elf').open('rb')as f:
            e=ELFFile(f);self.fn=sorted((s['st_value']&~1,s['st_size'],s.name)for s in e.get_section_by_name('.symtab').iter_symbols()if s['st_info']['type']=='STT_FUNC'and s['st_size'])
        self.starts=[x[0]for x in self.fn]
    def hook(self,u,at,size,user):
        if self.stage and hasattr(self,'fn'):
            i=bisect.bisect_right(self.starts,at)-1
            if i>=0:
                a,n,name=self.fn[i]
                if at<a+n:self.counts[self.stage][name+'@'+hex(a)]+=1
        super().hook(u,at,size,user)
    def call(self,name,args):
        old=self.stage
        if name in ['nes_native165_prepare','nes_native165_poll']:self.stage='receive'
        elif name=='nes_native_video211_plan':self.stage='planner'
        q=super().call(name,args);self.stage=old;return q
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','dataset','reference','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();ref=json.loads((a.reference/'result.json').read_text())
    nums=map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(','));m=Profile(a.arm,struct.pack('<64H',*nums));rows=[];pins={}
    for serial,frame in enumerate(range(905,908),1):
        paths=[a.dataset/f'frame{frame}.{ext}'for ext in ['geometry','raw']]
        for f in paths:assert sha(f)==ref['input_SHA256'][f.name];pins[f.name]=sha(f)
        geom,raw=[f.read_bytes()for f in paths];packets,_,_=encode(geom,raw,frame);m.counts={'receive':Counter(),'planner':Counter()};r=m.frame(packets,geom,raw,frame,serial)
        rows.append({'frame':frame,'receive_instructions':r['receive_instructions'],'planner_instructions':r['planner_instructions'],'counts':{k:dict(v)for k,v in m.counts.items()}})
    r={'scope':__doc__,'rows':rows,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),'input_SHA256':pins}
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'frames':len(rows),'physical_time':False}))
