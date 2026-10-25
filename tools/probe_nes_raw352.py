# SPDX-License-Identifier: MIT
"""338 RTL, changed-group material comparison on336 ARM; decoder unchanged."""
import shutil,csv,json
import probe_nes_ingress338 as previous
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM,crc
from nes_raw352 import native
engine=previous.engine
old_prepare=engine.prepare
def prepare(*a,**k):
    src,pins=old_prepare(*a,**k);d=a[0]
    evidence=BASE/'probes/nes-raw352/decoder01'
    rows=list(csv.DictReader((evidence/'blocks.csv').open()))
    for name,field in [('source-cost280.hex','instructions'),('source-length280.hex','length')]:
        (d/name).write_text(' '.join(f'{int(r[field]):08x}' for r in rows)+'\n')
    c=json.loads((evidence/'control.json').read_text())
    (d/'control280.hex').write_text(' '.join(f'{r["instructions"]:08x}' for r in c['cases'])+f' {c["complete_instructions"]:08x}\n')
    arm=ARM(evidence/'decoder.elf',None);costs=[]
    for token,row in enumerate(rows):
        for flags in (0,1,3):
            before=arm.instructions;assert arm.call('prefix280',[0x20018000,token,int(row['frame'])-904,flags])==1
            costs.append(arm.instructions-before)
        for ready in (0,1):
            header=bytes([0xaa|ready,int(row['length']) if ready else 0,token>>8,token&255])
            arm.uc.mem_write(0x20018000,header+bytes([crc(header,8)]));before=arm.instructions
            assert arm.call('reply280',[0x20018000,token])==1;costs.append(arm.instructions-before)
    (d/'transaction-cost280.hex').write_text(' '.join(f'{v:08x}' for v in costs)+'\n')
    for name in ('blocks.csv','control.json','decoder.elf','nes_decode280.c'):
        shutil.copyfile(evidence/name,d/('source-ARM-'+name));pins['source-ARM-'+name]=sha(evidence/name)
    for n in ('nes_raw352.py','probe_nes_raw352.py','probe_nes_rawdecode352.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
old_init=engine.ARM296.__init__
def observed_init(self,*a,**k):
    old_init(self,*a,**k)
    for n in ('nes_dirty231_material','nes_dirty231_begin'):
        if n in self.symbols:self.watch317[self.symbols[n]&~1]=n
engine.ARM296.__init__=observed_init
old_call=engine.ARM296.call
def observed_call(self,name,args):
    if name=='input_commit286':
        serial=int.from_bytes(self.uc.mem_read(self.symbols['receiver280']+4,4),'little')
        (self.endpoint.d/f'precommit352-{serial}.bin').write_bytes(bytes(self.uc.mem_read(0x20000000,0x40000)))
    return old_call(self,name,args)
engine.ARM296.call=observed_call
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
