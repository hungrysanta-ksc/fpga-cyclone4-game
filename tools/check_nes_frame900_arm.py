"""Exercise the installed record format, window limits, E0 validation and FatFS writes."""
import json
import struct
import sys
from types import SimpleNamespace
from unittest.mock import patch

import check_nes_windows518 as windows
from check_nes_frame862_arm import TimedProbe,UC_HOOK_CODE,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
from check_nes_game478 import ELFFile
from prepare_nes_frame900 import WORK
from read_nes_frame900 import ROW,read_trace


def verify(n,src=None,out=None,*,short_header=False,marker_values=(384,410,411,412)):
    src=src or WORK/f'link{n}/src'
    out=out or WORK/f'proof{n}'
    row_type,decoder,capacity=ROW,read_trace,194
    if n==903:
        from read_nes_tile903 import ROW as row_type, decode as decoder
        capacity=151
    if n in (905,907,915,925,950):
        from read_nes_supply905 import ROW as row_type, decode, CAP as capacity
        direct_probe=n==915 and 'step_begin915' not in (src/'nes_budget210.c').read_text()
        decoder=lambda path:decode(path,n,direct_probe=direct_probe)
    if n==927:
        from read_nes_display927 import ROW as row_type, CAP as capacity, decode as decoder
    class WindowMachine(windows.Machine):
        def __init__(self,*args):
            super().__init__(*args)
            self.u.mem_map(0xe0001000,0x1000)
            with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
                sym,=ELFFile(f).get_section_by_name('.symtab').get_symbol_by_name('mode900')
                self.u.mem_write(sym['st_value'],b'\x03')
    with patch.object(windows,'Machine',WindowMachine):
        result=windows.run(SimpleNamespace(arm=src,layout='demo'))
    (out/'windows.json').write_text(json.dumps(result))
    for mode in (0,1,2,3):
        q=TimedProbe(src)
        scratch=q.data['ptrcache'];at=0x20012000
        for name,value in zip(('MMC3','EARLY','LATE','CONTROL'),marker_values,strict=True):
            q.u.mem_write(at,f'NES {name} {n}.nh1'.encode()+b'\0')
            assert q.call('marker_geometry',[at])==value
        q.u.mem_write(q.data['mode900'],bytes([mode]))
        q.call('nes_budget210_reset',[])
        g=0x1234
        q.put(q.video,'nes_native_video165','generation',g,2)
        def time(t):q.u.mem_write(0xe0001004,struct.pack('<I',t))
        time(100000);q.call('input900',[g]);time(120000);q.call('input900',[g+2])
        # Same parity, different generations. The previous completion is still available.
        s=q.rt+q.layout['nes_native_runtime165']['transport']
        for k,v,width in [('sent',1,2),('retired',0,2),('ever_sent',1,1)]:q.put(s,'nes_sink_window184',k,v,width)
        identity=bytes.fromhex('03000100020000003412')
        q.u.mem_write(s+q.layout['nes_sink_window184']['last'],identity)
        ack=bytearray(20);ack[2]=2;ack[4]=ack[6]=1
        ack[7:19]=bytes([1])+identity[:1]+identity[2:]+bytes([0x65,0x9a])
        q.status_override=ack;time(150000)
        assert q.call('nes_window184_through',[s,at,1])
        time(180000)
        def bulk(cpu,pc,size,_):
            length=cpu.reg_read(UC_ARM_REG_R3)
            assert mode!=3 and length==(16 if short_header else 32 if n in (905,907,915,925,927,950) else 26)
            tx=cpu.reg_read(UC_ARM_REG_R1)
            assert 0x20000000<=tx<0x20010000 and cpu.mem_read(tx,1)==b'\x78'
            wire=bytes([0,0x90,255,0x34,0x12])+struct.pack('<10H',8000,8050,8800,9300,9400,9450,3939,8100,8200,9600)+bytes(1)
            if n==903:
                wire=struct.pack('<BBBH8HIB',0,0x93,3,g,3940,0,0,0,0,0,9400,9600,0,0)
            if n in (905,907,915,925,950):
                wire=struct.pack('<BBHBBHHHI',0,0x95,g,0,0,120,122,120,0)+bytes(16)
            if n==927:
                wire=struct.pack('<BBHBBH8H',0,0x97,g,0x7f,0x38,10,100,110,115,130,140,150,160,105)+bytes(8)
            cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),wire[:length]);q.ret(cpu,1)
        pc=q.syms['nes_native165_bulk'];q.u.hook_add(UC_HOOK_CODE,bulk,None,begin=pc,end=pc)
        if n==927:
            q.call('block927',[g,100,50,25])
            q.u.mem_write(q.data['advance927'],bytes([1]))
            q.call('block927',[g,30,20,10])
            q.u.mem_write(q.data['advance927'],bytes([0]))
        for tick in (2999,3000,3499,3500,5499,5500,5999,6000):
            q.call('nes_budget210_frame',[tick]);q.call('nes_budget210_display',[tick,q.video])
        q.u.mem_map(0xe000e000,0x1000)
        files={}
        def io(cpu,pc,size,name):
            if name=='f_open':
                io.path=bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),96)).split(b'\0')[0].decode()
                files[io.path]=bytearray()
            elif name=='f_write':
                length=cpu.reg_read(UC_ARM_REG_R2)
                files[io.path].extend(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),length))
                cpu.mem_write(cpu.reg_read(UC_ARM_REG_R3),struct.pack('<I',length))
            q.ret(cpu,0)
        for name in ('f_open','f_write','f_close','printf'):
            pc=q.syms[name];q.u.hook_add(UC_HOOK_CODE,io,name,begin=pc,end=pc)
        q.u.mem_write(at,b'PREPARED_RESET_HELD\0')
        q.call('save_report',[at,0]);assert not files
        q.call('save_report',[at,1])
        raw=out/f'mode{mode}.bin'
        raw.write_bytes(files[f'/sd2snes/nes-frame-mmc{n}.bin'])
        run=decoder(raw);rows=run['rows']
        ticks=[t for t in (3000,3499,5500,5999) if not (mode==1 and t>=5500 or mode==2 and t<5500)]
        if n in (903,905,907,915,925,927,950):
            ticks=[3000,3499] if mode==1 else [5500,5999]
        if n in (907,915,925,927,950):assert run['displayed55']==2
        if n==927:
            assert run['bins'][0]['foreground']==(100,50,25,1)
            assert run['bins'][0]['prefetch']==(30,20,10,1)
            assert all(r['foreground_cycles']==[100,50,25] and r['prefetch_cycles']==[30,20,10] for r in rows)
        assert [r['tick'] for r in rows]==ticks and all(r['bank']==1 and 'invalid' not in r for r in rows)
        assert all(row_type.unpack_from(raw.read_bytes(),16+i*row_type.size)[3:5]==(156,58) for i in range(len(rows)))
        # A full buffer must count the omitted row, without overwriting any payload.
        q.u.mem_write(scratch+6,struct.pack('<H',capacity))
        before=bytes(q.u.mem_read(scratch+16,8176))
        tick=ticks[0];q.call('nes_budget210_frame',[tick]);q.call('nes_budget210_display',[tick,q.video])
        expected=bytearray(before)
        if n in (907,915,925,927,950) and 5500<=tick<6000:
            if n==927:
                from read_nes_display927 import DISPLAYED as SIZE
            else:
                from read_nes_supply905 import SIZE
            position=SIZE-16
            count=struct.unpack_from('<H',before,position)[0]
            struct.pack_into('<H',expected,position,count+1)
        assert bytes(q.u.mem_read(scratch+16,8176))==expected
        assert sum(struct.unpack('<2H',q.u.mem_read(scratch+8,4)))==1
    q=TimedProbe(src)
    s=q.rt+q.layout['nes_native_runtime165']['transport']
    for k,v,width in [('sent',1,2),('retired',0,2),('ever_sent',1,1)]:q.put(s,'nes_sink_window184',k,v,width)
    q.u.mem_write(s+q.layout['nes_sink_window184']['last'],identity)
    ack[15]^=1
    q.status_override=ack
    assert not q.call('nes_window184_through',[s,at,1])
    assert not int.from_bytes(q.u.mem_read(q.data['ack900']+6,2),'little')
    print('PASS windows, markers, two pending generations, four file modes, capacity, guarded report')

if __name__=='__main__':verify(int(sys.argv[1]))
