# SPDX-License-Identifier: MIT
"""Deployed exporter/fill + deployed CDC -> bulk aperture; query/memory fixture.

Not a live PPU/game, new SNES CPU client, physical CDC timing or FPS proof.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(records):
    out=bytearray();widths=[2,1,7,4,7,1,2,8]
    for v in records:
        k=v>>93;idx=(v>>64)&8191;g=(v>>77)&65535;n=widths[k]
        out.extend(((k<<13)|idx).to_bytes(2,'big'));out.extend(g.to_bytes(2,'big'))
        value=v&((1<<64)-1);assert value<(1<<(8*n))
        out.extend(value.to_bytes(n,'big'))
    return bytes(out)
def main():
    p=argparse.ArgumentParser()
    for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02'
    baseline=ROOT.parent/'probes/nes-packed181/evidence/test02';pins={}
    names=['nes_native_export181.sv','nes_native_fill165.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv']
    for n in names:
        shutil.copyfile(board/n,a.out/n);pins[(board/n).relative_to(ROOT.parent).as_posix()]=sha(board/n)
    for n in ['src/nes/rtl/nes_bulk_aperture188.sv','src/nes/rtl/nes_source_bulk189.sv','tests/nes-functional/source_bulk189_tb.sv']:
        shutil.copyfile(ROOT/n,a.out/Path(n).name);pins[n]=sha(ROOT/n);names.append(Path(n).name)
    source=baseline/'wire181_source.svh';s=source.read_text();pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
    old="if(data[95:93]==7&&data[76:64]==2)$fatal(1,\"unexpected ABORT %x\",data);"
    assert old in s;s=s.replace(old,'// ABORT is expected in the injected source-fault case.')
    old=".response(er),.hit(1'b1),.data(ed)";assert old in s
    s=s.replace(old,".response(er),.hit(!(FAULT&&ek==7&&ei==16)),.data(ed)")
    old='6:fixture=i==3||i==7?1:i==5?2:0;';assert old in s
    s=s.replace(old,'6:fixture=LARGE?(i<512?1:0):(i==3||i==7?1:i==5?2:0);')
    (a.out/'wire181_source.svh').write_text(s,encoding='utf8')
    def run(exe,args,name,d=a.out):
        with (d/(name+'.log')).open('wb') as f:
            q=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(name+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
        return t
    run('vlib',['work'],'vlib');run('vlog',['-sv',*names],'vlog')
    cases=[]
    for tag,patches,groups,fault,large in [('patch0',0,1,0,0),('maxgroups',7,32,0,0),('late_fault',7,1,1,0),('pressure512',0,1,0,1)]:
        d=a.out/tag;d.mkdir();shutil.copytree(a.out/'work',d/'work')
        t=run('vsim',['-c','work.source_bulk189_tb',f'-gPATCHES={patches}',f'-gGROUPS={groups}',f'-gFAULT={fault}',f'-gLARGE={large}','-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],'rtl',d)
        m=re.search(r'PASS SOURCE189 bytes=(\d+) chunks=(\d+) records=(\d+) stalls=(\d+) commit=(\d+) abort=(\d+)',t);assert m
        records=[int(x,16) for x in (d/'records.hex').read_text().split()]
        data=bytes(int(x,16) for x in (d/'read.hex').read_text().split())
        assert data==encode(records)
        if not fault and not large:
            old=baseline/tag/'records.hex';pins[old.relative_to(ROOT.parent).as_posix()]=sha(old)
            assert records==[int(x,16) for x in old.read_text().split()],tag
        if fault:assert (records[-1]>>93,(records[-1]>>64)&8191)==(7,2)
        full=int(re.search(r'FULL_SLOT_WAIT hostcycles=(\d+)',t)[1])
        if large:assert full>0 and len(data)>4096
        assert int(m[4])>0
        cases.append(dict(name=tag,bytes=int(m[1]),chunks=int(m[2]),records=int(m[3]),stalled_source_cycles=int(m[4]),full_slot_wait_host_cycles=full,commits=int(m[5]),aborts=int(m[6]),read_sha256=sha(d/'read.hex')))
    result=dict(passed=True,cases=cases,source_pins=pins,query_fixture_sha256=sha(a.out/'wire181_source.svh'),scope=__doc__,new_firmware=False,new_fit=False,new_package=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'},indent=2))
if __name__=='__main__':main()
