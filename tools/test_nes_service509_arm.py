# SPDX-License-Identifier: MIT
"""Compare linked508/509 E8 phase/error precedence and exact SPI transcript."""
import argparse,json
from pathlib import Path
from check_nes_supply485_arm import ARM,Endpoint,crc,sha,ELFFile
class Inject(Endpoint):
    def __init__(self,phase,mutation):super().__init__('normal');self.phase=phase;self.mutation=mutation;self.injected=False
    def exchange(self,tx,clock):
        r=bytearray(super().exchange(tx,clock))
        eligible=(self.rearmed if self.phase=='REARM'else not self.rearmed)
        if tx[0]!=0xe8 or not eligible or self.injected:return bytes(r)
        self.injected=True;k=self.mutation
        if k=='header':r[1]^=1
        if k in ['reserved','reserved_crc','header_reserved_crc']:r[18]=1
        if k=='header_reserved_crc':r[1]^=1
        if k=='flags':r[3]|=4
        if k=='count':r[5]^=1
        if k=='descriptor':r[6]=2
        if k=='empty':r[7]=1
        r[19]=crc(r[1:19],8,7,0)
        if k in ['crc','reserved_crc','header_reserved_crc']:r[19]^=1
        return bytes(r)
def run(src,phase,mutation):
    m=ARM(src,'normal');m.endpoint=Inject(phase,mutation);m.setup()
    if phase=='FLUSH':ok=m.emit(0,1,4)
    else:
        m.endpoint.end=True
        for k,v,n in [('started',1,1),('ending',1,1),('generation',907,2)]:m.put(m.p,'nes_plan200',k,v,n)
        if phase=='FINISH':ok=m.call('nes_plan200_progress',[m.p,1])
        else:
            m.put(m.p,'nes_plan200','finished',1,1)
            for k,v,n in [('state',0,1),('displayed',1,1),('last_generation',907,2)]:m.put(m.s,'nes_native_sink165',k,v,n)
            ok=m.call('nes_plan200_retire',[m.p])
    assert m.endpoint.injected
    return dict(ok=ok,error=m.get(m.p,'nes_plan200','error'),diagnostic=bytes(m.u.mem_read(m.data_symbols['nes_plan215'],30)).hex(),SPI=m.endpoint.calls)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['baseline','candidate','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
    for src in [a.baseline,a.candidate]:
        with (src/'obj-nes-100/sd2snes.elf').open('rb')as f:
            assert next(s['st_size']for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()if s.name=='nes_plan215')==30
    for phase in ['FLUSH','FINISH','RETIRE','REARM']:
        for mutation in ['none','header','reserved','crc','reserved_crc','header_reserved_crc','flags','count','descriptor','empty']:
            b=run(a.baseline,phase,mutation);c=run(a.candidate,phase,mutation);assert b==c,(phase,mutation,b,c)
            if mutation=='none':assert c['ok']==1,(phase,c)
            rows.append(dict(phase=phase,mutation=mutation,ok=c['ok'],error=c['error'],diagnostic=c['diagnostic'],SPI_calls=len(c['SPI'])))
    r=dict(passed=True,scope=__doc__,cases=len(rows),diagnostic_size_B=30,baseline_SHA256=sha(a.baseline/'obj-nes-100/firmware.stm'),candidate_SHA256=sha(a.candidate/'obj-nes-100/firmware.stm'),rows=rows)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS509',len(rows),'phase/error/SPI equivalence cases')
