"""Check window edges, sampling capacity and serialized files on the linked debug ARM."""
import json
import struct
from pathlib import Path
from check_ff3_sd1043 import Machine, fat16, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR
from prepare_nes_pair1054 import WORK
from read_nes_kirby1034 import decode
from read_nes_ingress1029 import SIZE,HEADER,ROW

m=Machine(WORK/'debug/link/src',fat16())
u=m.u
files={}
active=None
def hook(u,pc,size,name):
    global active
    a,b,c,d=(u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
    result=0
    if name=='f_open':
        active=bytes(u.mem_read(b,80)).split(b'\0')[0].decode()
    elif name=='f_write':
        assert active not in files
        files[active]=bytes(u.mem_read(b,c))
        u.mem_write(d,struct.pack('<I',c))
    elif name=='f_close':
        active=None
    u.reg_write(UC_ARM_REG_R0,result)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
u.mem_map(0xe000e000,4096)
for name in ('page905','nes_cost471_now','f_open','f_write','f_close'):
    a=m.sym[name]&~1
    u.hook_add(UC_HOOK_CODE,hook,name,a,a)
m.call('nes_budget210_reset')
ticks=[99,100,1499,1500,2999,3000,4499,4500,5499,*range(5500,5750,10),*range(5750,6000,5),5999,6000]
for tick in ticks:
    m.call('nes_budget210_frame',tick)
    m.call('nes_budget210_display',tick,0x08050000)
u.mem_write(0x0807fe00,b'PREPARED_RESET_HELD\0')
m.call('save_report',0x0807fe00,1)
text=files['/sd2snes/nes-game-last-debug1054.txt'].decode()
windows=[sum(100<=x<3000 for x in ticks),sum(3000<=x<6000 for x in ticks)]
assert f'w1={windows[0]} w2={windows[1]}' in text,text
blob=files['/sd2snes/nes-frame-debug1054.bin']
assert len(blob)==SIZE
magic,edition,mode,used,d1,d2,size,capacity=HEADER.unpack_from(blob)
assert (magic,edition,mode,used,d1,d2,size,capacity)==(0x9001,1054,0,79,0,0,60,80)
assert ROW.unpack_from(blob,HEADER.size+(used-1)*60)[0]==5995
assert len(decode(blob,1054)['rows'])==79
baseline=[]
for p in sorted((Path.home()/'Downloads').glob('nes-frame-mmc1035-*.bin')):
    rows=decode(p.read_bytes(),1035)['rows']
    paired=[r for r in rows if 'banks' in r]
    assert paired and all('show_tick' in r and 'SEAL_tick' in r and 'final_ACK_tick' in r for r in paired)
    baseline.append(len(paired))
assert len(baseline)==2
report=dict(windows=windows,capacity=capacity,used=used,drop=0,paired_historic_samples=baseline)
(WORK/'debug/windows.json').write_text(json.dumps(report,indent=2))
print(report)
