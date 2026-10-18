# SPDX-License-Identifier: MIT
"""Actual240 row/record observations plus random boundaries on shared245 RTL."""
from pathlib import Path
import argparse,json,os,random,shutil
from nes_delta231 import ROOT,BASE,sha
from nes_operand245 import assemble,LAYOUT
from observe_nes_rows245 import observe
from test_nes_operand243 import run
from test_nes_operand244 import Model

PUBLIC=['src/nes/rtl/nes_operand245.sv','tools/nes_operand245.py','tools/observe_nes_rows245.py',
        'tools/test_nes_operand245.py','tools/run_nes_operand245.ps1','tests/nes-functional/rows245_tb.sv']
DEPS=['tools/nes_operand244.py','tools/nes_operand243.py','tools/nes_operand242.py','tools/test_nes_operand243.py',
      'src/nes/rtl/nes_source_encoder240.sv','tests/nes-functional/source_encoder240_tb.sv',
      'tests/nes-functional/literal244_tb.sv','tests/nes-functional/operand244_base_tb.sv','tools/test_nes_operand244.py']

def get(mem,n):return int.from_bytes(bytes(mem[x] for x in LAYOUT[n]),'little')
def put(mem,n,v):
    for i,x in enumerate(LAYOUT[n]):mem[x]=(v>>(8*i))&255

def reference(name,mem,a):
    m=bytearray(mem);packets=[];r=0
    if name=='row_compare':
        old=m[:66];new=m[128:194]
        r=(old==new)|((old[2:]==new[:64])<<1)|((old[:64]==new[2:])<<2)
    elif name in ('mask_compare','mask_set'):
        mask=bytes(m[i]^m[128+i] for i in range(8));put(m,'xor_byte',mask[-1])
        if name=='mask_compare':
            r=int(mask==m[96:104])
            if r and get(m,'rows'):put(m,'rows',get(m,'rows')+1)
        else:m[96:104]=mask;put(m,'rows',1);r=int(any(mask))
    elif name=='row_more':put(m,'rows',get(m,'rows')+1)
    elif name=='shift':
        assert a in (1,255)
        off=192 if a==1 else 128
        packets=[get(m,'row_start').to_bytes(2,'little')+bytes([0,2,a])+m[off:off+2]]
        put(m,'spans',get(m,'spans')+1);put(m,'expanded',get(m,'expanded')+66)
    elif name=='raster':
        packets=[get(m,'group_start').to_bytes(2,'little')+bytes([0,1,get(m,'rows')])+m[96:104]]
        put(m,'spans',get(m,'spans')+1);put(m,'expanded',get(m,'expanded')+get(m,'rows')*8)
    elif name=='cheap':
        at=0;cost=get(m,'cheap_cost');assert cost<13
        while at<cost:
            size=m[80+at+2]+3;assert 4<=size<=12 and at+size<=cost
            packets.append(bytes(m[80+at:80+at+size]));at+=size
            put(m,'build_i',size);put(m,'spans',get(m,'spans')+1);put(m,'expanded',get(m,'expanded')+size-3)
        put(m,'cheap_i',cost)
    else:raise ValueError(name)
    return m,r,packets

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    (d/'source').mkdir()
    for f in PUBLIC+DEPS:shutil.copyfile(ROOT/f,d/'source'/Path(f).name)
    words,entries=assemble();k=d/'kernel';k.mkdir()
    (k/'operand245.mem').write_text('\n'.join(f'{v:018b}' for v in words+[0]*(512-len(words)))+'\n')
    (k/'entries-base.hex').write_text('\n'.join(f'{v:x}' for v in list(entries.values())+[0]*(32-len(entries)))+'\n')
    shutil.copyfile(ROOT/PUBLIC[0],k/'nes_operand245.sv');shutil.copyfile(ROOT/PUBLIC[-1],k/'rows245_tb.sv')
    # Test244 regression uses its SEALED inputs; no new observer or re-generated
    # expected data. Module/file name substitution alone binds it to new245.
    old=BASE/'probes/nes-operand244/test02/kernel'
    for f in ['vectors-base.txt','lifecycle.txt','records.txt','append.txt','flush.txt','expected_counts.txt']:
        shutil.copyfile(old/f,k/f)
    for f in ['operand244_base_tb.sv','literal244_tb.sv']:
        text=(ROOT/'tests/nes-functional'/f).read_text().replace('nes_operand244 dut','nes_operand245 dut')
        (k/f).write_text(text,newline='\n')
    b=d/'baseline';b.mkdir()
    for f in (BASE/'probes/nes-source242/guards02').glob('case*'):shutil.copyfile(f,b/f.name)
    (b/'nes_source_encoder240.sv').write_text(observe((ROOT/DEPS[4]).read_text()),newline='\n')
    shutil.copyfile(ROOT/DEPS[5],b/'source_encoder240_tb.sv')
    run(b,a.questa_bin,'vlib',['work']);run(b,a.questa_bin,'vlog',['-sv','nes_source_encoder240.sv','source_encoder240_tb.sv'])
    text=run(b,a.questa_bin,'vsim',['-c','work.source_encoder240_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    assert 'PASS ENCODER240 checks=41 normal=24' in text
    vectors=[];packets=[];counts={};observed={};x_nibbles=0
    def add(name,mem,arg=0,actual=None):
        post,res,ps=reference(name,mem,arg)
        if actual is not None:
            expected_rf,expected_m,expected_result,expected_bytes=actual
            assert post[104:128]==expected_rf,(name,'RF')
            assert post[96:104]==expected_m,(name,'mask')
            assert res==expected_result,(name,res,expected_result)
            assert b''.join(ps)==expected_bytes,(name,'accepted record bytes')
        h=lambda v:int.from_bytes(v,'little')
        vectors.append(f'{list(entries).index(name)} {arg} {res} {h(mem):01024x} {h(post):01024x}')
        packets.extend(ps);counts[name]=counts.get(name,0)+1
    names=['row_compare','mask_compare','mask_set','shift','raster']
    for line in (b/'rows-observed.txt').read_text().splitlines():
        kind,arg,res,pre,post,o,n,m,m1,size,packet=line.split();name=names[int(kind)];size=int(size)
        # Semantic input bytes must be defined; unknown unused retained bytes
        # may be normalized only if they remain unknown and unchanged.
        required={'row_compare':[], 'mask_compare':[], 'mask_set':[],
                  'shift':['row_start','spans','expanded'],'raster':['group_start','rows','spans','expanded']}[name]
        rb=[pre[i:i+2] for i in range(0,48,2)][::-1]
        for field in required:
            for at in LAYOUT[field]:assert 'x' not in rb[at-104]
        used=66 if name=='row_compare' else 8 if name.startswith('mask') else 0
        assert 'x' not in o[-2*used:]+n[-2*used:] if used else True
        if name in ('mask_compare','raster'):assert 'x' not in m
        if size:assert 'x' not in packet[-2*size:]
        for before,after in [(pre,post),(m,m1)]:
            for x,y in zip(before,after):
                if y=='x':assert x=='x';x_nibbles+=1
        mem=bytearray([165]*512)
        decode=lambda s,length:int(s.replace('x','0'),16).to_bytes(length,'little')
        mem[104:128]=decode(pre,24);mem[:66]=decode(o,66);mem[128:194]=decode(n,66);mem[96:104]=decode(m,8)
        add(name,mem,int(arg),(decode(post,24),decode(m1,8),int(res),decode(packet,13)[:size]))
        observed[name]=observed.get(name,0)+1
    assert all(observed.get(n,0)>0 for n in names),observed
    rng=random.Random(245)
    # Direct branch coverage: unchanged / both shifts / boundary mismatch /
    # repeated/ambiguous rows, all224 legal raster lengths and16-bit wrap.
    for case in range(320):
        mem=bytearray(rng.randbytes(512));mem[104:128]=bytes(24)
        oldrow=bytes(rng.randrange(256) for _ in range(66));newrow=rng.randbytes(66)
        if case%5==0:newrow=oldrow
        elif case%5==1:newrow=oldrow[2:]+rng.randbytes(2)
        elif case%5==2:newrow=rng.randbytes(2)+oldrow[:64]
        elif case%5==3:oldrow=newrow=bytes([case%256])*66
        mem[:66]=oldrow;mem[128:194]=newrow
        put(mem,'row_start',(case%32)*66);put(mem,'group_start',3872+(case%224)*8)
        put(mem,'spans',65535 if case%2 else 255);put(mem,'expanded',65530 if case%3 else 250)
        put(mem,'rows',case%224+1)
        add('row_compare',mem);add('shift',mem,1 if case%2 else 255);add('raster',mem)
        mask=bytes(mem[i]^mem[128+i] for i in range(8));mem[96:104]=mask
        if case%2:mem[96+case%8]^=1
        add('mask_compare',mem);add('mask_set',mem)
        put(mem,'rows',case%223+1);add('row_more',mem)
        sizes=([4,4,4],[5,7],[6,6],[4,5],[12],[],[4,4],[7])[case%8]
        at=0
        for size in sizes:
            mem[80+at:80+at+size]=bytes([case&255,15,size-3])+rng.randbytes(size-3);at+=size
        put(mem,'cheap_cost',at);add('cheap',mem)
    # Continuous row groups reuse the SAME RF/C/L/M state. Only host O/N row
    # input changes between operations; the TB writes it through port A.
    model=Model(entries);chain_commands=0
    def chain(name,av=0,bv=0,first=False):
        nonlocal chain_commands
        pre=bytes(model.mem);before=len(model.records)
        if name in names or name in ('row_more','cheap'):
            model.mem,r,ps=reference(name,model.mem,av);model.records.extend(ps)
        else:r=model.command(name,av,bv)
        h=lambda v:int.from_bytes(v,'little')
        which=list(entries).index(name)+(0 if first else 100)
        # arg1 is carried separately for literal/flush raster mode.
        vectors.append(f'{which} {av|(bv<<16)} {r if r is not None else -1} {h(pre):01024x} {h(model.mem):01024x}')
        packets.extend(model.records[before:]);chain_commands+=1;counts[name]=counts.get(name,0)+1
        return r
    chain('init',first=True);chain('dispatch',3872,8);chain('group_done')
    model.mem[:8]=bytes(8);model.mem[128:136]=bytes([1]*8);chain('mask_set')
    expensive=False
    for row in range(224):
        if row:chain('mask_compare')
        if not expensive:
            for x in range(8):
                chain('context',3872+row*8+x,0)
                if chain('literal',1,1)==1:expensive=True;break
    assert expensive and model.get('rows')==224
    chain('flush',0,1);chain('raster');chain('dispatch',5664,8);chain('group_done')
    # A second group stays cheap and emits two accumulated four-byte records.
    chain('init');chain('dispatch',3872,8);chain('group_done')
    model.mem[:8]=bytes(8);model.mem[128:136]=bytes([1,0,0,0,0,0,0,0]);chain('mask_set')
    for row in range(2):
        if row:chain('mask_compare')
        for x in range(5):
            chain('context',3872+row*8+x,0)
            ret=chain('literal',int(x==0),1)
            if ret==3:chain('flush',0,1)
            else:assert ret==0
    chain('flush',0,1);assert model.get('cheap_cost')==8;chain('cheap');chain('group_done')
    (k/'rows.txt').write_text('\n'.join(vectors)+'\n')
    (k/'rows-records.txt').write_text('\n'.join(str(len(v))+' '+v.hex(' ') for v in packets)+'\n')
    (k/'rows-counts.txt').write_text(f'{len(vectors)} {len(packets)} {sum(map(len,packets))}\n')
    run(k,a.questa_bin,'vlib',['work']);run(k,a.questa_bin,'vlog',['-sv','nes_operand245.sv','operand244_base_tb.sv','literal244_tb.sv','rows245_tb.sv'])
    summaries=[]
    for top,marker in [('operand244_tb','PASS OPERAND244_BASE'),('literal244_tb','PASS LITERAL244'),('rows245_tb','PASS ROWS245')]:
        text=run(k,a.questa_bin,'vsim',['-c','work.'+top,'-do','onerror {quit -code 1}; run -all; quit -f'])
        shutil.copyfile(k/'vsim.log',k/(top+'.log'));assert marker in text
        summaries += [s for s in text.splitlines() if marker in s or 'ROW245 entry=' in s]
    result=dict(passed=True,scope=__doc__,program_words=len(words),entries=entries,observed240=observed,
        cases=len(vectors),counts=counts,chain_commands=chain_commands,records=len(packets),record_bytes=sum(map(len,packets)),summaries=summaries,
        unknown_unused_nibbles=x_nibbles,pins={f:sha(ROOT/f) for f in PUBLIC},dependency_pins={f:sha(ROOT/f) for f in DEPS},
        program_sha256=sha(k/'operand245.mem'),physical=False,full_encoder=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
