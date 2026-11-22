"""Check post-STOP reports and the two lengths of the passive SPI query."""
from check_nes_frame862_arm import TimedProbe, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


def reports(src):
    q=TimedProbe(src)
    at=0x20012000
    q.u.mem_map(0xe000e000,0x1000)
    files={}
    def intercept(cpu,pc,size,name):
        if name=='f_open':
            intercept.name=bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),96)).split(b'\0')[0].decode()
            files[intercept.name]=bytearray()
        elif name=='f_write':
            n=cpu.reg_read(UC_ARM_REG_R2)
            files[intercept.name].extend(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),n))
            cpu.mem_write(cpu.reg_read(UC_ARM_REG_R3),n.to_bytes(4,'little'))
        q.ret(cpu,0)
    for name in ('f_open','f_write','f_close','printf'):
        pc=q.syms[name]
        q.u.hook_add(UC_HOOK_CODE,intercept,name,begin=pc,end=pc)
    q.u.mem_write(at,b'PREPARED_RESET_HELD\0')
    q.call('save_report',[at,1])
    assert any('game-last' in name for name in files)
    bounded=[]
    for n in (0,1,2,39,40,41,42,43,200):
        q.u.mem_write(at,b'\xa5'*208)
        q.u.mem_write(at+256,bytes(range(20)))
        ret=q.call('nes_hexline512',[at,n,0,at+256,20])
        bounded.append((ret,bytes(q.u.mem_read(at,208))))
    return files,bounded


def check(base,link):
    old,bounds=reports(base)
    new,limits=reports(link)
    assert old==new and bounds==limits
    q=TimedProbe(link)
    at=0x20012000
    query=[]
    def bulk(cpu,pc,size,_):
        tx=cpu.reg_read(UC_ARM_REG_R1)
        dst=cpu.reg_read(UC_ARM_REG_R2)
        n=cpu.reg_read(UC_ARM_REG_R3)
        assert 0x20000000<=tx<0x20010000 and dst==at
        query.append((bytes(cpu.mem_read(tx,2)),n))
        cpu.mem_write(dst,bytes(range(n)))
        q.ret(cpu,1)
    pc=q.syms['nes_native165_bulk']
    q.u.hook_add(UC_HOOK_CODE,bulk,None,begin=pc,end=pc)
    for page,n in ((256,16),(0,32),(128,32)):
        q.u.mem_write(at,b'\xa5'*40)
        assert q.call('page905',[at,page])==1
        assert bytes(q.u.mem_read(at,40))==bytes(range(n))+b'\xa5'*(40-n)
    assert query==[(bytes((0x78,p)),n) for p,n in ((0,16),(0,32),(128,32))]
    return dict(identical_files={k:len(v) for k,v in old.items()},
                bounded_hex_cases=len(bounds),SPI_lengths=[n for _,n in query])
