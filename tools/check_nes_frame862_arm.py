"""Check the final ARM links, exact gate/receipt, file bytes, and recovery paths."""
import argparse
import struct
from pathlib import Path
from check_nes_longrun693 import Probe,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2
from check_nes_game478 import UC_ARM_REG_R3,UC_HOOK_CODE
from check_nes_longrun692 import run as timer_cases
from package_nes_trial704 import checked,save
from package_nes_trial855 import loader
from prepare_nes_frame862 import WORK
from read_nes_frame862 import decode,compare


class TimedProbe(Probe):
    def call(self,name,args):
        if name=='nes_runtime165_begin':
            args=list(args);args[8]=6000
        return super().call(name,args)


def verify(temp,n,rom):
    out=WORK/'delivery'/f'proof{n}'
    out.mkdir(exist_ok=True)
    src=WORK/f'delivery/build{n}/src'
    resp=bytes.fromhex((temp/'nes-frame862-wire/receipt.hex').read_text())
    for bad,control in ((True,False),(False,True),(False,False)):
        q=TimedProbe(src)
        marker=f'NES CONTROL {n}.nh1' if control else f'NES MMC3 {n}.nh1'
        q.u.mem_write(0x20012000,marker.encode()+bytes(1))
        assert q.call('marker_geometry',[0x20012000])==(387 if control else 384)
        q.u.mem_write(q.data['control862'],bytes([control]))
        q.call('nes_budget210_reset',[])
        def word(name,width):return int.from_bytes(q.u.mem_read(q.data[name],width),'little')
        for tick in (3499,3500):
            q.call('nes_budget210_frame',[tick])
            assert bool(word('row862',4))==(tick==3500)
            if tick==3499:q.call('nes_budget210_display',[tick,q.video])
        row=word('row862',4);gen=0x23fe
        q.u.mem_write(row+25,bytes([168]))
        s=q.rt+q.layout['nes_native_runtime165']['transport']
        for f,v,size in [('sent',1,2),('retired',0,2),('ever_sent',1,1)]:
            q.put(s,'nes_sink_window184',f,v,size)
        identity=bytes.fromhex('0300010001000000fe23')
        q.u.mem_write(s+q.layout['nes_sink_window184']['last'],identity)
        ack=bytearray(20);ack[2]=2;ack[4]=ack[6]=1
        ack[7:19]=bytes([1])+identity[:1]+identity[2:]+bytes([0x64 if bad else 0x65,0x9a])
        q.status_override=ack
        q.u.mem_write(0xe0001004,struct.pack('<I',2100000))
        result=q.call('nes_window184_through',[s,0x20011ff0,1])
        assert bool(result)!=bad and q.u.mem_read(row+26,1)[0]==int(not bad)
        if bad:continue
        q.u.mem_write(row+8,struct.pack('<I',2140000))
        q.put(q.video,'nes_native_video165','generation',gen,2)
        def spi(cpu,at,size,_):
            assert not control and cpu.reg_read(UC_ARM_REG_R3)==44 and cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),1)[0]==0x78
            cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),resp)
            q.ret(cpu,1)
        pc=q.syms['nes_native165_bulk']
        q.u.hook_add(UC_HOOK_CODE,spi,begin=pc,end=pc)
        q.call('nes_budget210_display',[3501,q.video])
        q.call('nes_budget210_frame',[4000]);assert not word('row862',4)
        q.u.mem_map(0xe000e000,0x1000)
        files={}
        def io(cpu,at,size,name):
            if name=='f_open':
                io.name=bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),96)).split(b'\0')[0].decode()
                files[io.name]=bytearray()
            elif name=='f_write':
                length=cpu.reg_read(UC_ARM_REG_R2)
                files[io.name].extend(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),length))
                cpu.mem_write(cpu.reg_read(UC_ARM_REG_R3),struct.pack('<I',length))
            q.ret(cpu,0)
        for name in ('f_open','f_write','f_close','printf'):
            pc=q.syms[name];q.u.hook_add(UC_HOOK_CODE,io,name,begin=pc,end=pc)
        q.u.mem_write(0x20012000,b'PREPARED_RESET_HELD\0')
        q.call('save_report',[0x20012000,0]);assert not files
        q.call('save_report',[0x20012000,1])
        raw=out/('sample-control.bin' if control else 'sample.bin')
        raw.write_bytes(files[f"/sd2snes/nes-frame-{'ctl' if control else 'mmc'}{n}.bin"])
        data=decode(raw);r,=data['rows']
        assert r['gen']==gen and 'invalid' not in r ,r
        assert data['control']==control and (control or r['boundary']=='map -> raw' and r['gaps']==1)
        assert compare(data,data,(1,1,1))['total_delta_ms']==0
    save(out/'timer.json',timer_cases(src))
    loader(rom,src,n,out)
    for name,script,args in [
        ('menu','check_nes_menu533.py',['--trial',n]),
        ('base','check_nes_transfer512_recovery.py',['--trial',n,'--fault','none']),
        ('windows','check_nes_windows518.py',['--layout','demo'])]:
        checked(script,['--arm',src,*args,'--out',out/('base' if name=='base' else name+'.json')],out/(name+'.log'))
    save(out/'wire-arm.json',dict(edition=n,identity_fault_rejected=True,window=[3500,4000],
                                 files=sorted(files),decoded_gap=r['boundary'],hardware=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('temp',type=Path);p.add_argument('edition',type=int)
    p.add_argument('rom',type=Path);a=p.parse_args();verify(a.temp,a.edition,a.rom)
