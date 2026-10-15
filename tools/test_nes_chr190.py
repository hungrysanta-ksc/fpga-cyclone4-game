# SPDX-License-Identifier: MIT
"""190 tile batching through deployed exporter/fill/CDC and raw cartridge bus.
Synthetic queries, not whole game, SNES CPU, physical timing or FPS proof.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from test_nes_source189 import encode as encode189
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode190(records):
    out=bytearray();i=0
    while i<len(records):
        v=records[i];k=v>>93;idx=(v>>64)&8191
        if k==6:
            group=records[i:i+16];assert len(group)==16
            g=(v>>77)&65535;kind=(v>>12)&3;assert kind
            for lane,q in enumerate(group):
                assert q>>64==v>>64 and (q&((1<<64)-1))>>8==(kind<<4)|lane
            out.extend(((6<<13)|idx).to_bytes(2,'big'));out.extend(g.to_bytes(2,'big'))
            out.extend((kind,0));out.extend(q&255 for q in group);i+=16
        else:
            if k==7 and idx==0:
                assert (v>>48)&65535==0x1813
                v=(v&~(65535<<48))|(0x1901<<48)
            out.extend(encode189([v]));i+=1
    return bytes(out)
def main():
    p=argparse.ArgumentParser()
    for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    frozen=ROOT.parent/'probes/nes-source189/test02';pins={}
    def copy(src,name=None):
        name=name or src.name;shutil.copyfile(src,a.out/name)
        pins[str(src.relative_to(ROOT.parent)).replace('\\','/')]=sha(src)
    names=['nes_native_export181.sv','nes_native_fill165.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv']
    for n in names:copy(frozen/n)
    for n in ('nes_bulk_aperture188.sv','nes_source_bulk190.sv'):
        copy(ROOT/'src/nes/rtl'/n);names.append(n)
    copy(frozen/'wire181_source.svh')
    tb=frozen/'source_bulk189_tb.sv';pins['frozen_bench']=sha(tb)
    s=tb.read_text().replace('source_bulk189_tb','chr190_tb').replace('nes_source_bulk189 bridge','nes_source_bulk190 bridge')
    s=s.replace('repeat(LARGE?100000:16000)','repeat(LARGE?300000:16000)')
    s=s.replace('case(kind)0,6:width=2;','case(kind)0:width=2;6:width=18;')
    s=s.replace('PASS SOURCE189','PASS CHR190')
    (a.out/'chr190_tb.sv').write_text(s,encoding='utf8',newline='\n');names.append('chr190_tb.sv')
    def run(exe,args,label,d=a.out):
        env=os.environ.copy();env['PATH']=str(Path(exe).parent)+os.pathsep+env.get('PATH','')
        with (d/(label+'.log')).open('wb') as f:
            q=subprocess.run([str(exe),*map(str,args)],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(label+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
        return t
    run(a.questa_bin/'vlib.exe',['work'],'vlib');run(a.questa_bin/'vlog.exe',['-sv',*names],'vlog')
    arm=ROOT.parent/'probes/nes-paired186/arm01/src'
    for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'):copy(arm/n)
    copy(ROOT/'tests/nes-functional/chr190_host.c')
    gcc=a.questa_bin.parent/'gcc-7.4.0-mingw64vc16/bin/gcc.exe'
    run(gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','chr190_host.c','nes_native165.c','nes_trace166.c','-o','host.exe'],'gcc')
    cases=[]
    for tag,patches,groups,fault,large in [('patch0',0,1,0,0),('maxgroups',7,32,0,0),('late_fault',7,1,1,0),('pressure512',0,1,0,1)]:
        d=a.out/tag;d.mkdir();shutil.copytree(a.out/'work',d/'work')
        t=run(a.questa_bin/'vsim.exe',['-c','work.chr190_tb',f'-gPATCHES={patches}',f'-gGROUPS={groups}',f'-gFAULT={fault}',f'-gLARGE={large}','-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],'rtl',d)
        m=re.search(r'PASS CHR190 bytes=(\d+) chunks=(\d+) records=(\d+) stalls=(\d+) commit=(\d+) abort=(\d+)',t);assert m
        records=[int(x,16) for x in (d/'records.hex').read_text().split()]
        old=frozen/tag/'records.hex';pins[f'189/{tag}/records.hex']=sha(old)
        assert records==[int(x,16) for x in old.read_text().split()]
        data=bytes(int(x,16) for x in (d/'read.hex').read_text().split());assert data==encode190(records)
        oldbytes=encode189(records)
        (d/'old.hex').write_text(''.join(f'{b:02x}\n' for b in oldbytes),encoding='ascii')
        c=None
        if not fault and not large:
            c=run(a.out/'host.exe',[d/'old.hex',d/'read.hex'],'host',d).strip();assert 'PASS CHR190C' in c
        full=int(re.search(r'FULL_SLOT_WAIT hostcycles=(\d+)',t)[1])
        if large:assert full>0
        cases.append(dict(name=tag,old_bytes=len(oldbytes),bytes=len(data),chunks=int(m[2]),records=len(records),full_wait_host_cycles=full,commits=int(m[5]),aborts=int(m[6]),receiver=c))
    neg=ROOT/'tests/nes-functional/chr190_faults_tb.sv';copy(neg)
    run(a.questa_bin/'vlog.exe',['-sv',neg.name],'fault-vlog')
    t=run(a.questa_bin/'vsim.exe',['-c','work.chr190_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'fault-rtl')
    assert 'PASS CHR190FAULT cases=10' in t
    pins['runner']=sha(Path(__file__));pins['encode189']=sha(ROOT/'tools/test_nes_source189.py')
    result=dict(passed=True,cases=cases,negative_cases=10,source_pins=pins,generated_bench_sha256=sha(a.out/'chr190_tb.sv'),scope=__doc__,new_firmware=False,new_fit=False,new_package=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'},indent=2))
if __name__=='__main__':main()
