# SPDX-License-Identifier: MIT
"""Actual M4 ABI converter cost; independent semantic oracle, not new RTL."""
import argparse,binascii,collections,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM,u16,u32

def build(d):
    d.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(ROOT/'tools/nes_abi364.c',d/'nes_abi364.c')
    (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
    (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
    tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    for name,args,label in [
      ('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-fno-builtin','-nostdlib','-fstack-usage','-Wl,-T,layout.ld','-Wl,-Map,abi364.map','nes_abi364.c','stubs.s','-o','abi364.elf'],'build'),
      ('size',['abi364.elf'],'size'),('objdump',['-dr','abi364.elf'],'disassembly')]:
        r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (d/f'{label}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')

def rle(b,n):
    out=bytearray();at=0
    while at<len(b):
        h=b[at];at+=1;k=(h&127)+1
        if h&128:out.extend(bytes(k))
        else:assert at+k<=len(b);out.extend(b[at:at+k]);at+=k
    assert len(out)==n
    return bytes(out)

def plans(b,count):
    out=[];at=0
    for _ in range(count):
        k=b[at]
        if k&128:
            kind=k&127;n=7 if kind==0 else 8 if kind==1 else 3
            assert at+n<=len(b);p=b[at:at+n];at+=n
            d=bytearray(32);d[0]=kind;d[2:4]=p[1:3]
            if kind<2:d[4:8]=p[3:7];d[8]=255 if kind==0 else p[7];d[9:15]=bytes.fromhex('40226d646bff');d[15]=1
        else:
            assert at+16<=len(b);d=bytearray(b[at:at+16])+bytearray(16);at+=16
            for j in range(8):
                if d[1]>>j&1:assert at+2<=len(b);d[16+j*2:18+j*2]=b[at:at+2];at+=2
        out.append(bytes(d))
    assert at==len(b)
    return out

def old_semantics(tx):
    if tx[0]==0xe9:
        assert len(tx)==u16(tx,1)+8
        return [('plan',p) for p in plans(tx[4:-4],tx[3])]
    assert tx[0]==0xe1 and binascii.crc_hqx(tx[:-2],65535)==int.from_bytes(tx[-2:],'big')
    p=tx[1:-2];op,section=p[:2];start=u16(p,10);span=u16(p,14);v=p[16:];assert u16(p,12)==len(v)
    if op==14:
        token=u32(v);out=[];at=5
        for i in range(v[4]):
            off=u16(v,at);n=v[at+2];at+=3;out.append(('map',section,token+i,off,v[at:at+n]));at+=n
        assert at==len(v);return out
    if op==15:assert v[24]==1;return [('metadata',15,0,v[:24]+rle(v[25:],166))]
    if op==11:assert v[0]==3;return [('metadata',10,0,rle(v[1:],256))]
    if op==10:return [('metadata',10,start,v)]
    return [('output',op,section,start,len(v) if op==2 else span,v)]

def envelopes(b,serial,seq):
    out=[];at=0
    while at<len(b):
        assert at+13<=len(b);n=u16(b,at+5);p=b[at:at+n+13];assert len(p)==n+13 and p[0]==0xeb
        assert u16(p,3)==seq and u32(p,7)==serial and seq<=65535
        assert binascii.crc_hqx(p[:-2],65535)==int.from_bytes(p[-2:],'big')
        route=p[2];assert route in range(7)
        assert (route in (1,2) and n<=512) or (route not in (1,2) and n<=246)
        out.append((p[1],route,p[11:-2]));seq+=1;at+=len(p)
    return out,seq

def normalized_semantics(records):
    out=[]
    for kind,route,b in records:
        op,section=kind&15,kind>>4
        if route==1:out.extend(('plan',p) for p in plans(b,kind));continue
        if route==2:assert len(b)==kind*32;out.extend(('plan',b[i:i+32]) for i in range(0,len(b),32));continue
        if route==0:
            # Reconstruct a legacy payload only for the semantic oracle.
            p=bytearray(16);p[0:2]=bytes([op,section]);p[10:12]=b[:2];p[12:14]=(len(b)-4).to_bytes(2,'little');p[14:16]=b[2:4]
            tx=b'\xe1'+p+b[4:];tx+=binascii.crc_hqx(tx,65535).to_bytes(2,'big');out.extend(old_semantics(tx));continue
        if route==3:
            assert op in (10,11,15) and len(b)>=2
            off=u16(b);v=b[2:];assert off+len(v)<=(190 if op==15 else 256)
            out.append(('metadata',15 if op==15 else 10,off,v));continue
        if route==4:assert op in (1,3,13);out.append(('output',op,section,0,0,b));continue
        if route==6:
            assert len(b)>=8 and u16(b,4)==len(b)-8 and b[7]==section
            assert b[6]==(1 if op in (4,5) else 2 if op==8 else 3 if op==7 else 0)
            out.append(('output',op,section,u16(b),u16(b,2),b[8:]));continue
        assert route==5 and op==14 and len(b)>=5
        token=u32(b);count=b[4];assert count and token+count<=0xffffffff;at=5
        for i in range(count):
            assert at+8<=len(b);off=u16(b,at);n=u16(b,at+2)
            assert 0<n<=64 and not (off|n)&1 and off+n<=4096 and u16(b,at+4)==n and b[at+6:at+8]==bytes([0,section])
            at+=8;assert at+n<=len(b);out.append(('map',section,token+i,off,b[at:at+n]));at+=n
        assert at==len(b)
    # Only adjacent fragments of the same original item can coalesce.
    merged=[]
    for row in out:
        if merged and row[0]=='metadata' and merged[-1][:2]==row[:2] and merged[-1][2]+len(merged[-1][3])==row[2]:
            prior=merged.pop();merged.append((*prior[:3],prior[3]+row[3]))
        elif merged and row[:2]==('output',2) and merged[-1][:3]==row[:3] and merged[-1][3]+len(merged[-1][5])==row[3]:
            prior=merged.pop();merged.append((*prior[:4],prior[4]+row[4],prior[5]+row[5]))
        else:merged.append(row)
    return merged

class Converter:
    def __init__(self,elf,mode):
        self.arm=ARM(elf,None);self.arm.call('reset364',[]);self.mode=mode;self.serial=0;self.seq=0
    def convert(self,tx,serial):
        if serial!=self.serial:self.serial=serial;self.seq=0
        self.arm.uc.mem_write(0x20010000,tx);before=self.arm.instructions
        assert self.arm.call('convert364',[0x20010000,len(tx),self.mode,serial])==1,('convert',tx.hex())
        instructions=self.arm.instructions-before
        word=lambda name:int.from_bytes(self.arm.uc.mem_read(self.arm.symbols[name],4),'little')
        b=bytes(self.arm.uc.mem_read(self.arm.symbols['output364'],word('size364')))
        records,self.seq=envelopes(b,serial,self.seq)
        assert normalized_semantics(records)==old_semantics(tx),('semantic mismatch',tx.hex(),normalized_semantics(records),old_semantics(tx))
        assert len(records)==word('packets364')
        return b,instructions,len(records)

def packet(op,section,serial,start,span,v):
    p=bytearray(16);p[0:2]=bytes([op,section]);p[4:8]=serial.to_bytes(4,'little');p[8:10]=(serial&65535).to_bytes(2,'little');p[10:12]=start.to_bytes(2,'little');p[12:14]=len(v).to_bytes(2,'little');p[14:16]=span.to_bytes(2,'little')
    b=b'\xe1'+p+v;return b+binascii.crc_hqx(b,65535).to_bytes(2,'big')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--build',action='store_true');a=ap.parse_args();d=a.out.resolve()
    if a.build:build(d)
    rows=[];detail=[];pins={}
    for schedule,folder in [('continuous','keepwindow01'),('fixed','keepfixed01')]:
        for mode in (0,1):
            c=Converter(d/'abi364.elf',mode)
            for f in range(905,908):
                p=BASE/f'probes/nes-execute362/{folder}/arm{f}.json';pins[str(p)]=sha(p);transfers=json.loads(p.read_text())['transfers'];r=collections.Counter()
                for t in transfers:
                    tx=bytes.fromhex(t['tx'])
                    if not tx or tx[0] not in (0xe1,0xe9):continue
                    b,ins,count=c.convert(tx,f-904);r.update(old_bytes=len(tx),new_bytes=len(b),instructions=ins,old_packets=1,new_packets=count,positive_bytes=max(0,len(b)-len(tx)))
                    detail.append(dict(schedule=schedule,mode=mode,frame=f,old=tx.hex(),new=b.hex(),instructions=ins,packets=count))
                r=dict(r);extra=r['new_packets']-r['old_packets'];r.update(schedule=schedule,mode=mode,frame=f,delta_bytes=r['new_bytes']-r['old_bytes'],extra_packets=extra,
                    added_cost_ms=r['instructions']/84000+r['positive_bytes']*8/2625+extra*(8/1000+14*8/2625+8/1000))
                rows.append(r)
    c=Converter(d/'abi364.elf',1)
    v=(100).to_bytes(4,'little')+bytes([47])+b''.join((i*2).to_bytes(2,'little')+b'\x02\x12\x34' for i in range(47))
    tests=[packet(14,0,1,0,0,v),packet(2,5,1,0,240,bytes(range(240)))]
    directed=[]
    for tx in tests:
        b,ins,n=c.convert(tx,1);directed.append(dict(old_bytes=len(tx),new_bytes=len(b),packets=n,instructions=ins))
    b,_,_=Converter(d/'abi364.elf',0).convert(tests[1],1)
    guards=[]
    for label,mutate,serial,seq in [('CRC',lambda x:x.__setitem__(-1,x[-1]^1),1,0),('serial',lambda x:None,2,0),('sequence',lambda x:None,1,1),('truncated',lambda x:x.pop(),1,0),('length',lambda x:x.__setitem__(5,x[5]^1),1,0)]:
        bad=bytearray(b);mutate(bad)
        try:envelopes(bad,serial,seq)
        except AssertionError:guards.append(label)
        else:raise AssertionError(('guard escaped',label))
    result=dict(passed=True,rows=rows,directed=directed,envelope_guards=guards,observed_stack_bytes=0x2003f000-c.arm.low_sp,pins=pins,
        scope='Actual M4 conversion of real outgoing packets; independent Python semantic checks. No new ABI receiver RTL, token ownership, STOP or final ACK proof.',added_cost='Old serializer retained. Positive wire delta only; extra fragment charges one 14B progress response and two 8us CS allocations; credit wait is NOT bounded.')
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');(d/'packets.json').write_text(json.dumps(detail,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
