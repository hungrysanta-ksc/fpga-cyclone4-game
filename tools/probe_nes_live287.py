# SPDX-License-Identifier: MIT
"""Actual row planner -> credited E9 refill with live ARM/IRQ/ROM/receipt.

Source decoder/control instruction replay and ordinary command templates remain
fixtures. Planner material and E9 bytes are produced in this same M4 ELF. Source
decoder executes for material but is excluded here because source already pays
its separately measured instruction replay. CPI/exception costs are allocations.
"""
import inspect,json,shutil,struct,time,binascii,textwrap
from pathlib import Path
import probe_nes_refill284 as prior
import probe_nes_refill267 as old
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint286 import apply as identity
from nes_joint287 import apply
from probe_nes_decode280 import records,chunks,golden
from probe_nes_split274 import verify
from probe_nes_arm264 import ARM as BaseARM
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE

class ARM(prior.ARM):
    def __init__(self,elf,endpoint):
        self.pending=False;self.in_handler=False;self.action=None;self.exti=[];self.mmio=[];self.pr=0
        BaseARM.__init__(self,elf,endpoint)
        self.uc.mem_map(0x40000000,0x4000000);self.uc.mem_map(0xe0000000,0x100000)
        # Unfiltered data hooks trigger a Unicorn IT-state defect in the decoder.
        # Only peripheral addresses belong to this MMIO adapter.
        self.uc.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,self.memory,begin=0x40000000,end=0x43ffffff)
        self.uc.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,self.memory,begin=0xe0000000,end=0xe00fffff)

class Live(prior.Live):
    checkpoint_mode=False
    def checkpoint(self):
        self.checkpoint_mode=True
        try:return self.exchange(b'')
        finally:self.checkpoint_mode=False

# Same exchange, with a non-SPI/non-WFI cooperative hardware checkpoint.
_s=inspect.getsource(prior.Live.exchange)
_s=_s.replace('260 if tx is None else len(tx)','261 if self.checkpoint_mode else 260 if tx is None else len(tx)')
_s=_s.replace('wait284=tx is None,','checkpoint287=self.checkpoint_mode,wait284=tx is None,')
_ns=dict(prior.__dict__);exec(compile(textwrap.dedent(_s),'exchange287','exec'),_ns);Live.exchange=_ns['exchange']

def prepare(*args,**kwargs):
    src,pins=prior.prepare(*args,**kwargs);d=args[0];identity(d);apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'     if(n267==260)begin', '     if(n267==261)begin $fwrite(events261,"checkpoint287,%0d,%0t,%0d\\n",f,$time,delay267);end\n     else if(n267==260)begin')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_bridge267.c';s=p.read_text().replace('count>260','count>261').replace('count==260?0:count','count>=260?0:count');p.write_text(s)
    for n in ('nes_joint286.py','nes_joint287.py','nes_bind287.c','probe_nes_live287.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins

def build_rom(d):
    prior.build_rom(d)
    p=d/'nes_refill267.c';s=p.read_text().replace('extern void wait284(void);','extern void wait284(void);\nextern unsigned prefill_active287;').replace('if(wait_armed284)wait284();','if(wait_armed284&&!prefill_active287)wait284();').replace('if(command==0xe2&&wait_armed284)wait284();','if(command==0xe2&&wait_armed284&&!prefill_active287)wait284();');p.write_text(s)
    # Build from the source transformer, not mutable artifacts from a previous run.
    import probe_nes_planner287 as planner
    q=d/'planner-build';q.mkdir();planner.build(q)
    sources=['nes_planner285.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_delta231.c']
    for p in q.iterdir():
        if p.suffix in ('.h','.inc') or p.name in sources+['nes_decode280.c','libgcc.a']:shutil.copyfile(p,d/p.name)
    p=d/'nes_output264.c';s=p.read_text()
    s='#include "nes_delta231.h"\nextern struct nes_native_video165 video285;\n'+s
    s=once(s,'const uint8_t *h=material259+5152;', 'const uint8_t *h=video285.hdma,*raw287=video285.patch.mode[0],*sizes287=(const uint8_t *)video285.patch.size;')
    # Native patch has one alignment byte before size[]. Preserve exact packed
    # 249-byte CRC semantics by explicitly skipping that byte.
    for before,after in [('h[3169+at]','raw287[at]'),('h+3170+at','raw287+1+at'),('h[3250+at]','raw287[81+at]'),('h[3331+at]','raw287[162+at]'),('h+3251+at','raw287+82+at'),('h+3172+at','raw287+3+at'),('h+3253+at','raw287+84+at'),('h+3332+at','raw287+163+at'),('h+3334+at','raw287+165+at'),('h+3412+i*2','sizes287+i*2'),('h[3169+i]','(i<243?raw287[i]:sizes287[i-243])')]:
        assert before in s,before;s=s.replace(before,after)
    p.write_text(s,encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'tools/nes_bind287.c',d/'nes_bind287.c')
    arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    old.run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map',*sources,'nes_output264.c','nes_refill267.c','nes_irq284.c','nes_bind287.c','stubs.s','libgcc.a','-o','output.elf'],d,'build287')
    old.run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size287')
    old.run(arm/'arm-none-eabi-objdump.exe',['-dr','output.elf'],d,'disassembly287')

def worker(d,last,irq=False,rom=False):
    assert rom
    ep=Live(d,irq);arm=ARM(d/'output.elf',ep);ep.arm=arm
    def word(name):return struct.unpack('<I',arm.uc.mem_read(arm.symbols[name],4))[0]
    def call(name,args=[]):
        before=arm.instructions;ok=arm.call(name,args);assert ok,(name,word('expansion_error286'));return arm.instructions-before
    arm.symbols['io259']=arm.symbols['physical267']
    for name in ('irq_init284','reset259','reset285','reset280'):arm.call(name,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    oracle,groups=old.plans();rows=[]
    for f in range(905,last+1):
        deadline=time.monotonic()+600
        while not (d/f'arm-frame{f}').exists():
            if time.monotonic()>deadline:raise TimeoutError(f'frame {f}')
            time.sleep(.01)
        pp=groups[f-904];generation=old.u16(pp[0],8);blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp)
        arm.uc.mem_write(0x20010000,blob)
        start=len(ep.transfers);sent=len(ep.packets);before=arm.instructions;decoder=0;preview=False;components={}
        for b in chunks(records(d/f'frame{f}.records')):
            arm.uc.mem_write(0x20028000,b)
            n=call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)]);decoder+=n;ep.before+=n
            if not preview and arm.call('geometry_ready286',[]):
                for name in ('expand286','begin285','geometry_plan286','h2early286'):components[name]=call(name)
                cert=bytes(arm.uc.mem_read(arm.symbols['certificate286'],32))
                assert cert==bytes.fromhex((d/f'prelude{f}.hex').read_text())[16:48]
                preview=True
        geom,raw=golden(f);assert bytes(arm.uc.mem_read(arm.symbols['history286'],4910))==geom+raw
        for name in ('input_commit286','begin_step286'):components[name]=call(name)
        arm.call('seed287',[generation]);ep.checkpoint();steps=[];prefills=0;last_size=0
        while True:
            at=arm.instructions;ok=arm.call('next_step286',[]);assert ok;steps.append(arm.instructions-at)
            n=word('output_size285')
            if n!=last_size:call('prefill287');prefills+=1;last_size=n
            ep.checkpoint()
            if ok==2:break
            assert len(steps)<=32
        actual=bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))
        assert actual==(d/f'plans{f-904}.bin').read_bytes(),('plans',f)
        components['pack287']=call('pack287')
        v=arm.symbols['video285'];layout=[arm.call('layout285',[i]) for i in range(3)]
        metadata=b''.join(bytes(arm.uc.mem_read(v+at,n)) for at,n in [(layout[0],4096),(layout[1],512),(layout[2],544),(layout[1]+512,1121),(0,2291),(2292,6)])
        assert metadata==(oracle/f'expected-{generation}.bin').read_bytes(),('metadata',f)
        ok=arm.call('frame259',[0x20010000,len(blob),f-904,generation])
        state=bytes(arm.uc.mem_read(arm.symbols['state259'],20)).hex()
        (d/f'arm{f}.json').write_text(json.dumps(dict(ok=ok,state=state,transfers=ep.transfers[start:]),indent=2)+'\n')
        assert ok==1,(f,state);verify(pp,ep.packets[sent:]);call('finish267');commit=call('commit285');ep.transfer(b'')
        tr=ep.transfers[start:]
        row=dict(frame=f,instructions=arm.instructions-before,decoder_excluded=decoder,components=components,steps=steps,commit=commit,
                 rows_reused=word('rows_reused287'),rows_full=word('rows_full287'),prefills=prefills,packets=len(ep.packets)-sent,
                 status_reads=sum(t['tx'].startswith('e0') for t in tr),SPI_bytes=sum(len(t['tx'])//2 for t in tr),last_RTL_ns=tr[-1]['RTL_ns'])
        rows.append(row);print(json.dumps(row),flush=True)
    (d/'arm-result.json').write_text(json.dumps(dict(passed=True,frames=rows,stack_observed=0x2003f000-arm.low_sp,live_RTL=True,
       hardware_cycles=False,full_RUN=False,IRQ_body_service_boundary=irq,IRQ_cases=ep.irq_rows,IRQ_entry_exit_cycles=24,
       IRQ_preemption_modeled='PB8 foreground checkpoints',EXTI284=arm.exti,MMIO284=arm.mmio),indent=2)+'\n')

def main():
    ns=dict(prior.__dict__);ns.update(prepare=prepare,build_rom=build_rom,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(prior.main),'live287-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
