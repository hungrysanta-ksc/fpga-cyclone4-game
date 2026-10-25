# SPDX-License-Identifier: MIT
"""Live source receive, causal hint, planner and shared SPI/IRQ on ONE M4 ELF."""
import builtins,inspect,json,os,shutil,struct,sys,textwrap
from pathlib import Path
control='--control' in sys.argv
if control:sys.argv.remove('--control');os.environ['NES367_CONTROL']='1'
observe_miss='--observe-miss' in sys.argv
if observe_miss:sys.argv.remove('--observe-miss')
if '--early-release' not in sys.argv:sys.argv.append('--early-release')
import probe_nes_capture365 as previous
import probe_nes_live287 as live287
import probe_nes_live307 as live307
from nes_hint367 import functional,continuous,COMMON
from nes_delta231 import ROOT,BASE,sha,once
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_PRIMASK
engine=previous.engine
old_prepare=engine.prepare;old_build=engine.build_rom

class Live367(live287.Live):
    phase367=0
    def source_transfer(self,tx,phase):
        assert phase in (1,2);self.phase367=phase
        try:
            result=self.exchange(tx);self.transfers[-1]['source_phase367']=phase;return result
        finally:self.phase367=0

source=textwrap.dedent(live287._s)
source=once(source,'261 if self.checkpoint_mode else 260 if tx is None else len(tx)',
            '(self.phase367*512+len(tx)) if self.phase367 else 261 if self.checkpoint_mode else 260 if tx is None else len(tx)')
source=once(source,"irq_instructions+=row['instructions'];self.next_irq+=10000000",
            "irq_instructions+=row['instructions'];self.exception_cycles+=24;self.next_irq+=10000000")
ns=dict(live287._ns);exec(compile(source,'source367-exchange','exec'),ns);Live367.exchange=ns['exchange']

class ARM367(engine.ARM296):
    def hook(self,uc,address,size,user):
        if address==(self.symbols['source_io367']&~1) and not(
            not self.in_handler and self.pending and self.enabled() and not uc.reg_read(UC_ARM_REG_PRIMASK)):
            self.instructions+=1;self.low_sp=min(self.low_sp,uc.reg_read(UC_ARM_REG_SP))
            p=uc.reg_read(UC_ARM_REG_R0);n=uc.reg_read(UC_ARM_REG_R1);phase=uc.reg_read(UC_ARM_REG_R2)
            assert n<=250 and phase in (1,2)
            tx=bytes(uc.mem_read(p,n)) if n else b'';rx=self.endpoint.source_transfer(tx,phase)
            if n:uc.mem_write(p,rx)
            uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        super().hook(uc,address,size,user)

def build_rom(d):
    old_build(d)
    shutil.copyfile(d/'output.elf',d/'pre367-output.elf');shutil.copyfile(d/'size.log',d/'pre367-size.log')
    p=d/'nes_decode280.c';s=p.read_text()
    s=once(s,'State receiver280;', 'State receiver280;\nuint32_t geometry_groups367;')
    s=once(s,'if(index>=68)return reject();', 'if(index>=68)return reject();\n    if(index<32)geometry_groups367|=UINT32_C(1)<<index;')
    p.write_text(s+'\n'+(ROOT/'tools/nes_source367.c').read_text(),newline='\n')
    p=d/'nes_output264.c';s=p.read_text();s+='\nuint8_t *source_buffer367(void){return wire259;}\n';p.write_text(s,newline='\n')
    p=d/'stubs.s';s=p.read_text();s+='\n.global source_io367\n.thumb_func\nsource_io367:\n bx lr\n';p.write_text(s,newline='\n')
    p=d/'nes_irq284.c';s=p.read_text().replace('Only after a checked E2 response switched the physical pin owner.', 'Only after a checked E2/D4 response selected progress/source-ready ownership.');p.write_text(s,newline='\n')
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    files=['nes_planner285.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_delta231.c',
           'nes_output264.c','nes_refill267.c','nes_irq284.c','nes_bind287.c','nes_native289.c','stubs.s','libgcc.a']
    from probe_nes_refill267 import run
    run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map',*files,'-o','output.elf'],d,'build367')
    run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size367')
    run(arm/'arm-none-eabi-objdump.exe',['-dr','output.elf'],d,'disassembly367')

def worker_source():
    # Preserve the selected planner/serializer worker, replacing its source
    # replay section explicitly. Capture the generated function BEFORE it runs.
    f=live307.original_worker;box=[]
    class Captured(Exception):pass
    def intercept(text,*args,**kwargs):box.append(text);raise Captured()
    env=dict(f.__globals__);env['compile']=intercept
    exec(builtins.compile(inspect.getsource(f),'worker367-template','exec'),env)
    try:env['worker'](Path('unused367'),0)
    except Captured:pass
    assert len(box)==1;return box[0],dict(f.__globals__['old'].previous.__dict__)

def worker(d,last,irq=False,rom=False):
    s,ns=worker_source()
    s=once(s,"('irq_init284','reset259','reset285','reset280')", "('irq_init284','reset259','reset285','reset280','source_reset367')")
    a=s.index("        for b in chunks(records(d/f'frame{f}.records')):");z=s.index('        geom,raw=golden(f);',a)
    s=s[:a]+'''        arm.call('source_policy367',[1 if f<=907 or os.environ.get('NES367_CONTROL')!='1' else 0])
        source_before=arm.instructions
        assert arm.call('source_receive367',[])==1,('source367',f,word('source_error367'))
        source_instructions367=arm.instructions-source_before
        actual_gen=int.from_bytes(arm.uc.mem_read(arm.symbols['receiver280']+14,2),'little')
        assert actual_gen==generation,('received generation',f,actual_gen,generation)
        for name in ('expand286','begin285','geometry_plan286','h2early286'):components[name]=call(name)
        cert=bytes(arm.uc.mem_read(arm.symbols['certificate286'],32))
        assert cert==bytes.fromhex((d/f'prelude{f}.hex').read_text())[16:48]
'''+s[z:]
    s=once(s,'row=dict(service296=', 'row=dict(source_instructions367=source_instructions367,source_blocks367=word("source_blocks367"),source_empty367=word("source_empty367"),source_hints367=word("source_hint_count367"),source_hint_tags367=word("source_hint_tags367"),service296=')
    from nes_bg295 import unbatch as unbatch295
    from nes_bg293 import unbatch
    ns.update(ARM=ARM367,Live=Live367,os=os,unbatch295=unbatch295,unbatch=unbatch)
    (d/'executed-worker367.py').write_text(s,newline='\n')
    exec(compile(s,'worker367','exec'),ns);answer=ns['worker'](d,last,irq,rom)
    import probe_nes_live317 as stamp
    (d/'metadata317.json').write_text(json.dumps(stamp.instances[-1].events317,indent=2)+'\n',newline='\n')
    (d/'calls337.json').write_text(json.dumps(stamp.instances[-1].calls337,indent=2)+'\n',newline='\n')
    return answer

def prepare(*a,**k):
    src,pins=old_prepare(*a,**k);d=a[0];functional(d);continuous(d,a[1])
    if observe_miss:
        # A rejected FINAL next-start remains rejected. Let the current909
        # source/output drain so its missed handoff deadline can be measured.
        # Do not generate another frame or call a missed capture successful.
        assert a[1]==909
        p=d/'joint266_tb.sv';s=p.read_text()
        s=once(s,'if(!capture_begin)$fatal(1,"next capture deadline missed367',
               'if(!capture_begin&&free_id367!=last+1)$fatal(1,"next capture deadline missed367')
        s=once(s,'if(missed367||attempts367!=last-906)$fatal', '''if(missed367)begin : observe_failed_deadline367
     integer fd367;fd367=0;
     while(!fd367)begin #1000;fd367=$fopen("arm-result.json","r");end
     $fclose(fd367);
    end
    if(missed367||attempts367!=last-906)$fatal''')
        p.write_text(s,newline='\n')
    src=list(src)
    for n in COMMON:
        if n not in src:src.append(n)
    pins={k:v for k,v in pins.items() if not k.startswith('shared365/')}
    for n in COMMON:pins['shared367/'+n]=sha(d/n)
    for n in ('nes_hint367.py','probe_nes_hint367.py','nes_source367.c'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    (d/'manifest367.json').write_text(json.dumps(dict(sources=src,control=control,observe_miss=observe_miss,shared_boundary={n:sha(d/n) for n in COMMON}),indent=2)+'\n',newline='\n')
    return src,pins

engine.prepare=prepare;engine.build_rom=build_rom;engine.worker=worker;engine.__file__=__file__
if __name__=='__main__':engine.main()
