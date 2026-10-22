# SPDX-License-Identifier: MIT
"""Measure ARM normalization proposals against actual280 packets and receipts.

Cost probe, not a new serializer/RTL/CPU schedule. Paired wire-helper deltas
are explicit sensitivities; old producer loops have not been replaced.
"""
from pathlib import Path
import argparse,binascii,collections,csv,json,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM,u16


def oracle_spans(p,scroll,raw):
    op,sec,start=p[0],p[1],u16(p,10)
    length=u16(p,12) if op==2 else u16(p,14)
    bits=[]
    if op==7:
        unit=32 if sec else 16
        bits=list(range((1024 if sec else 0)+start//unit,(1024 if sec else 0)+(start+length)//unit))
    elif sec==3:bits=list(range(1152+start//16,1152+(start+length)//16))
    elif sec==5:
        for i in range(128):
            lo,hi=1121+i*16,1121+(i+1)*16
            if start<=lo and hi<=start+length:bits.append(1184+i)
        if raw:
            for i in range(16):
                lo,hi=3169+i*16,min(3418,3169+(i+1)*16)
                if start<=lo and hi<=start+length:bits.append(1312+i)
    spans=[]
    # Body and raw ranges remain distinct even when adjacent in bit space.
    for bit in bits:
        if spans and bit==sum(spans[-1]) and bit!=1312:spans[-1][1]+=1
        else:spans.append([bit,1])
    return spans


def dense_packet(p,body,at):
    q=bytearray(p[:16]);q[0]=10;q[10:12]=at.to_bytes(2,'little')
    q[12:14]=len(body).to_bytes(2,'little');q[14:16]=b'\0\0'
    return bytes(q)+body


def build(d):
    shutil.copyfile(ROOT/'tools/nes_boundary281.c',d/'nes_boundary281.c')
    (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
    (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
    tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    for name,args,label in [('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-fno-builtin','-nostdlib','-fstack-usage','-Wl,-T,layout.ld','-Wl,-Map,probe.map','nes_boundary281.c','stubs.s','-o','probe.elf'],'build'),('size',['probe.elf'],'size'),('objdump',['-dr','probe.elf'],'disassembly')]:
        r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (d/f'{label}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);build(d)
    q=BASE/'probes/nes-joint280/test05';pins={};arm=ARM(d/'probe.elf',None)
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def call(name,p,args):
        arm.uc.mem_write(0x20010000,p);before=arm.instructions
        ret=arm.call(name,[0x20010000,len(p),0x20011000,*args])
        return ret,arm.instructions-before
    def wire(p,compact):
        n,cost=call('wire281',p,[int(compact)]);assert n==len(p)+3-4*compact
        actual=bytes(arm.uc.mem_read(0x20011000,n))
        body=bytes(v for i,v in enumerate(p) if not compact or i not in (8,9,12,13))
        expected=b'\xe1'+body;expected+=binascii.crc_hqx(expected,65535).to_bytes(2,'big')
        assert actual==expected
        return n,cost
    receipt=bytes.fromhex(read(q/'expected.hex'));rows=[];frames={};hints={};rejects=[]
    for f in range(905,976):
        tx=json.loads(read(q/f'arm{f}.json'))['transfers'];packets=[]
        for t in tx:
            x=bytes.fromhex(t['tx'])
            if x[0]==225:
                assert binascii.crc_hqx(x,65535)==0;packets.append(x[1:-2])
        scroll,raw=u16(packets[0],30),packets[0][36];assert raw<=2
        manifest=bytearray();mapped=set();received=set();span_cost=manifest_cost=0;spanbytes=0
        frame_hints={};arm.uc.mem_write(0x20011000,bytes(256))
        for seq,p in enumerate(packets):
            assert u16(p,2)==seq and len(p)==16+u16(p,12)
            if p[0] in (2,4,5,7,8):
                n,c=call('spans281',p,[scroll|(raw<<16)]);assert n<=2,(f,seq,n)
                actual=bytes(arm.uc.mem_read(0x20011000,4*n))
                spans=oracle_spans(p,scroll,raw)
                expected=b''.join(x.to_bytes(2,'little')+y.to_bytes(2,'little') for x,y in spans)
                assert actual==expected,(f,seq,spans)
                for first,count in spans:
                    for bit in range(first,first+count):assert bit not in received;received.add(bit)
                frame_hints[seq]=actual+bytes([n]);span_cost+=c;spanbytes+=4*n+1
            elif p[0] in (10,11):
                # C and independent Python expansion start at identical offsets.
                arm.uc.mem_write(0x20011000,bytes(manifest)+bytes(256-len(manifest)))
                n,c=call('manifest281',p,[len(manifest)]);assert n<=256
                if p[0]==10:manifest+=p[16:]
                else:
                    assert p[16]==3;at=17
                    while at<len(p):
                        tag=p[at];at+=1;count=(tag&127)+1
                        if tag&128:manifest+=bytes(count)
                        else:assert at+count<=len(p);manifest+=p[at:at+count];at+=count
                assert n==len(manifest) and bytes(arm.uc.mem_read(0x20011000,n))==manifest
                manifest_cost+=c
            elif p[0]==14:
                at=21
                for _ in range(p[20]):
                    off,n=u16(p,at),p[at+2];at+=3
                    for bit in range(off//2,(off+n)//2):assert bit not in mapped;mapped.add(bit)
                    at+=n
                assert at==len(p)
        expected=receipt[(f-905)*754+332:(f-905)*754+498]
        assert received=={i for i in range(1328) if expected[i//8]>>(i%8)&1},f
        assert len(manifest)==256 and mapped=={i for i in range(2048) if manifest[i//8]>>(i%8)&1}
        assert manifest==receipt[(f-905)*754+498:(f-904)*754]
        base_wire=base_cost=0
        for p in packets:
            n,c=wire(p,False);base_wire+=n;base_cost+=c
        row=dict(frame=f,packets=len(packets),manifest_packets=sum(p[0] in (10,11) for p in packets),
            manifest_payload=sum(len(p)-16 for p in packets if p[0] in (10,11)),span_bytes=spanbytes,
            span_instructions=span_cost,manifest_instructions=manifest_cost,reference_pack_instructions=base_cost,
            baseline_E1_bytes=base_wire)
        for variant in ('dense','spans','compact'):
            proposed=[];emitted=False
            for seq,p in enumerate(packets):
                if p[0] in (10,11):
                    if not emitted:
                        cap=240
                        proposed.extend(dense_packet(p,manifest[at:at+cap],at) for at in range(0,256,cap));emitted=True
                    continue
                if variant!='dense' and seq in frame_hints:
                    p=bytearray(p+frame_hints[seq]);p[12:14]=(len(p)-16).to_bytes(2,'little');p=bytes(p)
                proposed.append(p)
            total=cost=0
            for seq,p in enumerate(proposed):
                p=bytearray(p);p[2:4]=seq.to_bytes(2,'little');p=bytes(p)
                # Keep the existing 256B logical envelope for every variant.
                assert len(p)<=256,(f,variant,len(p))
                n,c=wire(p,variant=='compact');total+=n;cost+=c
            row.update({variant+'_bytes_delta':total-base_wire,variant+'_packets_delta':len(proposed)-len(packets),
                variant+'_pack_instructions_delta':cost-base_cost,
                variant+'_extra_instructions':manifest_cost+(span_cost if variant!='dense' else 0)+max(0,cost-base_cost)})
        rows.append(row);frames[str(f)]=dict(manifest=manifest.hex(),received=expected.hex(),spans={str(k):v.hex() for k,v in frame_hints.items()})
        hints[f]=frame_hints
    # Reject malformed normalization inputs; partial scratch writes never publish.
    def reject(name,fn,p,arg):
        ret,_=call(fn,p,[arg]);assert ret==0xffffffff,name;rejects.append(name)
    sample=next(p for p in packets if p[0]==11)
    for name,offset,val in [('manifest section',1,4),('manifest version',16,2),('manifest cursor',10,1),('manifest outlen',14,1)]:
        p=bytearray(sample);p[offset]=val;reject(name,'manifest281',bytes(p),0)
    reject('manifest truncation','manifest281',sample[:-1],0)
    p=bytearray(16);p[0]=11;p[1]=2;p[12]=4;p+=bytes([3,255,255,255]);reject('manifest overflow','manifest281',bytes(p),0)
    data=next(p for p in packets if p[0]==7)
    for name,offset,val in [('tile target',1,2),('tile alignment',10,1),('tile zero length',14,0)]:
        p=bytearray(data);p[offset]=val
        if name=='tile zero length':p[15]=0
        reject(name,'spans281',bytes(p),scroll|(raw<<16))
    reject('raw outside candidate','spans281',data,scroll|(3<<16))
    # A proposed ARM hint cannot be accepted just because its packet CRC is good.
    independent=[]
    for f in (905,954,970):
        seq=next(k for k,v in hints[f].items() if v[-1]);good=hints[f][seq]
        for field in (0,2):
            bad=bytearray(good);bad[field]^=1
            assert bytes(bad)!=good;independent.append(f'{f}:forged_span_field{field}')
        expected=bytes.fromhex(frames[str(f)]['manifest']);bad=bytearray(expected);bad[0]^=1
        assert bad!=expected;independent.append(f'{f}:forged_manifest')
    with (d/'frames.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'vectors.json').write_text(json.dumps(frames,indent=2)+'\n',encoding='utf-8',newline='\n')
    r=dict(passed=True,frames=71,packets=sum(r['packets'] for r in rows),rejected_inputs=rejects,
        independent_mismatch_vectors=independent,ELF_sha256=sha(d/'probe.elf'),C_sha256=sha(d/'nes_boundary281.c'),
        script_sha256=sha(Path(__file__)),input_hashes=pins,size=(d/'size.log').read_text(),
        observed_stack=0x2003f000-arm.low_sp,static_dense_scratch=256,span_scratch=9,
        limits=['Scratch is caller memory, not reclaimed FPGA RAM.',
          'Wire helper paired deltas are measured instruction sensitivities, not an integrated serializer.',
          'No old CRC/copy loop is credited beyond the measured paired helper; negative helper deltas are clamped to zero.',
          'No new RTL, SNES CPU ABI, polling/ROM retime, full RUN or hardware cycles.'],new_RTL=False,new_MAP=False,new_schedule=False)
    (d/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:r[k] for k in ('passed','frames','packets','size','observed_stack')}))


if __name__=='__main__':main()
