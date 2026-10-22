# SPDX-License-Identifier: MIT
"""Execute the new N5-v2 source codec on Cortex-M4; exact bytes, not CRC-only."""
import argparse,binascii,collections,csv,json,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_block249 import encode
from analyze_nes_cost279 import raw_delta
from probe_nes_arm264 import ARM,crc as armcrc


def records(path):
    out=[]
    for line in path.read_text().splitlines():
        n,h=line.split();b=bytes.fromhex(h);assert len(b)==int(n);out.append(b)
    return out


def golden(f):
    old=records(BASE/f'probes/nes-joint278/test07/frame{f}.records')
    raw=False;data=bytearray()
    for r in old:
        if r[:4]==b'\xff\xff\x00\x03':raw=True
        elif raw and r[:4]!=b'\xff\xff\x00\x04':data+=r[3:]
    geometry=bytes.fromhex((BASE/f'probes/nes-joint278/test07/frame{f}.expected').read_text())
    assert len(geometry)==4398 and len(data)==512
    return geometry,bytes(data)


def encode280(old,new,raw,prior_raw,serial,generation):
    rr=encode(old,new,b'',serial,generation)[:-1]
    h=bytearray(rr[0]);h[2]=2;h[3]|=2 if prior_raw is None or len(prior_raw)!=len(raw) else 0;rr[0]=bytes(h)
    rr+=raw_delta(raw,prior_raw if prior_raw is not None and len(prior_raw)==len(raw) else None)
    rr+=[b'\xff\xff\x00\x04\x00\x00'];c=65535;result=[]
    for r in rr:
        trailer=r[:4] in (b'\xff\xff\x00\x03',b'\xff\xff\x00\x04')
        c=binascii.crc_hqx(r[:-2] if trailer else r,c)
        result.append(r[:-2]+struct.pack('<H',c) if trailer else r)
    return result


def chunks(rr):
    blocks=[];cur=b''
    for r in rr:
        if len(cur)+len(r)>248:blocks.append(cur);cur=b''
        cur+=r
    if cur:blocks.append(cur)
    return blocks


def build(d):
    shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')
    (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
    (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
    tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    for name,args,label in [
      ('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-fno-builtin','-nostdlib','-fstack-usage','-Wl,-T,layout.ld','-Wl,-Map,decoder.map','nes_decode280.c','stubs.s','-o','decoder.elf'],'build'),
      ('size',['decoder.elf'],'size'),('objdump',['-dr','decoder.elf'],'disassembly')]:
        r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (d/f'{label}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--rtl',type=Path)
    a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);build(d)
    arm=ARM(d/'decoder.elf',None);arm.call('reset280',[]);old=bytes(4398);prev=None;rows=[];blockrows=[];pins={}
    bb=collections.defaultdict(list)
    if a.rtl:
        for line in (a.rtl/'blocks.txt').read_text().splitlines():
            f,tok,n,h=line.split();b=bytes.fromhex(h);assert len(b)==int(n);bb[int(f)].append(b)
    for f in sorted(bb) if a.rtl else range(905,976):
        geom,raw=golden(f);rr=encode280(old,geom,raw,prev,f-904,f-904)
        if a.rtl:
            assert rr==records(a.rtl/f'frame{f}.records'),('RTL records',f)
            assert chunks(rr)==bb[f],('SPI payload',f)
        else:bb[f]=chunks(rr)
        (d/f'frame{f}.records').write_text(''.join(f'{len(r)} {r.hex()}\n' for r in rr))
        before=arm.instructions
        for i,b in enumerate(bb[f]):
            arm.uc.mem_write(0x20018000,b);ib=arm.instructions
            assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1,(f,i)
            blockrows.append(dict(frame=f,block=i,length=len(b),instructions=arm.instructions-ib))
        assert arm.call('complete280',[])==1
        assert bytes(arm.uc.mem_read(0x20010000,4910))==geom+raw,('ARM reconstruction',f)
        rows.append(dict(frame=f,payload=sum(map(len,bb[f])),blocks=len(bb[f]),instructions=arm.instructions-before,
                         CRC16=binascii.crc_hqx(geom+raw,65535)))
        for p in [BASE/f'probes/nes-joint278/test07/frame{f}.expected',
                  BASE/f'probes/nes-joint278/test07/frame{f}.records']:pins[str(p)]=sha(p)
        old=geom;prev=raw
    for name,data in [('frames.csv',rows),('blocks.csv',blockrows)]:
        with (d/name).open('w',newline='') as fp:
            w=csv.DictWriter(fp,fieldnames=data[0]);w.writeheader();w.writerows(data)
    control=[]
    for flags in (0,1,3):
        before=arm.instructions
        assert arm.call('prefix280',[0x20018000,37,4,flags])==1
        p=bytes(arm.uc.mem_read(0x20018000,8));assert armcrc(p[:6],8)==p[6] and p[7]==165
        control.append(dict(kind=f'prefix{flags}',instructions=arm.instructions-before))
    for ready in (0,1):
        p=bytes([0xaa|ready,248 if ready else 0,0,38]);p+=bytes([armcrc(p,8)])
        arm.uc.mem_write(0x20018000,p);before=arm.instructions
        assert arm.call('reply280',[0x20018000,38])==1
        control.append(dict(kind=f'reply{ready}',instructions=arm.instructions-before))
    # Each block cost includes block CRC and parsing. Final complete() cost is
    # charged to the last block; control cost is separately replayed per poll.
    deltas=[]
    for row in rows:
        sums=sum(b['instructions'] for b in blockrows if b['frame']==row['frame'])
        deltas.append(row['instructions']-sums)
    assert len(set(deltas))==1
    (d/'control.json').write_text(json.dumps(dict(cases=control,complete_instructions=deltas[0]),indent=2)+'\n')
    result=dict(passed=True,frames=rows,reconstructed_bytes=len(rows)*4910,raw_bytes=len(rows)*512,
        stack_observed=0x2003f000-arm.low_sp,size=(d/'size.log').read_text(),input_hashes=pins,
        ELF_sha256=sha(d/'decoder.elf'),C_sha256=sha(d/'nes_decode280.c'),
        control=control,complete_instructions=deltas[0],
        RTL_bound=bool(a.rtl),source_SPI_ARM=False,full_N5_planner=False,hardware_cycles=False,scope=__doc__)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','reconstructed_bytes','stack_observed','size')}))


if __name__=='__main__':main()
