# SPDX-License-Identifier: MIT
"""Actual selected M4 ELF: private BG lifetime, raw alias, STOP and membership."""
import argparse,binascii,json
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_arm264 import ARM,ELFFile
from probe_nes_decode280 import records,chunks

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not a.out.exists();a.out.mkdir(parents=True)
    # Assert the exact candidate layout before using its byte-view tile store.
    with (a.source/'output.elf').open('rb') as f:
        elf=ELFFile(f);sym=elf.get_section_by_name('.symtab').get_symbol_by_name('input285')[0];assert sym['st_size']==9880
    rr=records(a.source/'frame905.records');geo=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\0\3')
    def begin():
        arm=ARM(a.source/'output.elf',None)
        for n in ('reset285','reset280'):arm.call(n,[])
        arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
        return arm
    def feed(arm,recs):
        for b in chunks(recs):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])==1
    def bg(arm):
        feed(arm,rr[:geo+1]);assert arm.call('geometry_ready286',[])==1
        for n in ('expand286','begin285','geometry_plan286','h2early286'):assert arm.call(n,[])==1,n
    results=[]
    arm=begin();bg(arm);assert arm.call('input_commit286',[])==0;assert arm.call('begin_step286',[])==0
    results.append('BG seal alone cannot commit or execute')
    arm=begin();bg(arm);arm.call('stop286',[]);assert arm.call('begin_step286',[])==0;assert arm.call('next_step286',[])==0
    results.append('STOP cancels private BG execution')
    arm=begin();bg(arm);at=arm.symbols['input285']+5728;before=bytes(arm.uc.mem_read(at,2048))
    assert any(before);feed(arm,rr[geo+1:]);assert arm.call('input_commit286',[])==1
    after=bytes(arm.uc.mem_read(at,2048));assert all((a&b)==a for a,b in zip(before,after))
    assert bytes(arm.uc.mem_read(arm.symbols['input285']+7776,512))==bytes(arm.uc.mem_read(arm.symbols['history286']+4398,512))
    results.append('BG membership survives actual OBJ merge and raw copy')
    assert arm.call('begin_step286',[])==1
    arm.uc.mem_write(at,bytes(2048));assert arm.call('next_step286',[])==0
    results.append('missing checked membership rejects actual BG step')
    out=dict(passed=True,cases=results,ELF_sha256=sha(a.source/'output.elf'),scope='Actual M4 private BG/commit lifecycle; no SPI timing claim')
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
