# SPDX-License-Identifier: MIT
"""NES242 register initialization observer on unchanged240 synthetic guards."""
from pathlib import Path
import argparse,json,os,random,re,shutil,subprocess
from nes_delta231 import ROOT,sha
from nes_stream234 import encode
from nes_operand242 import FIELDS, instrument

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
    a=p.parse_args();d=a.out.resolve();assert not d.exists() and str(d).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    rng=random.Random(237);old=bytes(5741);vectors=[]
    for c in range(24):
        new=bytearray(old)
        if c==0 or c%5==0:new[:]=rng.randbytes(5741)
        elif c%5==1:
            for off in range(0,2112,66):new[off:off+66]=old[off+2:off+66]+rng.randbytes(2)
        elif c%5==2:
            for off in range(0,2112,66):new[off:off+66]=rng.randbytes(2)+old[off:off+64]
        elif c%5==3:
            for row in range(224):
                at=3872+row*8;mask=0x01010101010101 if row<40 else 0 if row<90 else 1 if row<160 else rng.getrandbits(64)
                new[at:at+8]=(int.from_bytes(old[at:at+8],'little')^mask).to_bytes(8,'little')
        else:
            for off in (2112,2115,2119,2124,2351,2352,2355,3871,3872,5663,5664,5740):new[off]^=0x51
        serial=c+1 if c<20 else (256,65536,0x80000000,0xfffffffe)[c-20]
        raw=bytes(rng.randrange(64) for _ in range((c%8)*256));rr,_=encode(old,bytes(new),raw,serial,(65535+c)&65535)
        (d/f'case{c}.serial').write_text(f'{serial:08x}\n')
        (d/f'case{c}.geometry').write_text(new.hex(' ')+'\n')
        (d/f'case{c}.raw').write_text((raw+bytes(1792-len(raw))).hex(' ')+'\n')
        (d/f'case{c}.expected').write_text(str(len(rr))+'\n'+'\n'.join(str(len(b))+' '+b.hex(' ') for b in rr)+'\n')
        vectors.append(dict(case=c,serial=serial,records=len(rr),bytes=sum(map(len,rr))))
        old=bytes(new)
    files=[ROOT/'src/nes/rtl/nes_source_encoder240.sv',ROOT/'tests/nes-functional/source_encoder240_tb.sv']
    for f in files:shutil.copyfile(f,d/f.name)
    enc=d/'nes_source_encoder240.sv'
    (d/'encoder240.original.sv').write_bytes(enc.read_bytes())
    observed,inv=instrument(enc.read_text())
    enc.write_text(observed,encoding='utf-8',newline='\n')
    (d/'observer').mkdir()
    for name in ('nes_operand242.py','test_nes_operand242.py','run_nes_source242.ps1'):
        shutil.copyfile(ROOT/'tools'/name,d/'observer'/name)
    for name,args in [('vlib',['work']),('vlog',['-sv',*[f.name for f in files]]),('vsim',['-c','work.source_encoder240_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
        with (d/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
    assert 'PASS ENCODER240 checks=41 normal=24' in t
    # A negative for the observer, not a production mutation: intentionally
    # omit the IDLE initialization mark for lit_len. Its register still gets
    # the original value; the lifetime checker must reject the missing proof.
    negative=d/'negative';negative.mkdir()
    for f in d.iterdir():
        if f.is_file() and f.suffix not in ('.log',):shutil.copyfile(f,negative/f.name)
    marker=f'prof_writes[{list(FIELDS).index("lit_len")}]=1;'
    at=observed.index('    IDLE:if(start)begin');end=observed.index('    HEADER:',at)
    before=observed[at:end];assert before.count(marker)==1
    damaged=observed[:at]+before.replace(marker,'/* deliberately missing initialization mark */')+observed[end:]
    (negative/enc.name).write_text(damaged,encoding='utf-8',newline='\n')
    for name,args in [('vlib',['work']),('vlog',['-sv',*[f.name for f in files]]),('vsim',['-c','work.source_encoder240_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
        with (negative/(name+'.log')).open('wb') as log:
            q=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=negative,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        neg=(negative/(name+'.log')).read_text(errors='replace')
        if name=='vsim':
            # Questa may exit0 after $fatal+$finish in a run-all script. The
            # expected fatal and absence of normal completion are decisive.
            assert '** Fatal: OPERAND242 uninitialized state=6' in neg and 'PASS ENCODER240' not in neg,neg[-4000:]
        else:assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',neg),neg[-4000:]
    result=dict(passed=True,scope=__doc__,vectors=vectors,summary=[s for s in t.splitlines() if 'ENCODER240 ' in s or 'VIEWS240 ' in s],
        missing_initialization_negative_rejected=True,
        observer_sha256=sha(ROOT/'tools/nes_operand242.py'),instrumented_sha256=sha(enc),
        pins={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in files},runner_sha256=sha(Path(__file__)),physical=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(result['summary']))
if __name__=='__main__':main()
