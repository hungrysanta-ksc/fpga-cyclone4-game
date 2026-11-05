"""Run the ARM producer and 65816 actual-read verifier on pinned MMC577 output."""
import argparse
import binascii
import csv
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
from collections import defaultdict

from check_nes_game478 import (ELFFile, ROOT, Uc, UC_ARCH_ARM, UC_MODE_THUMB,
                               UC_MODE_MCLASS, UC_ARM_REG_SP, UC_ARM_REG_PC,
                               UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR)
from unicorn import UC_HOOK_CODE
from nes_abi582 import map_records, output_decode
from nes_output599_cpu import image, DATA

MASTER = 21477272
OFF = [0,512,1056,4474]
def digest(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_bytes())
def checked(path, expected):
    data = path.read_bytes()
    assert digest(data) == expected, path
    return data

def compiler(out):
    gcc = next((ROOT.parent/'.tools').glob('arm-gnu-toolchain*/*/bin/arm-none-eabi-gcc.exe'))
    env = os.environ.copy()
    env['PATH'] = str(gcc.parent)+os.pathsep+env['PATH']
    source = ROOT/'tools/output599_arm.c'
    elf = out/'producer.elf'
    subprocess.run([gcc,'-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-nostdlib',
                    '-Wl,-Ttext=0x08000000,-e,produce','-o',elf,source],check=True,env=env,cwd=out)
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB|UC_MODE_MCLASS)
    cpu.mem_map(0x08000000,0x10000)
    cpu.mem_map(0x20000000,0x10000)
    with elf.open('rb') as f:
        e = ELFFile(f)
        for s in e.iter_sections():
            if s.name in ('.text','.rodata'): cpu.mem_write(s['sh_addr'],s.data())
        entry = e.header['e_entry']
        size = sum(s['sh_size'] for s in e.iter_sections() if s.name in ('.text','.rodata'))
    instructions = 0
    def count_instruction(*_):
        nonlocal instructions
        instructions += 1
    cpu.hook_add(UC_HOOK_CODE, count_instruction)
    def run(data):
        nonlocal instructions
        instructions = 0
        cpu.mem_write(0x20000000,data)
        outptr = 0x20006000
        cpu.mem_write(outptr,bytes(4520))
        for reg,value in [(UC_ARM_REG_R0,0x20000000),(UC_ARM_REG_R1,outptr),
                          (UC_ARM_REG_LR,0x0800fff1),(UC_ARM_REG_SP,0x2000fff0)]:
            cpu.reg_write(reg,value)
        cpu.emu_start(entry,0x0800fff0,count=5000000)
        assert cpu.reg_read(UC_ARM_REG_PC)==0x0800fff0 and cpu.reg_read(UC_ARM_REG_R0)==1
        masks,stream,descs,used,count,crc = struct.unpack('<64s4224s224sHHH',cpu.mem_read(outptr,4518))
        return masks,bytes(stream[:used]),bytes(descs[:count*7]),crc,instructions
    return run,dict(ELF=digest(elf.read_bytes()),code_and_constants_B=size,
                    stack_usage=next(out.glob('*.su')).read_text(encoding='utf8').splitlines()[-1].split('\t')[1:])

LUA = r'''
local dir, labels, target, fault = @DIR@, @LABELS@, @TARGET@, @FAULT@
local wr,vr=emu.memType.snesWorkRam,emu.memType.snesVideoRam
local function file(n)
 local f=assert(io.open(dir..'/'..n,'rb'));local s=f:read('*a');f:close();return s
end
local init=file('wram.bin');local old=file('old.bin');local expected=file('new.bin')
local function clock()return emu.getState().masterClock end
local times={};local function stamp(k) times[k]=clock() end
local armed,started=false,false
emu.addEventCallback(function()
 if armed or clock()+400000<target then return end
 armed=true
 for i=0x1000,0x11ff do emu.write(i,init:byte(i+1),wr) end
 for i=0x10000,#init-1 do emu.write(i,init:byte(i+1),wr) end
 for i=1,#old do emu.write(i-1,old:byte(i),vr) end
 emu.addMemoryCallback(function()
  if not started and clock()>=target then started=true;emu.write(0x1054,1,wr) end
 end,emu.callbackType.exec,labels.gate)
end,emu.eventType.endFrame)
for _,name in ipairs({'start','map_crc','map'}) do
 local key=name
 emu.addMemoryCallback(function()stamp(key)end,emu.callbackType.exec,labels[key])
end
local reads=0
if fault=='stop' then
 emu.addMemoryCallback(function()reads=reads+1;if reads==65 then emu.write(0x1050,1,wr) end end,emu.callbackType.exec,labels.byte)
end
if fault=='partial' then
 local touched=false
 emu.addMemoryCallback(function()
  if not touched then
   for i=1,#old do
    if old:byte(i)~=emu.read(i-1,vr) then touched=true;emu.write(0x1050,1,wr);break end
   end
  end
 end,emu.callbackType.exec,labels.dma)
end
local finished=false
emu.addMemoryCallback(function()
 if finished then return end
 finished=true
 stamp('done')
 local status=emu.read(0x1052,wr)
 local oracle=status==1 and expected or old
 local mismatches=0
 for i=1,#oracle do if emu.read(i-1,vr)~=oracle:byte(i) then mismatches=mismatches+1 end end
 if fault=='partial' then
  local f=assert(io.open(dir..'/partial.bin','wb'))
  for i=0,#old-1 do f:write(string.char(emu.read(i,vr))) end
  f:close()
 end
 local f=assert(io.open(dir..'/result.txt','w'))
 f:write(string.format('%d %d %d %d %d %d',status,mismatches,times.start,times.map_crc or 0,times.map or 0,times.done));f:close()
 emu.stop(0)
end,emu.callbackType.exec,labels.done)
'''

def simulate(a, name, target, base, current, memory, masks, records, declarations, crc, fault):
    d=a.out/name
    d.mkdir()
    rom, labels, size = image()
    (d/'kernel.sfc').write_bytes(rom)
    # Only data areas are installed; do not overwrite the executing WRAM routine.
    wram = bytearray(0x12000+len(records)+1)
    wram[0x1000:0x1040]=masks
    struct.pack_into('<3H',wram,0x1070,len(declarations),DATA+len(records),crc)
    wram[0x1080:0x1080+len(declarations)]=declarations
    wram[0x10000:0x10000+len(memory)]=memory
    wram[0x12000:0x12000+len(records)]=records
    if fault=='corrupt':
        sec,start,_,_=struct.unpack_from('<BHHH',declarations)
        wram[0x10000+OFF[sec-3]+start]^=1
    if fault=='address_wrap':
        wram[0x1080:0x1083]=struct.pack('<BH',4,0xffff)
    if fault=='overlap':
        wram[0x1087:0x108e]=wram[0x1080:0x1087]
    if fault=='map_crc': wram[0x12002]^=1
    if fault=='mask': wram[0x1000+records[0]]^=1
    (d/'wram.bin').write_bytes(wram)
    (d/'old.bin').write_bytes(base)
    (d/'new.bin').write_bytes(current)
    lua=LUA.replace('@DIR@',json.dumps(d.as_posix(),ensure_ascii=False)).replace('@LABELS@','{'+','.join(f'{k}={labels[k]}' for k in ['gate','start','map_crc','map','byte','done','dma'])+'}')
    (d/'run.lua').write_text(lua.replace('@TARGET@',str(target)).replace('@FAULT@',json.dumps(fault)),encoding='utf8')
    env=os.environ.copy()
    env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (d/'mesen.log').open('wb') as log:
        subprocess.run([a.mesen,'--testRunner',d/'run.lua',d/'kernel.sfc','--timeout=40',
                        '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true'],env=env,cwd=d,check=True,
                       stdout=log,stderr=subprocess.STDOUT,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
    status,wrong,start,mid,dma,end=map(int,(d/'result.txt').read_text().split())
    assert status==(1 if fault=='normal' else 2)
    if fault=='partial':
        partial=(d/'partial.bin').read_bytes()
        assert wrong>0 and partial!=current
        assert all(x in (before,after) for x,before,after in zip(partial,base,current,strict=True))
    else:
        assert wrong==0
    assert 0<=start-target<256,(start,target)
    return dict(status=status,VRAM_mismatches=wrong,requested_clock=target,start=start,end=end,
                inherited_clocks=mid-start if mid else None,map_CRC_clocks=dma-mid if dma else None,
                sparse_DMA_with_VBlank_clocks=end-dma if dma else None,body_B=size)

def main(a):
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    arm,info=compiler(a.out)
    whole=load(ROOT/'analysis/whole580-verification.json')
    body=load(ROOT/'analysis/body581-verification.json')
    reference=load(ROOT/'analysis/abi582-verification.json')['frames']
    result=dict(ARM=info,phases=[],guards={})
    for phase in whole['phases']:
        i=phase['phase'];pins=phase['evidence']
        traces=a.traces/f'nes-close561-run{i}'
        packets=defaultdict(list)
        for line in checked(traces/'packets.jsonl',pins['packets.jsonl']).splitlines():
            raw=bytes.fromhex(json.loads(line)[2])
            packets[int.from_bytes(raw[8:10],'little')].append(raw)
        events=json.loads(checked(traces/'events.json',pins['events.json']))
        marks=defaultdict(dict)
        for row in csv.DictReader(checked(traces/'window.csv',pins['window.csv']).decode().splitlines()):
            if row['op']=='3' and row['event'] in ('seal','reveal','ack'):
                assert row['event'] not in marks[int(row['g'])]
                if row['event']=='ack': assert row['value']=='1'
                marks[int(row['g'])][row['event']]=int(row['clock'])
        banks=[bytes(4096),bytes(4096)]
        history=[bytes(4474),bytes(4474)]
        stale=[set(range(512)),set(range(512))]
        valid=[[0]*3 for _ in range(2)]
        prev=bytes(4096)
        layouts=[None,None]
        for g in range(905,955):
            group=packets[g]
            sealed=marks[g]
            assert sealed['seal']<sealed['reveal']<sealed['ack']
            issue=next(e['clock'] for e in events if e['generation']==g and e['event']=='output_enter531')
            if g>905: assert marks[g-1]['ack']<issue
            bank=int.from_bytes(group[0][18:20],'little')
            layout=int.from_bytes(group[-1][38:40],'little')
            base=history[bank];current=bytearray(base);sizes=[0]*3;ranges=[]
            if layout!=layouts[bank]: valid[bank][2]=0
            for p in group:
                if p[0] not in (2,4,5,8) or p[1]<3: continue
                k=p[1]-3
                at=int.from_bytes(p[10:12],'little');data=output_decode(p)
                assert at==sizes[k] and at+len(data)<=OFF[k+1]-OFF[k]
                current[OFF[k]+at:OFF[k]+at+len(data)]=data
                sizes[k]+=len(data);ranges.append((p[1],at,len(data)))
            key=f'capture/frame{g}/expected-map.bin'
            mp=checked(a.capture/f'frame{g}/expected-map.bin',body['inputs'][key])
            old_stale=bytes(sum(((r*8+b in stale[bank])<<b) for b in range(8)) for r in range(64))
            rec,mask,_=map_records(mp,prev,[stale[bank],stale[1-bank]],g<=906)
            if g in (952,954):
                args=prev+mp+old_stale+base+current+struct.pack('<4H',*valid[bank],len(ranges))
                args+=b''.join(struct.pack('<3H',*r) for r in ranges)
                am,rr,dd,cc,instructions=arm(args)
                assert am==mask and rr==b''.join(rec) and cc==binascii.crc_hqx(rr,65535)
                reuse=reference[g-905]['reuse'][str(i)]
                inherited=sum(n for _,_,n,_ in struct.iter_unpack('<BHHH',dd))
                assert len(dd)==7*reuse['ranges'] and inherited==reuse['inherited_check_B']
                ts=round(issue)
                # Candidates are admitted at the old issue instant with all data ready.
                existing_map=body['frames'][str(g)]['phases'][str(i)]['output']['map']['wire_B']
                record=dict(phase=i,generation=g,bank=bank,inherited_B=inherited,ARM_instructions=instructions,
                            net_nonmap_wire_saved_B=reuse['omitted_wire_B']-reuse['declaration_wire_B'],
                            net_map_wire_saved_B=existing_map-reference[g-905]['map']['wire_B'],
                            map_record_B=len(rr),declaration_B=len(dd),old_ACK_interval_ms=phase['frames'][str(g)]['ACK_interval_ms'])
                def bench(fault):
                    return simulate(a,f'{i}-{g}-{fault}',ts,banks[bank],mp,base,am,rr,dd,cc,fault)
                record.update(bench('normal'),baseline_marks=sealed)
                record['CRC_done_minus_baseline_ACK_clocks']=record['start']+record['inherited_clocks']-sealed['ack']
                assert record['CRC_done_minus_baseline_ACK_clocks']>0
                result['phases'].append(record)
                if i==1 and g==952:
                    for f in ('corrupt','map_crc','mask','address_wrap','overlap','stop','partial'):
                        result['guards'][f]=bench(f)
                    # No inherited bytes may be declared after STOP. Start the new
                    # cold map from the actual partially modified VRAM image.
                    cold_args=prev+mp+bytes([255])*64+base+current+struct.pack('<4H',0,0,0,len(ranges))+args[-6*len(ranges):]
                    cm,cr,cd,cs,_=arm(cold_args)
                    assert not cd and cm==bytes([255])*64 and len(cr)==4224
                    assert cr==b''.join(bytes([row,255])+mp[64*row:64*row+64] for row in range(64))
                    partial=(a.out/'1-952-partial/partial.bin').read_bytes()
                    result['guards']['cold_map']=simulate(a,'cold-map',ts,partial,mp,base,cm,cr,cd,cs,'normal')
            prev=mp;banks[bank]=mp;history[bank]=bytes(current);valid[bank]=sizes;layouts[bank]=layout;stale[bank].clear()
    result.update(stage=599,master_Hz=MASTER,full_final_ACK=None,physical=False,
                  scope='Matched producer/consumer kernels with frozen histories and preloaded output at old issue clocks. No retimed queue, IRQ, SEAL or final display.')
    result['inputs']={p.name:digest(p.read_bytes()) for p in (ROOT/'analysis/whole580-verification.json',
        ROOT/'analysis/body581-verification.json',ROOT/'analysis/abi582-verification.json',
        ROOT/'tools/output599_arm.c',ROOT/'tools/nes_output599_cpu.py',Path(__file__))}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['phases']))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('capture','traces','out','mesen'):p.add_argument('--'+key,type=Path,required=True)
    main(p.parse_args())
