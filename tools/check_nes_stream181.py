# SPDX-License-Identifier: MIT
"""Native codec/cost checks and paired ARM object stack; not full ARM runtime."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
from nes_stream181 import sink,ROOT
from test_nes_sinkpack181 import packets as old_packets


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def wire(d):
    data={};stats={}
    for p in sorted(d.glob('req-*.bin')):
        b=p.read_bytes();u=lambda i:int.from_bytes(b[i:i+2],'little')
        gen=u(8);q=stats.setdefault(gen,dict(packets=0,request_bytes=0,long_packets=0))
        q['packets']+=1;q['request_bytes']+=len(b)
        assert len(b)==16+u(12)
        if b[0] not in (2,4,5):continue
        if b[0]>=4:
            assert u(12)==2 and u(14)%2==0
            assert (4<=u(14)<=240) if b[0]==4 else (242<=u(14)<=4096)
            payload=b[16:]*(u(14)//2);q['long_packets']+=b[0]==5
        else:assert u(14)==0;payload=b[16:]
        dst=data.setdefault((gen,b[1]),bytearray());assert len(dst)==u(10);dst.extend(payload)
    for q in stats.values():
        q['minimum_spi_bytes']=q['request_bytes']+q['packets']*35
        q['minimum_spi_ms']=q['minimum_spi_bytes']*8/2625000*1000+q['packets']*.024
    return data,stats


def main():
    p=argparse.ArgumentParser()
    for n in ('out','gcc','arm_gcc','fixtures','normal','old_normal'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    files=['nes_native_sink165.h','nes_sink_trace168.h','nes_sink_trace168.c']
    for n in files:shutil.copyfile(a.fixtures/n,a.out/n)
    for src,dest in [('nes_native181.h','nes_native165.h'),('nes_native_video181.h','nes_native_video165.h')]:
        shutil.copyfile(ROOT/'src/nes/firmware'/src,a.out/dest)
    (a.out/'nes_native_sink165.c').write_text(sink((ROOT/'src/nes/firmware/nes_native_sink181.c').read_text()),encoding='utf8',newline='\n')
    shutil.copyfile(ROOT/'tests/nes-functional/stream181_codec.c',a.out/'codec.c')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args,name):
        with (a.out/name).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(a.out/name).read_text(errors='replace')
    run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','codec.c','nes_sink_trace168.c','-o','codec.exe'],'gcc.log')
    run([a.out/'codec.exe'],'codec.log')
    run([a.arm_gcc,'-std=gnu11','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-Wall','-Wextra','-Werror','-c','nes_native_sink165.c','-o','nes_native_sink165.o'],'arm.log')
    new,stats=wire(a.normal);old,_=old_packets(a.old_normal);assert new==old
    assert (a.normal.parent/'nes_native_sink165.c').read_bytes()==(a.out/'nes_native_sink165.c').read_bytes()
    result=dict(passed=True,scope=__doc__,codec=(a.out/'codec.log').read_text().strip(),
        logical_bytes=sum(map(len,new.values())),frames=stats,stack=(a.out/'nes_native_sink165.su').read_text(),
        source_sha256={n:sha(ROOT/n) for n in ['tools/nes_stream181.py','tests/nes-functional/stream181_codec.c','tools/check_nes_stream181.py']},
        candidate_C_sha256=sha(a.out/'nes_native_sink165.c'),full_ARM=False,physical_FPS=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
