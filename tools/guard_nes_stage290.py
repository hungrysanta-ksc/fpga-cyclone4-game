# SPDX-License-Identifier: MIT
"""Actual M4 partial planner/producer lifetime and malformed frontier checks."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from nes_delta231 import BASE,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);arm=Producer(a.source/'output.elf',None);checks=[]
    for n in ('reset259','reset285','reset280'):arm.call(n,[])
    assert not arm.call('begin_native290',[]);checks.append('uncommitted input cannot start native output')
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    for b in chunks(records(BASE/'probes/nes-joint284/test04/frame905.records')):
        arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
    for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286','begin_native290'):assert arm.call(n,[]),n
    size=lambda:int.from_bytes(arm.uc.mem_read(arm.symbols['output_size285'],4),'little')
    for _ in range(34):
        ok=arm.call('next_step286',[]);assert ok==1
        if size():break
    else:raise AssertionError('no partial batch')
    saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save();sent=list(arm.packets)
    def restore():arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx);arm.packets=sent.copy();arm.fail_at=None
    assert not arm.call('prepare289',[]) and not arm.call('commit285',[]);checks.append('partial planner cannot seal or commit')
    restore();assert not arm.call('tiles290',[1]) and not arm.call('commit285',[]);checks.append('partial plan cannot final-flush')
    restore();assert arm.call('tiles290',[0]);after=len(arm.packets);assert arm.call('tiles290',[0]) and len(arm.packets)==after;checks.append('same frontier is not replayed')
    arm.uc.mem_write(arm.symbols['output_size285'],b'\0'*4);assert not arm.call('tiles290',[0]);checks.append('shrinking frontier rejected')
    for name,off,value in [('empty batch',2,b'\0'),('oversized batch',0,b'\xff\xff'),('reserved opcode',3,b'\x83')]:
        restore();arm.uc.mem_write(arm.symbols['output285']+off,value);assert not arm.call('tiles290',[0]) and not arm.call('commit285',[]);checks.append(name)
    restore();arm.call('stop286',[])
    assert not arm.call('tiles290',[0]) and not arm.call('prepare289',[]) and not arm.call('commit285',[]);checks.append('STOP during partial planner rejects all output and commit')
    r=dict(passed=True,checks=checks,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
