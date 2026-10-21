# SPDX-License-Identifier: MIT
"""Producer failure guards with intercepted dispatch; not a display ACK test."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from nes_delta231 import BASE,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);arm=Producer(a.source/'output.elf',None)
    for n in ('reset259','reset285','reset280'):arm.call(n,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    for b in chunks(records(BASE/'probes/nes-joint284/test04/frame905.records')):
        arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
    for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(n,[])
    for _ in range(34):
        ok=arm.call('next_step286',[]);assert ok
        if ok==2:break
    else:raise AssertionError('planner bound')
    saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save();checks=[]
    def restore():
        arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx);arm.packets=[];arm.fail_at=None
    assert arm.call('prepare289',[]) and arm.call('produce289',[]);total=len(arm.packets)
    for failure in (1,total//2,total):
        restore();assert arm.call('prepare289',[]);arm.fail_at=failure
        assert not arm.call('produce289',[])
        before=bytes(arm.uc.mem_read(0x20000000,0x30000));assert not arm.call('commit285',[])
        assert before==bytes(arm.uc.mem_read(0x20000000,0x30000))
        arm.call('stop286',[]);assert not arm.call('prepare289',[]) and not arm.call('commit285',[])
        checks.append(f'packet {failure}/{total} failure: no commit; STOP')
    # First compact zero plan is mandatory and carries the generation.
    assert saved[arm.symbols['output285']-0x20000000+3]==0x82
    for name,offset,value in [('empty batch',2,b'\0'),('oversized batch',0,b'\xff\xff'),('reserved opcode',3,b'\x83'),('wrong generation',4,b'\xff\xff')]:
        restore();arm.uc.mem_write(arm.symbols['output285']+offset,value)
        assert arm.call('prepare289',[]) and not arm.call('produce289',[]) and not arm.call('commit285',[]),name
        checks.append(name)
    restore();arm.uc.mem_write(arm.symbols['output_size285'],struct.pack('<I',2))
    assert arm.call('prepare289',[]) and not arm.call('produce289',[]) and not arm.call('commit285',[]);checks.append('truncated batch header')
    result=dict(passed=True,checks=checks,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
