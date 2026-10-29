# SPDX-License-Identifier: MIT
"""Compare linked471/474 M4 planner, slot plans and bank state; instructions, not cycles."""
import argparse, hashlib, json, struct, sys
from pathlib import Path
from nes_delta231 import BASE, sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,type=Path);p.add_argument('--blocks',type=Path);p.add_argument('--rpc',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
assert bool(a.blocks)!=bool(a.rpc),'select block capture or actual live RPC'
rpc_inputs={}
if a.rpc:
 rows=[];token=length=None
 for req in sorted(a.rpc.glob('H-*.req')):
  wire=req.read_bytes()
  if wire[0]!=1:continue
  tx=wire[8:];reply=req.with_suffix('.rsp');rx=reply.read_bytes()
  if tx[0]==0xd0 and len(rx)==8 and rx[1]==0xd6 and rx[2]&1:
   token=int.from_bytes(rx[3:5],'big');length=int.from_bytes(rx[5:7],'big')
  if tx[0]!=0xd1:continue
  assert token is not None and len(rx)==length+3
  data=rx[1:-2];crc=65535
  for b in data:
   crc^=b<<8
   for _ in range(8):crc=((crc<<1)^0x1021 if crc&32768 else crc<<1)&65535
  assert crc==int.from_bytes(rx[-2:],'big')
  rows.append(f'{token} {length} {data.hex()}')
  rpc_inputs[req.name]=sha(req);rpc_inputs[reply.name]=sha(reply)
  token=length=None
 assert rows and bytes.fromhex(rows[0].split()[2])[4:6]==b'\x22\x32'
 a.blocks=a.out/'source-blocks.txt';a.blocks.write_text('\n'.join(rows)+'\n',encoding='utf8')

def run(src):
 fw=src/'obj-nes-100/firmware.stm';flash=fw.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
 u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000)
 layouts={}
 def offset(at):
  v=at.value
  if isinstance(v,int):return v
  assert v[0]==0x23;value=0;shift=0
  for b in v[1:]:
   value|=(b&127)<<shift
   if b<128:return value
   shift+=7
  raise AssertionError('bad DWARF member offset')
 with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
  e=ELFFile(f);segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_filesz']]
  syms={x.name:(x['st_value']&~1,x['st_size']) for x in e.get_section_by_name('.symtab').iter_symbols() if x['st_info']['type']=='STT_FUNC'}
  for cu in e.get_dwarf_info().iter_CUs():
   for die in cu.iter_DIEs():
    if die.tag!='DW_TAG_structure_type' or 'DW_AT_name' not in die.attributes or 'DW_AT_byte_size' not in die.attributes:continue
    name=die.attributes['DW_AT_name'].value.decode()
    if name not in ['nes_native165','nes_native_video165','nes_resident211','nes_plan191']:continue
    item={'size':die.attributes['DW_AT_byte_size'].value}
    for c in die.iter_children():
     if c.tag=='DW_TAG_member' and 'DW_AT_name' in c.attributes:item[c.attributes['DW_AT_name'].value.decode()]=offset(c.attributes['DW_AT_data_member_location'])
    if name in layouts:assert layouts[name]==item
    layouts[name]=item
 for at,b in segments:u.mem_write(at,b)
 names=['nes_native165_reset','nes_native165_packet','nes_native165_prepare','nes_resident211_reset','nes_resident211_begin','nes_native_video211_plan','nes_resident211_commit']
 for name in names:
  at,n=syms[name];seg_at,b=next((at0,b) for at0,b in segments if at0<=at and at+n<=at0+len(b))
  assert flash[at-0x0800c000:at-0x0800c000+n]==b[at-seg_at:at-seg_at+n],name
 state,video,resident,lut,buf=0x20008000,0x2000b000,0x2000f000,0x20011000,0x20012000
 assert state+layouts['nes_native165']['size']<=video and video+layouts['nes_native_video165']['size']<=resident
 assert resident+layouts['nes_resident211']['size']<=lut
 end,prepare,write=0x0807fff0,0x0807ffe0,0x0807ffd0;count=0;plans=[]
 def crc8(data):
  c=0
  for b in data:
   c^=b
   for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
  return c
 def hook(uc,at,size,user):
  nonlocal count
  if at==end:uc.emu_stop();return
  if at==prepare:
   reply=bytearray(8);reply[1]=0xd6;reply[2]=2;reply[7]=crc8(reply[1:7]);uc.mem_write(uc.reg_read(UC_ARM_REG_R2),bytes(reply))
  elif at==write:
   plans.append([uc.reg_read(UC_ARM_REG_R1),bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R2),layouts['nes_plan191']['size'])).hex()])
  else:count+=1;return
  uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 def call(name,args):
  stack=0x2001e000
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(reg,v)
  for i,v in enumerate(args[4:]):u.mem_write(stack+i*4,struct.pack('<I',v))
  u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,end|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000)
  u.emu_start(syms[name][0]|1,end+2,count=30000000);assert u.reg_read(UC_ARM_REG_PC)==end,name
  return u.reg_read(UC_ARM_REG_R0)
 call('nes_native165_reset',[state])
 for line in a.blocks.read_text().splitlines():
  token,n,data=line.split();b=bytes.fromhex(data);assert int(n)==len(b)
  if b[:2]==b'\xe0\x03':assert call('nes_native165_prepare',[state,1,prepare|1,0])==1
  u.mem_write(buf,b);assert call('nes_native165_packet',[state,int(token),buf,len(b)])==1
 u.mem_write(lut,struct.pack('<64H',*[x*371 for x in range(64)]));call('nes_resident211_reset',[resident])
 read16=lambda ptr:struct.unpack('<H',u.mem_read(ptr,2))[0]
 read32=lambda ptr:struct.unpack('<I',u.mem_read(ptr,4))[0]
 frames=[];g=read16(state+layouts['nes_native165']['generation']);layout=layouts['nes_native165']
 initial_raster=bytes(u.mem_read(state+layout['raster'],224*8))
 initial_maps=bytes(u.mem_read(state+layout['maps'],1056*2))
 initial_palette=bytes(u.mem_read(state+layout['palette'],64))
 count_maps=read16(state+layout['counts'])
 for i in range(15):
  generation=(g+i)&65535;u.mem_write(state+layouts['nes_native165']['generation'],struct.pack('<H',generation))
  if i>=4:
   columns=[0,1,31,32,33,63,0,16,31,63,1];col=columns[i-4]
   for y in range(224):
    v=struct.unpack_from('<Q',initial_raster,y*8)[0];x=(col+(y//8)*5)&63
    v=(v&~0x41f)| (x&31)|((x&32)<<5)
    if i>=12:v=(v&~(31<<44))|(((y//8)&1)<<44)
    u.mem_write(state+layout['raster']+y*8,struct.pack('<Q',v))
  if i>=12:
   u.mem_write(state+layout['counts']+10,struct.pack('<H',64));u.mem_write(state+layout['palette']+32,initial_palette[:32])
  if i==14:
   for at in range(count_maps):
    cell=struct.unpack_from('<H',initial_maps,at*2)[0]&8191;row,x=divmod(at,33)
    u.mem_write(state+layout['maps']+at*2,struct.pack('<H',cell|(((row>>(x%5))&1)<<13)))
  assert call('nes_resident211_begin',[resident,1,1,generation,write|1,0])==1
  plans.clear();before=count;assert call('nes_native_video211_plan',[state,lut,video,resident])==1
  instructions=count-before
  bank=u.mem_read(resident+layouts['nes_resident211']['target'],1)[0];serial=read32(resident+layouts['nes_resident211']['serial'])
  assert call('nes_resident211_commit',[resident,serial,generation,bank,1])==1
  data=bytes(u.mem_read(video,layouts['nes_native_video165']['size']))+bytes(u.mem_read(resident,layouts['nes_resident211']['size']))
  frames.append({'planner_instructions':instructions,'bank':bank,'plans':list(plans),'state_sha256':hashlib.sha256(data).hexdigest(),
                 'case':'warm' if i<4 else 'distinct rows' if i==14 else 'palette epochs' if i>=12 else 'coarseX/NT-X placement'})
 return {'firmware_sha256':sha(fw),'layouts':layouts,'frames':frames}

old=run(BASE/'probes/nes-nrom418/arm471-04/src');new=run(a.arm)
for x,y in zip(old['frames'],new['frames']):assert x['bank']==y['bank'] and x['plans']==y['plans'] and x['state_sha256']==y['state_sha256']
r={'passed':True,'old':old,'new':new,'scope':__doc__,'source_blocks_sha256':sha(a.blocks),'actual_RPC_inputs':rpc_inputs}
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':True,'old_instructions':[x['planner_instructions'] for x in old['frames']],'new_instructions':[x['planner_instructions'] for x in new['frames']]}))
