"""Actual M4 recipe and 65816 kernels; bounded cost gate, not a joint firmware."""
import argparse, binascii, hashlib, json, os, struct, subprocess
from collections import defaultdict
from pathlib import Path
from analyze_nes_supply670 import layout, source_maps, crc, word, ms
from nes_transfer512 import legacy_packets
from analyze_nes_output615 import packets, one
from analyze_nes_body581 import output_decode
from probe_nes_arm264 import ARM
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from elftools.elf.elffile import ELFFile
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_rom636 import pack, BOOT, STORED

ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT.parent
GCC=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
PYTHON=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def run(cmd,d,name,timeout=60):
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (d/(name+'.log')).open('wb') as f:
        r=subprocess.run(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,
                         timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,(name,(d/(name+'.log')).read_text(errors='replace')[-3000:])

class KernelARM(ARM):
    def __init__(self,p):
        self.uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.uc.mem_map(0x08000000,0x100000);self.uc.mem_map(0x20000000,0x40000)
        with p.open('rb') as f:
            e=ELFFile(f)
            for seg in e.iter_segments():
                if seg['p_type']=='PT_LOAD':self.uc.mem_write(seg['p_vaddr'],seg.data())
            self.symbols={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
        self.endpoint=None;self.instructions=0;self.low_sp=0x2003f000
        self.uc.hook_add(UC_HOOK_CODE,self.hook)
        self.symbols['io259']=0;self.symbols['trace259']=0

def arm_build(d):
    (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) } }')
    run([GCC/'arm-none-eabi-gcc.exe','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4',
         '-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib',
         '-Wl,-T,layout.ld','-Wl,-Map,recipe.map',ROOT/'tools/nes_supply671.c','-o','recipe.elf'],d,'arm-build')
    run([GCC/'arm-none-eabi-size.exe','-A','recipe.elf'],d,'arm-size')
    run([GCC/'arm-none-eabi-objdump.exe','-dr','recipe.elf'],d,'arm-disassembly')

def kernel(d):
    c=Code(0x8000)
    def imm(op,n):c.emit(op);c.word(n)
    def lda(n):c.absolute(0xad,n)
    def sta(n):c.absolute(0x8d,n)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    # Native16bit CPU, DBR7E, direct page0. Standalone test ROM only.
    c.emit(0x78,0x18,0xfb,0xc2,0x30);imm(0xa2,0x1fff);c.emit(0x9a)
    imm(0xa9,0);c.emit(0x5b,0xe2,0x20);c.store(0x4200,0);c.store(0x420c,0);c.store(0x2100,0x80)
    c.emit(0xa9,0x7e,0x48,0xab,0xc2,0x20)
    c.label('poll');c.emit(0xe2,0x20);c.long(0xaf,0x00607d);c.emit(0xc2,0x20);imm(0x29,255)
    for op,label in [(1,'cold'),(2,'warm'),(3,'mirror'),(4,'row'),(5,'stop')]:
        imm(0xc9,op);cond(0xf0,label)
    c.jump('poll')
    c.label('stop');c.emit(0x64,0x26);imm(0xa9,0);c.emit(0x85,0x30,0x64,0x32);c.jump('return')
    c.label('bad');imm(0xa9,0);c.emit(0x85,0x30,0x64,0x32);c.jump('return')
    c.label('good');imm(0xa9,1);c.emit(0x85,0x30)
    c.label('return');c.emit(0xe2,0x20,0xa5,0x30);c.long(0x8f,0x00607e);c.emit(0xc2,0x20);c.jump('poll')
    c.label('checkstop');c.emit(0xe2,0x20);c.long(0xaf,0x006050);c.emit(0xc2,0x20);imm(0x29,1);c.emit(0x60)
    c.label('cold');call(c,'checkstop');cond(0xd0,'bad');imm(0xa2,0);imm(0xa9,0)
    c.label('clear');c.absolute(0x9e,0x8000);c.emit(0xe8,0xe8,0x8a);imm(0x29,127);c.branch(0xd0,'clear_next')
    call(c,'checkstop');cond(0xd0,'bad')
    c.label('clear_next');imm(0xe0,16384);c.branch(0xd0,'clear')
    c.emit(0x64,0x26);imm(0xa9,1);c.emit(0x85,0x32);c.jump('good')
    c.label('warm');call(c,'checkstop');cond(0xd0,'bad');c.emit(0xa5,0x32);cond(0xf0,'bad');imm(0xa0,0)
    c.label('key');c.emit(0xc4,0x26);c.branch(0xf0,'keys_done');c.absolute(0xb9,0xc000);c.emit(0xaa)
    c.absolute(0x9e,0x8000);c.emit(0xc8,0xc8);c.branch(0x80,'key')
    c.label('keys_done');c.emit(0x64,0x26);c.jump('good')
    c.label('mirror');call(c,'checkstop');cond(0xd0,'bad');c.emit(0xa5,0x32);cond(0xf0,'bad')
    # Parameter10 destinationWRAM,12 size,28 expectedCRC. Header checking
    # and identity/credit are deliberately outside this bounded kernel.
    c.emit(0xe2,0x20,0xa5,0x10);c.long(0x8f,0x002181);c.emit(0xa5,0x11);c.long(0x8f,0x002182)
    for a,v in [(0x2183,0),(0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,0x50),(0x4304,0)]:
        c.emit(0xa9,v);c.long(0x8f,a)
    c.emit(0xc2,0x20,0xa5,0x12);c.long(0x8f,0x004305);c.emit(0xe2,0x20,0xa9,1);c.long(0x8f,0x00420b);c.emit(0xc2,0x20)
    call(c,'crc');c.emit(0xc5,0x28);cond(0xd0,'bad');call(c,'checkstop');cond(0xd0,'bad');c.jump('good')
    c.label('row');call(c,'checkstop');cond(0xd0,'bad');c.emit(0xa5,0x32);cond(0xf0,'bad')
    # Fixed8B row header plus updates. Final independent64B CRC verifies
    # inherited and reconstructed cells before any row is accepted.
    lda(0x7100);imm(0x29,255);imm(0xc9,64);cond(0xb0,'bad');c.emit(0x85,0x22)
    for _ in range(6):c.emit(0x0a)
    c.emit(0x85,0x24,0xaa);imm(0xa0,32)
    c.label('base_copy');c.long(0xbf,0x7f4000);c.long(0x9f,0x7fc000);c.emit(0xe8,0xe8,0x88);c.branch(0xd0,'base_copy')
    lda(0x7104);imm(0x29,255);imm(0xc9,34);cond(0xb0,'bad');c.emit(0x85,0x1a);imm(0xa0,8)
    c.label('binding');c.emit(0xa5,0x1a);c.branch(0xf0,'bound')
    c.absolute(0xb9,0x7100);imm(0xc9,8192);cond(0xb0,'bad');c.emit(0x0a,0xaa,0x85,0x1c)
    c.absolute(0xb9,0x7102);cond(0xf0,'bad');imm(0xc9,1024);cond(0xb0,'bad');c.absolute(0x9d,0x8000)
    c.emit(0xa6,0x26);imm(0xe0,2048);cond(0xb0,'bad');c.emit(0xa5,0x1c);c.absolute(0x9d,0xc000)
    c.emit(0xe8,0xe8,0x86,0x26,0xc8,0xc8,0xc8,0xc8,0xc6,0x1a);c.jump('binding')
    c.label('bound');lda(0x7101);imm(0x29,255);imm(0xc9,32);cond(0xf0,'row_crc');cond(0xb0,'bad')
    c.emit(0x85,0x10)
    for _ in range(5):c.emit(0x0a)
    c.emit(0x18,0x65,0x10,0x0a,0x85,0x10) # source group *66
    lda(0x7102);imm(0x29,255);imm(0xc9,64);cond(0xb0,'bad');c.emit(0x85,0x14)
    lda(0x7103);imm(0x29,255);imm(0xc9,2);cond(0xb0,'bad')
    for _ in range(4):c.emit(0x0a)
    c.emit(0xeb);imm(0x09,0x2000);c.emit(0x85,0x16);imm(0xa9,33);c.emit(0x85,0x18)
    c.label('cell');c.emit(0xa5,0x14,0x45,0x22);imm(0x29,32);c.branch(0xd0,'skip_cell')
    c.emit(0xa6,0x10);c.absolute(0xbd,0x6800);c.emit(0x85,0x1c);imm(0x29,8191);c.emit(0x0a,0xaa)
    c.absolute(0xbd,0x8000);cond(0xf0,'bad');c.emit(0x85,0x1e,0xa5,0x1c);imm(0x29,0x6000)
    c.emit(0x4a,0x4a,0x4a,0x05,0x16,0x05,0x1e,0x85,0x1e)
    c.emit(0xa5,0x14);imm(0x29,31);c.emit(0x0a,0x18,0x65,0x24,0xaa,0xa5,0x1e);c.long(0x9f,0x7fc000)
    c.label('skip_cell');c.emit(0xe6,0x10,0xe6,0x10,0xe6,0x14,0xc6,0x18);cond(0xd0,'cell')
    c.label('row_crc');c.emit(0xa5,0x24,0x18);imm(0x69,0xc000);c.emit(0x85,0x10);imm(0xa9,64);c.emit(0x85,0x12)
    # CRC uses long7F pointer for destination; source uses7E. DBR changes only here.
    c.emit(0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20);call(c,'crc')
    c.emit(0x48,0xe2,0x20,0xa9,0x7e,0x48,0xab,0xc2,0x20,0x68);c.absolute(0xcd,0x7106);cond(0xd0,'bad');c.jump('good')
    c.label('crc');imm(0xa9,65535);c.emit(0x85,0x20);imm(0xa0,0)
    c.label('crc_byte');c.emit(0xa5,0x20,0xeb,0x51,0x10);imm(0x29,255);c.emit(0x0a,0xaa,0xa5,0x20,0xeb);imm(0x29,0xff00)
    c.long(0x5f,0x7ec800);c.emit(0x85,0x20,0xc8,0x98);imm(0x29,63);c.branch(0xd0,'crc_next')
    call(c,'checkstop');c.branch(0xf0,'crc_next')
    # unwind CRC caller before rejecting; restores DBR so no later commit.
    c.emit(0x68,0xe2,0x20,0xa9,0x7e,0x48,0xab,0xc2,0x20);c.jump('bad')
    c.label('crc_next');c.emit(0xc4,0x12);c.branch(0xd0,'crc_byte');c.emit(0xa5,0x20,0x60)
    body=c.finish();r=bytearray([255])*32768;r[:len(body)]=body
    r[0x7fc0:0x7fd5]=b'NES671 BOUNDED KERNEL '.ljust(21)[:21];r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
    for pos in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,pos,0x8000)
    (d/'kernel.sfc').write_bytes(r);(d/'kernel.bin').write_bytes(body)
    (d/'labels.json').write_text(json.dumps(c.labels,indent=2)+'\n')
    return len(body)

LUA=r'''
local f=assert(io.open(OUT..'/cpu.csv','w'));f:write('case,op,clocks,status,reads\n')
local index=0;local active=nil;local start=0;local reads=0;local stopreads=0
local marks={};local m=assert(io.open(OUT..'/components.csv','w'));m:write('case,mark,clock\n')
local beats=assert(io.open(OUT..'/source-reads.csv','w'));beats:write('case,index,clock\n')
local function load(at,hex)
 for i=1,#hex,2 do emu.write(at+(i-1)//2,tonumber(hex:sub(i,i+1),16),emu.memType.snesWorkRam)end
end
local function word(at,v)emu.write(at,v&255,emu.memType.snesWorkRam);emu.write(at+1,v>>8,emu.memType.snesWorkRam)end
local function dump(at,n)local s={};for i=0,n-1 do s[#s+1]=string.format('%02x',emu.read(at+i,emu.memType.snesWorkRam))end;return table.concat(s)end
load(0xc800,TABLE)
emu.addMemoryCallback(function()
 index=index+1;active=CASES[index]
 if not active then f:close();m:close();beats:close();emu.stop(0);return 0 end
 if active.previous then load(0x14000,active.previous);load(0x1c000,active.target)end
 if active.desc then load(0x7100,active.desc)end
 if active.op==3 then word(0x10,0x6800+active.offset);word(0x12,#active.data//2);word(0x28,active.crc)end
 if active.cold then word(0x26,0)end
 start=emu.getState().masterClock;reads=0;stopreads=0;marks={};return active.op
end,emu.callbackType.read,0x607d)
emu.addMemoryCallback(function(a)
 assert(active.op==3 and a-0x5000==reads,'actual source read order');reads=reads+1
 beats:write(string.format('%s,%d,%d\n',active.name,reads-1,emu.getState().masterClock-start))
 local i=2*(reads-1)+1;return tonumber(active.data:sub(i,i+1),16)
end,emu.callbackType.read,0x5000,0x50ff)
emu.addMemoryCallback(function()stopreads=stopreads+1;return (active.stop and stopreads>=active.stop) and 1 or 0 end,emu.callbackType.read,0x6050)
emu.addMemoryCallback(function(a,v)
 local elapsed=emu.getState().masterClock-start
 f:write(string.format('%s,%d,%d,%d,%d\n',active.name,active.op,elapsed,v,reads));f:flush()
 assert(v==active.status,'kernel status '..active.name..' got '..v)
 if active.expected then assert(dump(0x1c000+active.row*64,64)==active.expected,'independent row bytes '..active.name)end
end,emu.callbackType.write,0x607e)
for name,pc in pairs(LABELS)do
 if name=='row_crc' or name=='crc' or name=='base_copy' or name=='binding' or name=='bound' then
  emu.addMemoryCallback(function()
   if active and not marks[name]then marks[name]=true;m:write(string.format('%s,%s,%d\n',active.name,name,emu.getState().masterClock-start));m:flush()end
  end,emu.callbackType.exec,pc)
 end
end
'''

def main(a):
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);arm_build(d);size=kernel(d)
    arm_elf=a.linked_arm if a.linked_arm else d/'recipe.elf';arm=KernelARM(arm_elf)
    traces=a.traces/'nes-entry665-a1';commands=packets(traces);sender=read(a.traces/'nes-reader661-sender/sender.json')
    wanted={905,906,907,911,951,952,953,954,955,957};history=[bytes(4096),bytes(4096)];previous=bytes(4096)
    scenarios=[];results=[];rawpins={};table=b''.join(struct.pack('<H',crc(bytes([i])) ^ crc(bytes([0]))) for i in range(256))
    # linearity removes theFFFF seed; table is standard CCITT byte table.
    assert table==b''.join(struct.pack('<H',binascii.crc_hqx(bytes([i]),0)) for i in range(256))
    for g in range(905,958):
        geometry=a.data/f'frame{g}.geometry';rawfile=a.data/f'frame{g}.raw'
        _,_,arrays=legacy_packets(geometry.read_bytes(),rawfile.read_bytes(),g);groups=layout(arrays)
        raw=struct.pack('<'+'H'*len(arrays[0]),*arrays[0]);bank=(g-905)%2
        target=history[bank];expected=(traces/f'map-{g}.bin').read_bytes()
        if g in wanted:
            arm.uc.mem_write(0x20001000,raw);arm.uc.mem_write(0x20003000,expected);arm.uc.mem_write(0x20005000,bytes(128))
            scenarios.append(dict(name=f'{g}-cold',op=1,status=1,previous=previous.hex(),target=target.hex()))
            blocks=source_maps(sender[str(g)],g,arrays[0]);offset=0
            for b in blocks:
                data=raw[offset:offset+b['source_B']];scenarios.append(dict(name=f'{g}-source',op=3,status=1,offset=offset,data=data.hex(),crc=crc(data)));offset+=len(data)
            instructions=0;new_wire=0;recipes=[];old_wire=0
            for packet,_,clock in commands[g]:
                if packet[1]!=2:continue
                old_wire+=len(packet)+3
                start=word(packet,10)//64;n=len(output_decode(packet))//64
                for row in range(start,start+n):
                    group=next((q for q in groups if q[1]==row%32),None)
                    src,col,epoch=(group[0],group[2],group[3]) if group else (32,0,0)
                    params=struct.pack('<8I',0x20001000,0x20003000,0x20005000,0x20006000,row,src,col,epoch)
                    arm.uc.mem_write(0x20000100,params);before=arm.instructions
                    length=arm.call('recipe671',[0x20000100]);assert 8<=length<=140
                    instructions+=arm.instructions-before;recipe=bytes(arm.uc.mem_read(0x20006000,length))
                    assert word(recipe,6)==crc(expected[row*64:row*64+64])
                    scenarios.append(dict(name=f'{g}-row',op=4,status=1,desc=recipe.hex(),row=row,expected=expected[row*64:row*64+64].hex()))
                    new_wire+=length+19;recipes.append(dict(row=row,descriptor=recipe.hex(),baseline_packet_clock=clock))
            scenarios.append(dict(name=f'{g}-warm-clear',op=2,status=1))
            if g==957:
                # Reconstruct the same last row again with a corrupted expected
                # digest after a real cold/source/row replay. Do not contaminate
                # the measured normal warm invalidation with fault cleanup.
                scenarios.append(dict(name='guard-cold',op=1,status=1))
                offset=0
                for b in blocks:
                    data=raw[offset:offset+b['source_B']]
                    scenarios.append(dict(name='guard-source',op=3,status=1,offset=offset,data=data.hex(),crc=crc(data)));offset+=len(data)
                for q in recipes:
                    row=q['row'];scenarios.append(dict(name='guard-row',op=4,status=1,desc=q['descriptor'],row=row,expected=expected[row*64:row*64+64].hex()))
                desc=bytearray.fromhex(recipes[-1]['descriptor']);desc[6]^=1
                scenarios.append(dict(name='bad-row-CRC',op=4,status=0,desc=desc.hex()))
                scenarios.append(dict(name='row-after-fault-blocked',op=4,status=0,desc=recipes[-1]['descriptor']))
                scenarios.append(dict(name='warm-after-fault-blocked',op=2,status=0))
                scenarios.append(dict(name='cold-after-row-fault',op=1,status=1))
            results.append(dict(generation=g,ARM_instructions=instructions,ARM_CPI2_ms=instructions*2/84000,
                old_map_wire_B=old_wire,new_row_wire_B=new_wire,wire_saving_ms=(old_wire-new_wire)*8/2625,
                rows=len(recipes),recipes=recipes))
            rawpins[str(g)]=dict(geometry=sha(geometry),raw=sha(rawfile),map=sha(traces/f'map-{g}.bin'))
        history[bank]=expected;previous=expected
    # Directed CRC damage and STOP during block checking, followed by cold restart.
    data=bytes(range(128))
    scenarios.extend([dict(name='bad-source-CRC',op=3,status=0,offset=0,data=data.hex(),crc=crc(data)^1),
        dict(name='source-after-fault-blocked',op=3,status=0,offset=0,data=data.hex(),crc=crc(data)),
        dict(name='cold-before-STOP',op=1,status=1),
        dict(name='STOP-entry',op=3,status=0,offset=0,data=data.hex(),crc=crc(data),stop=1),
        dict(name='cold-before-mid-STOP',op=1,status=1),
        dict(name='STOP-after64',op=3,status=0,offset=0,data=data.hex(),crc=crc(data),stop=2),
        dict(name='STOP-cold-clear',op=1,status=0,stop=2),
        dict(name='STOP-invalidate',op=5,status=0),dict(name='stale-row-after-STOP',op=4,status=0,desc=results[-1]['recipes'][-1]['descriptor']),dict(name='cold-recovery',op=1,status=1),
        dict(name='source-recovery',op=3,status=1,offset=0,data=data.hex(),crc=crc(data))])
    # Invalid descriptor / mismatched rowCRC never gets accepted.
    (d/'fixtures.json').write_text(json.dumps(scenarios)+'\n')
    def lua(v):
        if isinstance(v,dict):return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
        if isinstance(v,list):return '{'+','.join(map(lua,v))+'}'
        if isinstance(v,bool):return 'true' if v else 'false'
        return json.dumps(v)
    (d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\nlocal TABLE='+json.dumps(table.hex())+'\nlocal LABELS='+lua(read(d/'labels.json'))+'\nlocal CASES='+lua(scenarios)+'\n'+LUA,newline='\n')
    run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',d/'capture.lua',d/'kernel.sfc',
         '--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],d,'mesen',60)
    import csv
    times=list(csv.DictReader((d/'cpu.csv').read_text().splitlines()));assert len(times)==len(scenarios)
    for r in results:
        g=r['generation'];r['SNES_ms']={kind:ms(sum(int(t['clocks']) for t in times if t['case']==f'{g}-{kind}')) for kind in ('cold','warm-clear','source','row')}
        r['new_data_and_kernel_serial_ms']=sum(r['SNES_ms'][k] for k in ('warm-clear','source','row'))+r['ARM_CPI2_ms']
    # Actual compressed storage sensitivity: no claim that appended code is linked.
    body=(BASE/'probes/nes-entry665/client02/body.bin').read_bytes()
    addition=(d/'kernel.bin').read_bytes()+table
    sizes=[(BOOT+p+len(pack(body+addition,p)),p) for p in range(128,len(body)//128*128+1,128)]
    report=dict(stage=671,passed=True,scope=__doc__,selected='MMC666',new_whole_schedule=False,new_RTL=False,
        CPU_cases=len(times),ARM_stack_observed_B=0x2003f000-arm.low_sp,
        SNES_kernel_ROM_B=size,SNES_CRC_table_B=len(table),SNES_append_storage_min_B=min(sizes)[0],
        SNES_physical_capacity_excluding_vectors_B=STORED,ARM_sent_bitmap_B=128,ARM_packet_buffer_B=140,
        ARM_new_descriptor_input_struct_B=32,frames=results,
        limitations=['Source aperture and expected/header fixtures; no real dual-consumer RTL','Kernel ROM executes fromLoROM; selected client executesWRAM; both slow8clock accesses here',
        'Incremental callbacks use recorded accepted-row order; producer hook/readiness not linked to planner','No full IRQ/SPI/ROM/VBlank replay; standalone code addition is not net deletion'],
        pins=dict(input=rawpins,ELF=sha(arm_elf),ROM=sha(d/'kernel.sfc'),cpu=sha(d/'cpu.csv'),fixtures=sha(d/'fixtures.json')))
    (d/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pins','frames')},indent=2))
    for r in results:print(json.dumps({k:v for k,v in r.items() if k!='recipes'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','traces','data'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--linked-arm',type=Path)
    main(p.parse_args())
