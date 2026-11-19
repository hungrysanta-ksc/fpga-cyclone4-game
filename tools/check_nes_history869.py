"""Measure in-place ACK history maintenance on the ARM with exact published maps."""
import argparse
import json
import struct
from pathlib import Path

from cost_nes_strip868 import GCC, KernelARM, ROOT, run, ELFFile
from probe_nes_map868 import phase_cases

HIST, ARGS, MAP = 0x20008000,0x20000100,0x20001000
SIZE = 1368


def decode(hist,bank):
    _,s0,s1,mask=struct.unpack_from('<IIII',hist)
    assert (s0,s1)[bank] and mask.bit_count()==2
    result=bytearray(2944)
    for j in range(64):
        col=hist[144+64*bank+j]
        assert col<52
        for row in range(23):
            entry=row-(mask & ((1<<(row+1))-1)).bit_count()
            color=hist[272+21*col+entry]
            assert color<hist[1364]
            off=(j//32)*1472+row*64+j%32*2
            result[off:off+2]=hist[16+2*color:18+2*color]
    return bytes(result)


def verify(temp, work, out):
    work.mkdir(parents=True,exist_ok=False)
    image=ROOT.parent/'probes/nes-trial866/link/src/obj-nes-100/sd2snes.elf'
    with image.open('rb') as f:
        e=ELFFile(f)
        syms=e.get_section_by_name('.symtab')
        defs=[f"{name} = {syms.get_symbol_by_name(name)[0]['st_value']};" for name in ('memset','memcpy','memcmp')]
        flash=[(s['p_vaddr'],s.data()) for s in e.iter_segments()
               if s['p_type']=='PT_LOAD' and 0x08000000<=s['p_vaddr']<0x08050000]
    (work/'layout.ld').write_text('SECTIONS { . = 0x08058000; .text : { *(.text*) *(.rodata*) } }\n'+'\n'.join(defs))
    run([GCC/'arm-none-eabi-gcc.exe','-mcpu=cortex-m4','-mthumb','-Os','-nostdlib',
         '-fstack-usage','-Wall','-Werror','-Wl,-T,layout.ld',ROOT/'tools/nes_history869.c',
         '-o','history.elf'],work,'build')
    with (work/'history.elf').open('rb') as f:
        sym=ELFFile(f).get_section_by_name('.symtab')
        sizes={s.name:s['st_size'] for s in sym.iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_size']}
    cpu=KernelARM(work/'history.elf')
    for at,payload in flash:cpu.uc.mem_write(at,payload)
    fixture=temp/'nes-tile821-demo-jointmirror-p1-866-on'
    cases,_=phase_cases(fixture,True)
    # Size-control policy selects at most one page. The other page at g950
    # is sent as ordinary rows and must also update the published history.
    strips={c['g']:c for c in cases}
    maps={g:(fixture/f'map-{g}.bin').read_bytes() for g in range(905,967)}
    ordinary={g:[0,0] for g in maps}
    for line in (fixture/'packets.jsonl').read_text().splitlines():
        raw=bytes.fromhex(json.loads(line)[2])
        if raw[1]!=2 or raw[0] not in (2,4):continue
        g=int.from_bytes(raw[8:10],'little')
        at=int.from_bytes(raw[10:12],'little')
        size=len(raw)-16 if raw[0]==2 else int.from_bytes(raw[14:16],'little')
        for row in range(at//64,(at+size-1)//64+1):
            if row%32<23 and (g not in strips or row//32*2048!=strips[g]['page']):
                ordinary[g][row//32]|=1<<(row%32)
    def published(g,mode,page=0,col=0,count=0,data=None,epoch=1):
        buf=maps[g] if data is None else data
        cpu.uc.mem_write(MAP,buf)
        bank=(g-905)%2
        cpu.uc.mem_write(ARGS,struct.pack('<IIIHHHHIII',epoch,g-904,MAP,page,col,count,bank,mode,*ordinary[g]))
        before=cpu.instructions
        ok=cpu.call('publish869',[HIST,ARGS])
        h=bytes(cpu.uc.mem_read(HIST,SIZE))
        serial=struct.unpack_from('<II',h,4)
        if ok:
            expected=buf[:1472]+buf[2048:3520]
            restored=decode(h,bank)
            assert serial[bank]==g-904 and restored==expected,(g,mode,page,col,count,serial,
                next((i for i,(a,b) in enumerate(zip(restored,expected)) if a!=b),None))
        else:
            assert not serial[bank]
        assert cpu.uc.mem_read(HIST+SIZE,8)==b'abcdefgh'
        return ok,cpu.instructions-before,h

    cpu.uc.mem_write(HIST+SIZE,b'abcdefgh')
    rows=[]
    for g in maps:
        bank=(g-905)%2
        old=bytes(cpu.uc.mem_read(HIST,SIZE))
        serial=struct.unpack_from('<II',old,4)
        both=bool(serial[0] and serial[1])
        c=strips.get(g)
        mode=2 if g<907 or not both else (1 if c else 0)
        packet=bytes.fromhex(c['data']) if c else bytes(8)
        col=int.from_bytes(packet[6:8],'little')//2
        count=(len(packet)-8)//46
        send=[]
        for cand in (x for x in cases if x['g']==g):
            cpu.uc.mem_write(MAP,maps[g])
            cpu.uc.mem_write(ARGS,struct.pack('<IIIHHHHIII',1,g-904,MAP,cand['page'],0,0,bank,0,0,0))
            start=cpu.instructions
            n=cpu.call('prepare869',[HIST,ARGS,0x20006000])
            payload=bytes(cpu.uc.mem_read(0x20006000,n))
            assert payload==struct.pack('<I',g-906)+bytes.fromhex(cand['data'])[4:]
            assert old==bytes(cpu.uc.mem_read(HIST,SIZE))
            send.append(dict(page=cand['page'],instructions=cpu.instructions-start))
        ok,cost,h=published(g,mode,c['page'] if c else 0,col,count)
        if serial[1-bank]:
            assert decode(h,1-bank)==decode(old,1-bank)
        rows.append(dict(g=g,mode=mode,other_rows=ordinary[g],prepare=send,
                         strip_usable=bool(c and both),ok=ok,instructions=cost))
    before=bytes(cpu.uc.mem_read(HIST,SIZE))
    cpu.call('stop869',[HIST])
    assert bytes(cpu.uc.mem_read(HIST+4,8))==bytes(8)
    assert cpu.call('prepare869',[HIST,ARGS,0x20006000])==0
    assert published(905,0,epoch=2)[0] and published(906,0,epoch=2)[0]
    # An unrepresentable full refresh cannot authorize a later delta.
    bad=bytes(range(256))*16
    ok,_,h=published(907,2,data=bad,epoch=2)
    assert not ok and decode(h,1)==maps[906][:1472]+maps[906][2048:3520]
    assert published(907,0,epoch=2)[0]
    assert struct.unpack_from('<II',before,4)[1] or not rows[-1]['ok']
    out.write_text(json.dumps(dict(bytes=SIZE,text=sizes,records=rows,
        stop_cold_reseed=True,failed_update_preserves_peer=True),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','work','out'):p.add_argument(k,type=Path)
    verify(**vars(p.parse_args()))
