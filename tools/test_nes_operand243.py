# SPDX-License-Identifier: MIT
"""Sample actual240 operations and replay prepared RF fixtures on unbound243."""
from pathlib import Path
import argparse,json,os,random,re,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha
from nes_operand243 import assemble,instrument240,reference,LAYOUT,FIELDS

def run(d,q,name,args):
    with (d/(name+'.log')).open('wb') as log:
        p=subprocess.run([str(q/(name+'.exe')),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    t=(d/(name+'.log')).read_text(errors='replace')
    assert p.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-6000:]
    return t

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    files=['src/nes/rtl/nes_operand243.sv','tests/nes-functional/operand243_tb.sv','tools/nes_operand243.py','tools/test_nes_operand243.py',
           'tools/run_nes_operand243.ps1','src/nes/rtl/nes_source_encoder240.sv','tests/nes-functional/source_encoder240_tb.sv']
    pins={f:sha(ROOT/f) for f in files}
    snap=d/'source';snap.mkdir()
    for f in files:shutil.copyfile(ROOT/f,snap/Path(f).name)
    baseline=d/'baseline';baseline.mkdir()
    old=BASE/'probes/nes-source242/guards02'
    for f in old.glob('case*'):shutil.copyfile(f,baseline/f.name)
    assert len(list(baseline.glob('case*.geometry')))==24
    encoder=ROOT/'src/nes/rtl/nes_source_encoder240.sv'
    (baseline/encoder.name).write_text(instrument240(encoder.read_text()),encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'tests/nes-functional/source_encoder240_tb.sv',baseline/'source_encoder240_tb.sv')
    run(baseline,a.questa_bin,'vlib',['work']);run(baseline,a.questa_bin,'vlog',['-sv',encoder.name,'source_encoder240_tb.sv'])
    bt=run(baseline,a.questa_bin,'vsim',['-c','work.source_encoder240_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    assert 'PASS ENCODER240 checks=41 normal=24' in bt
    counts=[0]*7;vectors=[];unknown_preserved_bytes=0
    read_fields={0:[],1:['row_start'],2:['spans','expanded'],3:[],4:[],5:['lit_len'],6:['row_start']}
    write_fields={0:['row_start','lit_at','lit_len','lit_used','gap','cheap_cost','rows','spans','expanded','build_i','raw_limit','row_size'],
                  1:['byte_at','old_byte'],2:['spans','expanded'],3:['xor_byte'],4:['row_start','row_size'],5:['lit_len','lit_used'],
                  6:['cheap_cost','lit_len','lit_used','gap','rows','group_start']}
    for line in (baseline/'operations.txt').read_text().splitlines():
        c,av,bv,pre,post=line.split();c=int(c);av=int(av,16);bv=int(bv,16)
        prebytes=[pre[i:i+2] for i in range(0,48,2)][::-1];postbytes=[post[i:i+2] for i in range(0,48,2)][::-1]
        for name in read_fields[c]:
            for x in LAYOUT[name]:assert 'x' not in prebytes[x-104],('unknown semantic input',c,name,line)
        written={x-104 for name in write_fields[c] for x in LAYOUT[name]}
        if c==6 and int(prebytes[1]+prebytes[0],16)==5664:written-={x-104 for x in LAYOUT['group_start']}
        for i,s in enumerate(postbytes):
            if 'x' in s:
                assert i not in written and s==prebytes[i],('unknown written result',c,i,line)
                unknown_preserved_bytes+=1
        before=bytes(int(s.replace('x','0'),16) for s in prebytes);after=bytes(int(s.replace('x','0'),16) for s in postbytes)
        assert reference(c,av,bv,before)==after,('observer/reference disagreement',c,line)
        vectors.append(f'{c} {av:04x} {bv:04x} {int.from_bytes(before,"little"):048x} {int.from_bytes(after,"little"):048x}');counts[c]+=1
    assert all(counts),counts
    rng=random.Random(243)
    # Boundary/carry/13-bit truncation and randomized nonzero preserved fields.
    for c in range(7):
        for k in range(256):
            before=bytearray(rng.randbytes(24))
            for name,addresses in LAYOUT.items():
                v=int.from_bytes(bytes(before[x-104] for x in addresses),'little')&((1<<FIELDS[name])-1)
                if k<8 and name in ('spans','expanded','row_start','lit_len'):v=(0,1,254,255,256,8191,65534,65535)[k]&((1<<FIELDS[name])-1)
                if name=='row_start' and k%4==0:v=5664
                for i,x in enumerate(addresses):before[x-104]=(v>>(i*8))&255
            av=rng.randrange(65536);bv=rng.randrange(65536);after=reference(c,av,bv,before)
            vectors.append(f'{c} {av:04x} {bv:04x} {int.from_bytes(before,"little"):048x} {int.from_bytes(after,"little"):048x}')
    kernel=d/'kernel';kernel.mkdir()
    words,entries=assemble()
    (kernel/'operand243.mem').write_text('\n'.join(f'{w:018b}' for w in words+[0]*(512-len(words)))+'\n')
    (kernel/'entries.hex').write_text('\n'.join(f'{v:x}' for v in entries.values())+'\n')
    (kernel/'vectors.txt').write_text('\n'.join(vectors)+'\n')
    for f in files[:2]:shutil.copyfile(ROOT/f,kernel/Path(f).name)
    run(kernel,a.questa_bin,'vlib',['work']);run(kernel,a.questa_bin,'vlog',['-sv','nes_operand243.sv','operand243_tb.sv'])
    kt=run(kernel,a.questa_bin,'vsim',['-c','work.operand243_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    assert 'PASS OPERAND243 ' in kt
    result=dict(passed=True,scope=__doc__,actual240_sampled_by_command=counts,randomized_vectors=1792,total_vectors=len(vectors),
        unknown_unread_preserved_bytes_filled_zero=unknown_preserved_bytes,
        program_words=len(words),entries=entries,program_sha256=sha(kernel/'operand243.mem'),pins=pins,
        baseline_summary=[x for x in bt.splitlines() if 'ENCODER240 ' in x or 'VIEWS240 ' in x],
        kernel_summary=[x for x in kt.splitlines() if 'PASS OPERAND243' in x],full_encoder=False,physical=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
