# SPDX-License-Identifier: MIT
"""Actual exporter/fill/SPI -> actual C receiver, frozen181 comparison.

Only changed boundaries run. No cold game boot, FIT or physical FPS claim.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess
from nes_packed181 import ROOT, prepare, replace_once

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def encode(logical):
    """Independent run/batch reference, preserving logical END counts."""
    out=[];i=0;raw=False
    while i<len(logical):
        r=logical[i];k=r>>93;gen=(r>>77)&65535;idx=(r>>64)&8191;v=r&((1<<64)-1)
        def emit(kind,index,value):out.append((kind<<93)|(gen<<77)|(index<<64)|value)
        if k==7:
            if idx==0:v=(v&((1<<48)-1))|(0x1813<<48)
            if idx==4:raw=True
            emit(k,idx,v);i+=1;continue
        if k==6 and not raw:emit(k,idx,v);i+=1;continue
        n=1
        if raw or k in (1,5):
            size=10 if raw else 8;bits=6 if raw else 8
            while n<size and i+n<len(logical):
                q=logical[i+n]
                if q>>93!=k or ((q>>64)&8191)!=idx+n:break
                v=(v<<bits)|(q&((1<<64)-1));n+=1
            emit(7,0x1000+idx if raw else 0x1800|(k<<8)|(n-1),(n<<60)|v if raw else v)
        else:
            while n<256 and i+n<len(logical):
                q=logical[i+n]
                if q>>93!=k or ((q>>64)&8191)!=idx+n or q&((1<<64)-1)!=v:break
                n+=1
            emit(k,idx,v) if n==1 else emit(7,0x800|(k<<8)|(n-1),v)
        i+=n
    return out

def main():
    p=argparse.ArgumentParser()
    for n in ('workspace','out','questa-bin','gcc','arm-bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.workspace=a.workspace.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    frozen=a.workspace/'probes/nes-wire181/evidence/test02'
    metadata=json.loads((ROOT/'analysis/wire181-verification.json').read_bytes())['wire']
    assert sha(frozen/'wire181_tb.sv')==metadata['generated_bench_sha256']
    prep=prepare(a.out/'candidate',frozen/'nes_native_spi165.sv');sources={}
    for n in ('nes_native_fill165.sv','nes_native_spi165.sv','nes_trace166.c','nes_trace166.h'):
        shutil.copyfile(frozen/n,a.out/n);sources[n]=sha(frozen/n)
    for n in ('nes_native_export181.sv','nes_native165.c','nes_native165.h','nes_native_spi165.sv'):shutil.copyfile(a.out/'candidate'/n,a.out/n)
    for name in ('wire181_source.svh','packed181_host.c'):
        q=ROOT/'tests/nes-functional'/name;shutil.copyfile(q,a.out/name);sources[name]=sha(q)
    source=(a.out/'wire181_source.svh').read_text()
    source=replace_once(source,'parameter integer PATCHES=0;','parameter integer PATCHES=0;\nparameter integer GROUPS=1;')
    source=replace_once(source,".group_count(6'd1)",".group_count(6'(GROUPS))")
    source=replace_once(source,'if(chr_ended)raw_count<=raw_count+1;else chr_count<=chr_count+1;',
        'if(chr_ended)$fatal(1,"legacy raw record");else chr_count<=chr_count+1;')
    source=replace_once(source,'if(data[95:93]==7&&data[76:64]==2)',
        "if(data[95:93]==7&&data[76:64]>=13'h1000&&data[76:64]<13'h1700)raw_count<=raw_count+data[63:60];\n   if(data[95:93]==7&&data[76:64]==2)")
    (a.out/'wire181_source.svh').write_text(source)
    shutil.copyfile(frozen/'wire181_tb.sv',a.out/'bench.sv')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    def run(exe,args,label,d=None):
        d=d or a.out
        with (d/(label+'.log')).open('wb') as f:q=subprocess.run([str(exe),*map(str,args)],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        s=(d/(label+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),(label,s[-3000:])
        return s
    run(a.questa_bin/'vlib.exe',['work'],'vlib')
    run(a.questa_bin/'vlog.exe',['-sv','nes_native_fill165.sv','nes_native_spi165.sv','nes_native_export181.sv','bench.sv'],'compile')
    fault=ROOT/'tests/nes-functional/packed181_faults_tb.sv';shutil.copyfile(fault,a.out/fault.name);sources[fault.name]=sha(fault)
    run(a.questa_bin/'vlog.exe',['-sv',fault.name],'fault-compile')
    f=run(a.questa_bin/'vsim.exe',['-c','work.packed181_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'fault')
    assert 'PASS PACKED181FAULT cases=8' in f
    run(a.gcc,['-std=c11','-O2','-Wall','-Wextra','-Werror','nes_native165.c','nes_trace166.c','packed181_host.c','-o','host.exe'],'gcc')
    # Frozen old logical decoder for exact receiver-byte differential, not new RTL.
    ref=a.out/'reference';ref.mkdir()
    for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'):shutil.copyfile(frozen/n,ref/n)
    old=(ROOT/'tests/nes-functional/wire181_host.c').read_text()
    old=replace_once(old,'assert(ok);verify();unsigned extra;',
        'assert(ok);verify();struct nes_native165 copy=S;copy.next_token=0;copy.token_valid=false;FILE *dump=fopen("receiver.bin","wb");assert(dump&&fwrite(&copy,1,sizeof(copy),dump)==sizeof(copy));fclose(dump);unsigned extra;')
    (ref/'host.c').write_text(old)
    run(a.gcc,['-std=c11','-O2','-Wall','-Wextra','-Werror','nes_native165.c','nes_trace166.c','host.c','-o','host.exe'],'gcc',ref)
    cases=[]
    for patches,groups in ((0,1),(1,1),(7,1),(7,32)):
        d=a.out/(f'patch{patches}' if groups==1 else 'maxgroups');d.mkdir();shutil.copytree(a.out/'work',d/'work')
        s=run(a.questa_bin/'vsim.exe',['-c','work.native_spi165_tb',f'-gPATCHES={patches}',f'-gGROUPS={groups}','-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],'rtl',d)
        m=re.search(r'PASS WIRE181RTL patches=(\d+) records=(\d+) blocks=(\d+) wirebytes=(\d+) cycles=(\d+)',s);assert m
        oldcase=next(x for x in metadata['cases'] if x['patches']==patches)
        rp=frozen/f'patch{patches}'/'records.hex';assert sha(rp)==oldcase['records_sha256']
        logical=[int(x,16) for x in rp.read_text().splitlines()]
        if groups==32:
            logical[0]=(logical[0]&~(63<<42))|(32<<42)
            logical[1:34]=[(12<<77)|(i<<64)|3 for i in range(1056)]
            for i,x in enumerate(logical):
                if x>>93==7 and ((x>>64)&8191) in (1,4):logical[i]=x+(1023<<16)
        actual=[int(x,16) for x in (d/'records.hex').read_text().splitlines()]
        expected=encode(logical);assert actual==expected,(patches,next(((i,hex(x),hex(y)) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),None))
        c=run(a.out/'host.exe',[d/'transactions.txt',d/'records.hex',patches],'host',d)
        if groups==1:
            rd=ref/f'patch{patches}';rd.mkdir()
            run(ref/'host.exe',[frozen/f'patch{patches}'/'transactions.txt',rp,patches],'old-host',rd)
            assert (d/'receiver.bin').read_bytes()==(rd/'receiver.bin').read_bytes()
        cases.append(dict(patches=patches,groups=groups,records=int(m[2]),blocks=int(m[3]),wire_bytes=int(m[4]),cycles=int(m[5]),old_wire_bytes=oldcase['wire_bytes'] if groups==1 else None,receiver_sha256=sha(d/'receiver.bin'),checks=int(re.search(r'checks=(\d+)',c)[1])))
        print(m[0],c.strip(),flush=True)
    # ARM object-only: same ABI and stack report, not full firmware approval.
    arm=[]
    for variant,src in [('old',ref),('new',a.out)]:
        d=a.out/f'arm-{variant}';d.mkdir()
        for n in ('nes_native165.c','nes_native165.h','nes_trace166.h'):shutil.copyfile(src/n,d/n)
        (d/'layout.c').write_text('#include "nes_native165.h"\nchar receiver_size[sizeof(struct nes_native165)];\n')
        run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-Wall','-Wextra','-Werror','-c','nes_native165.c','layout.c'],'gcc',d)
        nm=run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','layout.o'],'nm',d)
        arm.append(int(re.search(r'\w+\s+([0-9a-fA-F]+)\s+\w\s+receiver_size',nm)[1],16))
    assert arm==[18064,18064]
    result=dict(passed=True,preparation=prep,cases=cases,arm_struct_bytes=arm,sources=sources,
                generated_sources={p.name:sha(p) for p in a.out.iterdir() if p.suffix in ('.sv','.svh','.c','.h')},
                runner_sha256=sha(Path(__file__)),scope='Actual fill/export/SPI -> actual C; frozen old receiver full bytes exact except transport token. Synthetic query/PSRAM, not collector/game/full board. No FIT/full ARM/physical FPS.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
