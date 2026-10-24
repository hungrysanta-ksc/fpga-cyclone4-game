# SPDX-License-Identifier: MIT
"""Actual N5-v3 RTL source and M4 BG view/first prefix with retained338 checks."""
import csv,json,shutil
import probe_nes_ingress338 as previous
from nes_hybrid340 import apply,native,host
from nes_delta231 import BASE,ROOT,once,sha
from probe_nes_decode280 import chunks,records
from probe_nes_arm264 import ARM,crc
engine=previous.engine
old_prepare=engine.prepare

def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0];apply(d);host(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'if(dut.core.in_offset!=seen||dut.core.in_data!==expected[seen])', 'if(dut.core.in_offset>=4398||dut.core.in_data!==expected[dut.core.in_offset])')
    p.write_text(s,newline='\n')
    p=d/'nes_bridge267.c';s=p.read_text()
    s=once(s,'while(!(f=fopen(path,"r"))) {', 'while(!(f=fopen(path,"r"))) { FILE *err=fopen("arm-error340","r");if(err){fclose(err);return fail267();}')
    p.write_text(s,newline='\n')
    evidence=BASE/'probes/nes-hybrid340/arm03'
    rows=list(csv.DictReader((evidence/'blocks.csv').open()))
    for name,field in [('source-cost280.hex','instructions'),('source-length280.hex','length')]:
        (d/name).write_text(' '.join(f'{int(r[field]):08x}' for r in rows)+'\n')
    blob=b''.join(b for f in range(905,976) for b in chunks(records(evidence/f'frame{f}.records')))
    (d/'source-expected280.hex').write_text(blob.hex(' ')+'\n')
    c=json.loads((evidence/'control.json').read_text())
    (d/'control280.hex').write_text(' '.join(f'{r["instructions"]:08x}' for r in c['cases'])+f' {c["complete_instructions"]:08x}\n')
    arm=ARM(evidence/'decoder.elf',None);costs=[]
    for token,row in enumerate(rows):
        for flags in (0,1,3):
            before=arm.instructions
            assert arm.call('prefix280',[0x20018000,token,int(row['frame'])-904,flags])==1
            costs.append(arm.instructions-before)
        for ready in (0,1):
            header=bytes([0xaa|ready,int(row['length']) if ready else 0,token>>8,token&255])
            arm.uc.mem_write(0x20018000,header+bytes([crc(header,8)]));before=arm.instructions
            assert arm.call('reply280',[0x20018000,token])==1
            costs.append(arm.instructions-before)
    (d/'transaction-cost280.hex').write_text(' '.join(f'{v:08x}' for v in costs)+'\n')
    for name in ('blocks.csv','control.json','decoder.elf','nes_decode280.c'):
        shutil.copyfile(evidence/name,d/('source-ARM-'+name));pins['source-ARM-'+name]=sha(evidence/name)
    for name in ('nes_hybrid340.py','probe_nes_joint340.py'):
        shutil.copyfile(ROOT/'tools'/name,d/name);pins[name]=sha(d/name)
    return src,pins

engine.prepare=prepare
engine.native=native
old_worker=engine.worker
def worker(*args,**kwargs):
    try:return old_worker(*args,**kwargs)
    except BaseException as e:
        (args[0]/'arm-error340').write_text(repr(e));raise
engine.worker=worker
engine.__file__=__file__
if __name__=='__main__':engine.main()
