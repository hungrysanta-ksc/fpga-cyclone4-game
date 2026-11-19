"""Replay the one-map ACK summary with both exact and conservative same-page flags."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from cost_nes_strip868 import ROOT, GCC, KernelARM, run, ELFFile
from probe_nes_map868 import phase_cases

H=0x20008000
M=0x20001000
P=0x20006000


def check(temp,work,out):
    work.mkdir(parents=True,exist_ok=False)
    image=ROOT.parent/'probes/nes-trial866/link/src/obj-nes-100/sd2snes.elf'
    with image.open('rb') as f:
        elf=ELFFile(f)
        symbols=elf.get_section_by_name('.symtab')
        definitions=[f"{name} = {symbols.get_symbol_by_name(name)[0]['st_value']};" for name in ('memcmp','memcpy')]
        segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments()
                  if s['p_type']=='PT_LOAD' and 0x08000000<=s['p_vaddr']<0x08050000]
    (work/'layout.ld').write_text('SECTIONS { . = 0x08058000; .text : { *(.text*) } }\n'+'\n'.join(definitions))
    # The standalone entry points use the four-register ARM harness ABI.
    code=(ROOT/'tools/nes_right869.c').read_text()+'''
unsigned prepare(const struct right869 *h,const mapword869 *map,uint32_t serial,uint16_t *out) {
 return serial>2 ? right_packet869(h,map,serial,out) : 0;
}
void confirm(struct right869 *h,const mapword869 *map,uint32_t serial,unsigned same) {
 (void)serial; remember869(h,map,same);
}
'''
    (work/'test.c').write_text(code)
    run([GCC/'arm-none-eabi-gcc.exe','-mcpu=cortex-m4','-mthumb','-Os','-nostdlib','-Wall','-Werror',
         '-Wl,-T,layout.ld','test.c','-o','right.elf'],work,'build')
    cpu=KernelARM(work/'right.elf')
    for at,data in segments:cpu.uc.mem_write(at,data)
    fixture=temp/'nes-tile821-demo-jointmirror-p1-866-on'
    cases={c['g']:bytes.fromhex(c['data']) for c in phase_cases(fixture,True)[0] if c['page']==2048}
    pages={g:(fixture/f'map-{g}.bin').read_bytes()[2048:3520] for g in range(905,967)}
    modes=[]
    for shortcut in (False,True):
        cpu.uc.mem_write(H,bytes(1352)+b'canary')
        records=[]
        for g,page in pages.items():
            cpu.uc.mem_write(M,page)
            before=bytes(cpu.uc.mem_read(H,1352))
            t=cpu.instructions
            n=cpu.call('prepare',[H,M,g-904,P])
            prep=cpu.instructions-t
            assert bytes(cpu.uc.mem_read(H,1352))==before
            if g<=906:assert not n
            if g in cases:
                assert bytes(cpu.uc.mem_read(P,n))==struct.pack('<I',g-906)+cases[g][4:]
            if n:
                # Prove exact omitted words in both published banks, including
                # packets produced on pages where another packet shape was used.
                data=bytes(cpu.uc.mem_read(P,n))
                col=int.from_bytes(data[6:8],'little')
                raw=bytearray(pages[g-2])
                peer=bytearray(pages[g-1])
                for k in range((n-8)//46):
                    for y in range(23):
                        at=y*64+col+2*k
                        j=8+46*k+2*y
                        raw[at:at+2]=peer[at:at+2]=data[j:j+2]
                assert bytes(raw)==bytes(peer)==page
            t=cpu.instructions
            cpu.call('confirm',[H,M,g-904,int(shortcut and pages.get(g-1)==page)])
            cycles=cpu.instructions-t
            hdr=bytes(cpu.uc.mem_read(H,1352))
            diff,keep=struct.unpack_from('<II',hdr)
            assert keep and cpu.uc.mem_read(H+1352,6)==b'canary'
            if g>905:
                previous=pages[g-1]
                expected=sum(1<<c for c in range(32) if any(previous[y*64+2*c:y*64+2*c+2]!=page[y*64+2*c:y*64+2*c+2] for y in range(23)))
                assert diff==expected
            j=-1
            for y in range(23):
                j+=y<keep or y>keep+1
                assert hdr[8+j*64:72+j*64]==page[y*64:y*64+64]
            records.append(dict(g=g,bytes=n,prepare=prep,publish=cycles))
        # Capacity failure invalidates serial. First subsequent full ACK
        # reseeds, but cannot authorize omission until two ACKs have arrived.
        cpu.uc.mem_write(M,b''.join(bytes([y])*64 for y in range(23)))
        cpu.call('confirm',[H,M,63,0])
        assert cpu.uc.mem_read(H+4,4)==bytes(4)
        cpu.uc.mem_write(M,pages[965])
        assert cpu.call('prepare',[H,M,64,P])==0
        cpu.call('confirm',[H,M,64,0])
        assert cpu.call('prepare',[H,M,65,P])==0
        modes.append(records)
    out.write_text(json.dumps(dict(physical_bytes=1352,eligible_baseline_pages=len(cases),
        input_elf_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),cold_capacity_recovery=True,
        conservative=modes[0],exact_same_flag=modes[1]),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','work','out'):p.add_argument(k,type=Path)
    check(**vars(p.parse_args()))
