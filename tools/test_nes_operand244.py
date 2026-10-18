# SPDX-License-Identifier: MIT
"""Continuous literal lifecycle + observed240 LAPPEND; no full encoder binding."""
from pathlib import Path
import argparse,json,os,random,shutil
from nes_delta231 import ROOT,BASE,sha
from nes_operand243 import reference, instrument240,LAYOUT,FIELDS
from nes_operand244 import assemble
from test_nes_operand243 import run
from observe_nes_literal244 import observe_flush

class Model:
    def __init__(self,entries):
        self.mem=bytearray([165]*512);self.mem[104:128]=bytes(24)
        self.entries=entries;self.vectors=[];self.records=[];self.counts={};self.results={}
    def get(self,n):return int.from_bytes(bytes(self.mem[x] for x in LAYOUT[n]),'little')
    def put(self,n,v):
        v&=(1<<FIELDS[n])-1
        for i,x in enumerate(LAYOUT[n]):self.mem[x]=(v>>(8*i))&255
    def command(self,n,a=0,b=0):
        result=0
        if n in ('init','row_byte','count','mask','dispatch','raw_increment','group_done'):
            self.mem[104:128]=reference(list(self.entries).index(n),a,b,self.mem[104:128])
            # HALT result of old243 routines was not part of its contract.
            result=None
        elif n=='context':self.put('byte_at',a);self.put('old_byte',b)
        elif n=='literal_at':self.put('lit_at',a)
        elif n in ('literal','append'):
            length=self.get('lit_len');old=self.get('old_byte');new=a&255
            if n=='literal' and old==new and not length:pass
            elif n=='literal' and old==new and (self.get('gap')==3 or length==240):result=3
            elif n=='literal' and old!=new and length==240:result=2
            else:
                if not length:self.put('lit_at',self.get('byte_at'))
                self.mem[256+length]=new;self.put('lit_len',length+1)
                if old!=new:self.put('lit_used',length+1);self.put('gap',0)
                else:self.put('gap',self.get('gap')+1)
                if b&1 and old!=new and self.get('cheap_cost')+4+length>=13:
                    for f in ('cheap_cost','lit_len','lit_used','gap'):self.put(f,0)
                    result=1
        elif n=='flush':
            used=self.get('lit_used');cost=self.get('cheap_cost')
            if not used:self.put('lit_len',0);self.put('gap',0)
            elif b&1 and cost+3+used>=13:
                for f in ('cheap_cost','lit_len','lit_used','gap'):self.put(f,0)
                result=1
            else:
                packet=self.get('lit_at').to_bytes(2,'little')+bytes([used])+self.mem[256:256+used]
                if b&1:
                    self.mem[80+cost:80+cost+len(packet)]=packet;self.put('build_i',used-1);self.put('cheap_cost',cost+len(packet))
                else:
                    self.records.append(bytes(packet))
                    if not b&2:self.put('spans',self.get('spans')+1);self.put('expanded',self.get('expanded')+used)
                for f in ('lit_len','lit_used','gap'):self.put(f,0)
        elif n=='raw_append':
            length=self.get('lit_len');assert length<240
            self.mem[256+length]=a&255;self.put('lit_len',length+1);self.put('lit_used',length+1)
        else:raise ValueError(n)
        self.counts[n]=self.counts.get(n,0)+1
        self.results[str(result)]=self.results.get(str(result),0)+1
        h=lambda v:int.from_bytes(v,'little')
        self.vectors.append(f'{self.entries[n]} {a:04x} {b:04x} {result if result is not None else -1} {h(self.mem[104:128]):048x} {h(self.mem[80:92]):024x} {h(self.mem[256:496]):0480x}')
        return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists() and str(d).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    public=['src/nes/rtl/nes_operand244.sv','tools/nes_operand244.py','tools/test_nes_operand244.py','tools/run_nes_operand244.ps1',
            'tests/nes-functional/operand244_base_tb.sv','tests/nes-functional/literal244_tb.sv','tools/observe_nes_literal244.py']
    (d/'source').mkdir()
    for f in public:shutil.copyfile(ROOT/f,d/'source'/Path(f).name)
    words,entries=assemble();kernel=d/'kernel';kernel.mkdir()
    (kernel/'operand244.mem').write_text('\n'.join(f'{v:018b}' for v in words+[0]*(512-len(words)))+'\n')
    (kernel/'entries-base.hex').write_text('\n'.join(f'{v:x}' for v in list(entries.values())+[0]*(32-len(entries)))+'\n')
    shutil.copyfile(BASE/'probes/nes-operand243/test06/kernel/vectors.txt',kernel/'vectors-base.txt')
    for f in (public[0],public[4],public[5]):shutil.copyfile(ROOT/f,kernel/Path(f).name)
    # Continuous state: no direct RF reseeding between these operations.
    model=Model(entries);rng=random.Random(244)
    for kind in range(8):
        model.command('init')
        for i in range(540):
            old=rng.randrange(256);new=old
            if kind==0 or (kind==1 and i%245==0) or (kind==2 and i%4==0) or (kind==3 and i%5==0) or (kind>=4 and rng.randrange(kind+1)==0):new^=81
            model.command('context',2112+i,old)
            result=model.command('literal',new)
            if result in (2,3):
                model.command('flush')
                if result==2:assert model.command('literal',new)==0
        model.command('flush')
    # Cold geometry and raw chunks use identical append storage but only
    # geometry contributes to spans/expanded. Exercise240-byte boundaries.
    for raw in (0,2):
        model.command('init')
        for i in range(701):
            if not model.get('lit_len'):model.command('literal_at',i)
            model.command('raw_append',rng.randrange(64))
            if model.get('lit_len')==240:model.command('flush',0,raw)
        model.command('flush',0,raw)
    # cheap raster records under13 bytes, exact13 expensive fallback and gaps.
    for case in range(48):
        model.command('init');model.command('dispatch',3872,8);model.command('group_done')
        expensive=False
        for i in range(24):
            old=0;new=1 if (i+case)%(case%5+1)==0 else 0
            model.command('context',3872+i,old)
            result=model.command('literal',new,1)
            if result in (2,3):
                if model.command('flush',0,1)==1:expensive=True;break
                if result==2:result=model.command('literal',new,1)
            if result==1:expensive=True;break
            if i%8==7:
                if model.command('flush',0,1)==1:expensive=True;break
        if not expensive:model.command('flush',0,1)
    (kernel/'lifecycle.txt').write_text('\n'.join(model.vectors)+'\n')
    (kernel/'records.txt').write_text('\n'.join(str(len(v))+' '+v.hex(' ') for v in model.records)+'\n')
    # Observe actual240 LAPPEND as an independent equation/data-lifetime check.
    baseline=d/'baseline';baseline.mkdir()
    for f in (BASE/'probes/nes-source242/guards02').glob('case*'):shutil.copyfile(f,baseline/f.name)
    s=instrument240((ROOT/'src/nes/rtl/nes_source_encoder240.sv').read_text())
    s=s.replace('GROUPDONE:op_cmd=6;','GROUPDONE:op_cmd=6;\n    LAPPEND:begin op_cmd=7;op_arg0=new_byte;op_arg1=raster_mode;end')
    s=observe_flush(s)
    (baseline/'nes_source_encoder240.sv').write_text(s,encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'tests/nes-functional/source_encoder240_tb.sv',baseline/'source_encoder240_tb.sv')
    run(baseline,a.questa_bin,'vlib',['work']);run(baseline,a.questa_bin,'vlog',['-sv','nes_source_encoder240.sv','source_encoder240_tb.sv'])
    bt=run(baseline,a.questa_bin,'vsim',['-c','work.source_encoder240_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    assert 'PASS ENCODER240 checks=41 normal=24' in bt
    append=[]
    for line in (baseline/'operations.txt').read_text().splitlines():
        c,av,bv,pre,post=line.split()
        if c!='7':continue
        assert 'x' not in pre+post
        m=Model(entries);m.mem[104:128]=int(pre,16).to_bytes(24,'little');before=m.mem[104:128];length=m.get('lit_len')
        result=m.command('append',int(av,16),int(bv,16));assert m.mem[104:128]==int(post,16).to_bytes(24,'little')
        append.append(f'{av} {bv} {result} {pre} {post} {length}')
    assert len(append)>100
    (kernel/'append.txt').write_text('\n'.join(append)+'\n')
    flush=[];observed_bytes=0;observed_records=0;preserved_x=0
    for line in (baseline/'flush-observed.txt').read_text().splitlines():
        flags,res,pre,post,c0,l0,c1,l1,size,packet=line.split()
        prebytes=[pre[i:i+2] for i in range(0,48,2)][::-1]
        for name in ('lit_used','lit_at','cheap_cost','spans','expanded'):
            for x in LAYOUT[name]:assert 'x' not in prebytes[x-104]
        # Unknowns may only persist unchanged in unmodified fields/payload.
        for old,new in ((pre,post),(c0,c1),(l0,l1)):
            assert len(old)==len(new)
            for i,ch in enumerate(new):
                if ch=='x':assert old[i]=='x';preserved_x+=1
        size=int(size);assert 'x' not in packet[-2*size:] if size else True
        observed_bytes+=size;observed_records+=size!=0
        flush.append(line.replace('x','0'))
    assert len(flush)>100 and observed_records>0
    (kernel/'flush.txt').write_text('\n'.join(flush)+'\n')
    (kernel/'expected_counts.txt').write_text(f'{len(model.vectors)} {len(model.records)} {sum(map(len,model.records))} {len(append)} {len(flush)}\n')
    run(kernel,a.questa_bin,'vlib',['work']);run(kernel,a.questa_bin,'vlog',['-sv','nes_operand244.sv','operand244_base_tb.sv','literal244_tb.sv'])
    summaries=[]
    for top,marker in [('operand244_tb','PASS OPERAND244_BASE'),('literal244_tb','PASS LITERAL244')]:
        log=run(kernel,a.questa_bin,'vsim',['-c','work.'+top,'-do','onerror {quit -code 1}; run -all; quit -f'])
        shutil.copyfile(kernel/'vsim.log',kernel/(top+'.log'));assert marker in log
        summaries += [l for l in log.splitlines() if marker in l]
    pins={f:sha(ROOT/f) for f in public}
    dependencies=['tools/nes_operand243.py','tools/nes_operand242.py','tools/test_nes_operand243.py','src/nes/rtl/nes_source_encoder240.sv','tests/nes-functional/source_encoder240_tb.sv']
    result=dict(passed=True,scope=__doc__,program_words=len(words),entries=entries,continuous_commands=len(model.vectors),commands=model.counts,results=model.results,
        records=len(model.records),record_bytes=sum(map(len,model.records)),actual240_append_samples=len(append),
        actual240_flush_samples=len(flush),actual240_flush_records=observed_records,actual240_flush_bytes=observed_bytes,
        unknown_preserved_nibbles_filled_zero=preserved_x,summaries=summaries,
        pins=pins,dependency_pins={f:sha(ROOT/f) for f in dependencies},program_sha256=sha(kernel/'operand244.mem'),physical=False,full_encoder=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
