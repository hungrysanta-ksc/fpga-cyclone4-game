# SPDX-License-Identifier: MIT
"""Actual exporter + real SPI block/CRC/POP + selected C receiver differential.

Fixture geometry, sequential RTL traces replayed into C. Not live game, board
timing, simultaneous C/RTL/SNES execution, or measured scrolling FPS.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_ingress223 import prepare, ROOT, BASE, sha, once
from test_nes_metadata203 import BENCH


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    prep=prepare(d)
    selected=BASE/'probes/nes-metadata203/test04'
    pins={}
    for i in range(11):
        for ext in ['cfg','mem']:
            f=selected/f'scene{i}.{ext}';shutil.copyfile(f,d/f.name);pins[str(f.relative_to(BASE))]=sha(f)
    # Added full32-group maps use physical tags within512. Nonidentical values
    # model scroll working-set pressure, but are NOT a captured SMB3 scene.
    mem=(d/'scene0.mem').read_text().splitlines()
    assert len(mem)==16384
    patterns={
        'unique':lambda i:(i%512)|((i%4)<<13),
        'repeated':lambda i:17,
        'pairs':lambda i:(i//2)%512,
        'mixed':lambda i:17 if i%37<12 else (i*29)%512,
        'run256':lambda i:(i//256)%512,
    }
    labels={i:f'archived{i}' for i in range(11)}
    for i,(label,fn) in enumerate(patterns.items(),11):
        m=mem.copy()
        for j in range(1056):m[j]=f'{fn(j):016x}'
        (d/f'scene{i}.mem').write_text('\n'.join(m)+'\n')
        cfg=(d/'scene0.cfg').read_text().split();cfg[0]=str((65533+i)&65535);cfg[4]='32'
        (d/f'scene{i}.cfg').write_text(' '.join(cfg)+'\n');labels[i]=label
    # Source upper-bit corruption must ABORT instead of silently truncate.
    bench=BENCH.replace('scene<11','scene<16').replace('fault<=3','fault<=4')
    bench=bench.replace('if(fault==2)begin', "if(fault==4)mem[0]=64'h8000;\n   if(fault==2)begin")
    bench=bench.replace('fault==1?3:fault==2?1:6','(fault==1||fault==4)?3:fault==2?1:6')
    bench=bench.replace('scenes=11 commits=11','scenes=16 commits=16').replace('faults=3','faults=4')
    # Baseline leaves source-invalid words for its checked C decoder, so only
    # the candidate runs the new source-abort assertion.
    (d/'candidate_tb.sv').write_text(bench)
    (d/'baseline_tb.sv').write_text(bench.replace('fault<=4','fault<=3').replace('faults=4','faults=3'))
    original=BASE/'probes/nes-status220/source02/nes_native_export203.sv'
    shutil.copyfile(original,d/'baseline_export.sv')
    c=(BASE/'probes/nes-startup222/arm02/src/nes_native165.c').read_text()
    # Same struct layout; rename only external functions in the baseline TU.
    for x in ['reset','packet','poll','prepare','consumed']:
        c=c.replace('nes_native165_'+x,'baseline_'+x)
    c=c.replace('nes_native181_pixels','baseline_pixels')
    (d/'baseline.c').write_text(c)
    host=ROOT/'tests/nes-functional/ingress223_host.c';shutil.copyfile(host,d/host.name)
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args,label):
        with (d/(label+'.log')).open('wb') as f:
            r=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,
                             timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(label+'.log')).read_text(errors='replace')
        assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-6000:]
        return t
    def q(tool,args,label):return run([a.questa_bin/(tool+'.exe'),*args],label)
    run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fstack-usage',host.name,
         'baseline.c','nes_native165.c','nes_trace166.c','-o','host.exe'],'gcc')
    q('vlib',['work'],'vlib')
    q('vlog',['-sv','baseline_export.sv','baseline_tb.sv'],'baseline-vlog')
    q('vsim',['-c','work.metadata203_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'baseline-vsim')
    for i in range(16):shutil.copyfile(d/f'scene{i}.wire',d/f'baseline{i}.wire')
    q('vlog',['-sv','nes_native_export203.sv','candidate_tb.sv'],'candidate-vlog')
    q('vsim',['-c','work.metadata203_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'candidate-vsim')
    results=[]
    for i in range(16):
        text=run([d/'host.exe',f'baseline{i}.wire',f'scene{i}.wire','records'],f'host{i}')
        m=re.search(r'exact state=(\d+) baseline_bytes=(\d+) candidate_bytes_or_blocks=(\d+)',text);assert m
        results.append(dict(scene=i,label=labels[i],state=int(m[1]),old_bytes=int(m[2]),new_bytes=int(m[3])))
    # Use actual serial endpoint, no bit-banging model substituted. Generation
    # stays explicit; max12B record and original room/CRC/seal rules unchanged.
    spi=(ROOT/'tests/nes-functional/native_spi165_tb.sv').read_text()
    spi=spi.replace('3:width=3','3:width=4').replace('pos=pos+4+width(kind);','pos=pos+4+((kind==0&&(index&4096))?8:width(kind));')
    spi=spi.replace('ag!=12','ag!=records[0][92:77]').replace("request(8'hd3,12,1)","request(8'hd3,records[0][92:77],1)")
    (d/'spi_tb.sv').write_text(spi)
    q('vlog',['-sv','nes_native_spi165.sv','spi_tb.sv'],'spi-vlog')
    serial=[]
    for i in [0,3,11,12,14]:
        records=(d/f'scene{i}.wire').read_text().splitlines();shutil.copyfile(d/f'scene{i}.wire',d/'records.hex')
        t=q('vsim',['-c','work.native_spi165_tb',f'+COUNT={len(records)}','-do','onerror {quit -code 1}; run -all; quit -f'],f'spi{i}')
        assert 'PASS SPI165' in t
        shutil.copyfile(d/'transactions.txt',d/f'spi{i}.transactions.txt')
        h=run([d/'host.exe',f'baseline{i}.wire',f'spi{i}.transactions.txt','serial'],f'spi{i}-host')
        serial.append(dict(scene=i,host=h,rtl=[s for s in t.splitlines() if 'PASS SPI165' in s]))
    r=dict(passed=True,preparation=prep,fixture_pins=pins,public_sources={str(x.relative_to(ROOT)):sha(x) for x in [Path(__file__),host]},
           cases=results,serial=serial,source_abort_faults=4,receiver_faults=14,
           scope=__doc__,physical=False,new_fit=False,new_package=False)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(passed=True,cases=results,serial_scenes=len(serial))))


if __name__=='__main__':main()
