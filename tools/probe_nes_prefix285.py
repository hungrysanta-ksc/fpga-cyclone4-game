# SPDX-License-Identifier: MIT
"""Bind checked geometry availability to actual N5 blocks and M4 decoding."""
import argparse,binascii,json,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_arm264 import ARM
from probe_nes_decode280 import records,chunks,golden


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    evidence=BASE/'probes/nes-joint284/test04';elf=evidence/'source-ARM-decoder.elf';shutil.copyfile(elf,d/'decoder.elf')
    arm=ARM(elf,None);arm.call('reset280',[]);rows=[];pins={str(elf):sha(elf)};rejected=0
    for f in range(905,976):
        path=evidence/f'frame{f}.records';pins[str(path)]=sha(path);rr=records(path);bs=chunks(rr)
        geom_end=sum(map(len,rr[:next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\x00\x03')+1]))
        wire_end=0;geom_block=None;costs=[]
        for i,b in enumerate(bs):
            arm.uc.mem_write(0x20018000,b)
            if i==len(bs)-1 and f in (905,907,954):
                memory=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save()
                bad=bytearray(b);bad[-1]^=1;arm.uc.mem_write(0x20018000,bytes(bad))
                assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(bad,65535)])==0
                assert arm.call('complete280',[])==0;rejected+=1
                arm.uc.mem_write(0x20000000,memory);arm.uc.context_restore(ctx)
            before=arm.instructions
            assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
            costs.append(arm.instructions-before);wire_end+=len(b)
            if geom_block is None and wire_end>=geom_end:geom_block=i
            assert arm.call('complete280',[])==int(i==len(bs)-1)
        geom,raw=golden(f);assert bytes(arm.uc.mem_read(0x20010000,4910))==geom+raw
        rows.append(dict(frame=f,blocks=len(bs),geometry_block=geom_block,tail_blocks=len(bs)-geom_block-1,
            tail_payload_bytes=sum(map(len,bs[geom_block+1:])),tail_decode_instructions=sum(costs[geom_block+1:]),
            decode_instructions=sum(costs),complete_only_at_last_block=True))
    result=dict(passed=True,frames=rows,late_checksum_rejects=rejected,ELF_sha256=sha(elf),input_hashes=pins,script_sha256=sha(Path(__file__)),
        new_wire=False,early_plan_generated=False,scope='Original block CRC and whole-stream CRC kept. Geometry may be available earlier only after its containing SPI block is checked. Planner still requires full input COMMITTED; no new schedule claim.')
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,frames=71,geometry_in_last_block=sum(r['tail_blocks']==0 for r in rows),late_checksum_rejects=rejected)))


if __name__=='__main__':main()
