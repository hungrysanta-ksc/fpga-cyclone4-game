# SPDX-License-Identifier: MIT
"""Actual ARM base-only recovery control with modeled failure responses."""
import argparse,collections,hashlib,json,struct,sys,time
from pathlib import Path
from nes_delta231 import BASE,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--fault',choices=['none','program','done','busy','token'],default='none');p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
obj=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm';rom=BASE/'probes/nes-nrom428/fixture01/nrom16.nes';raw=rom.read_bytes();assert sha(fw)=='596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c';assert sha(rom)=='61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c'
names=['nes_cf86_fail094','nes_rom_verify','nes_rom_verified_start','nes_rom_spi_frame','nes_nrom406_header','nes_nrom406_layout','load_crc','nes_menu_sd_probe','nes_diag_sd_handoff113','nes_checkpoint_begin112','nes_checkpoint112','nes_cf86_enter094','nes_css_begin108','nes_menu_entry_only113','nes_menu_base_only116','nes_cf86_check094','nes_cf86_failed094','nes_cf86_finish094','nes_cf86_monitoring094','nes_diag_sd_failed','nes_return_failed','nes_return_fail','nes_menu_diagnostic_pending','nes_diag_leave','nes_diag_progress','nes_diag_fpga_pgm','snes_reset','slow_end','slow_begin','configured','nes_return_spi_ready','nes_cf86_arm094','native_session165','nes_display_leave146','nes_game149_transfer','fpga_test','f_open','f_read','f_close','f_lseek','gpio_owned','nes_run136']
with elf.open('rb') as f:
 e=ELFFile(f);segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_filesz']];symbols={x.name:(x['st_value']&~1 if x['st_info']['type']=='STT_FUNC' else x['st_value']) for x in e.get_section_by_name('.symtab').iter_symbols() if x.name in names};sizes={x.name:x['st_size'] for x in e.get_section_by_name('.symtab').iter_symbols() if x.name in names};assert set(symbols)==set(names),set(names)-set(symbols)
 for typename,required in [('nes_mcu_load_report',{'result':0,'acknowledged_bytes':4,'end_accepted':13,'stop_ok':14,'base_restored':15,'recovery_attempted':16}),('nes_sd_readback_report',{'load':0,'verify':20,'verified':28}),('nes_run136_report',{'first':0,'last':4,'stopped':8})]:
  found=[]
  for cu in e.get_dwarf_info().iter_CUs():
   for z in cu.iter_DIEs():
    n=z.attributes.get('DW_AT_name')
    if z.tag=='DW_TAG_structure_type' and n and n.value.decode(errors='ignore')==typename:
     fields={c.attributes['DW_AT_name'].value.decode():c.attributes['DW_AT_data_member_location'].value for c in z.iter_children() if 'DW_AT_name' in c.attributes and 'DW_AT_data_member_location' in c.attributes};found.append(fields)
  assert found and all(all(fields[k]==[35,v] for k,v in required.items()) for fields in found),(typename,found)
flash=fw.read_bytes()
for name in ('nes_menu_sd_probe','nes_rom_verify','nes_rom_verified_start','nes_rom_spi_frame','nes_nrom406_header','nes_nrom406_layout','load_crc'):
 address=symbols[name];base,seg=next((b,v) for b,v in segments if b<=address and address+sizes[name]<=b+len(v));blob=seg[address-base:address-base+sizes[name]];assert flash[address-0x0800c000:address-0x0800c000+len(blob)]==blob
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000);u.mem_map(0x40000000,0x100000);u.mem_map(0xe000e000,0x2000)
for address,blob in segments:u.mem_write(address,blob)
u.mem_write(0x40013008,struct.pack('<I',2))
sentinel=0x0807fff0;path=0x20001000;image=0x20001100;out=0x20001200;stack=0x2001e000;u.mem_write(path,b'nrom.nes\0');u.mem_write(image,b'/sd2snes/fpga_nrom16.bi3\0')
expected=bytearray(0x60000);expected[:0x4000]=raw[16:0x4010];expected[0x40000:0x42000]=raw[0x4010:0x6010];memory=bytearray(0x60000);state={'flags':0,'count':0,'cursor':0,'pos':0};calls=collections.Counter();ops=collections.Counter();config=[];table=[]
for b in range(256):
 c=b
 for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
 table.append(c)
true_hooks={'nes_menu_base_only116','nes_diag_sd_handoff113','nes_checkpoint_begin112','nes_checkpoint112','nes_cf86_enter094','nes_css_begin108','nes_cf86_check094','nes_cf86_finish094','nes_cf86_arm094','nes_return_spi_ready','configured','nes_display_leave146'}
false_hooks={'nes_menu_entry_only113','nes_cf86_failed094','nes_cf86_monitoring094','nes_diag_sd_failed','nes_return_failed','nes_menu_diagnostic_pending'}
void_hooks={'nes_return_fail','nes_diag_leave','nes_diag_progress','snes_reset'}
def finish(uc,v):uc.reg_write(UC_ARM_REG_R0,v);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
def hook(uc,address,n,user):
 if address==sentinel:uc.emu_stop();return
 name=next(k for k,v in symbols.items() if v==address);calls[name]+=1
 if name=='nes_cf86_fail094':state['fault_latched']=True;finish(uc,0);return
 if name=='configured':finish(uc,not (a.fault=='done' and len(config)==2));return
 if name in true_hooks:finish(uc,1);return
 if name in false_hooks or name in void_hooks:finish(uc,0);return
 if name=='slow_begin':uc.mem_write(symbols['gpio_owned'],b'\1');finish(uc,1);return
 if name=='slow_end':uc.mem_write(symbols['gpio_owned'],b'\0');finish(uc,0);return
 if name=='nes_diag_fpga_pgm':
  ptr=uc.reg_read(UC_ARM_REG_R0);chars=bytearray()
  while True:
   v=uc.mem_read(ptr,1)[0];ptr+=1
   if not v:break
   chars.append(v)
  config.append(chars.decode())
  if a.fault=='busy' and len(config)==2:uc.mem_write(0x40013008,struct.pack('<I',0x82))
  finish(uc,not (a.fault=='program' and len(config)==2));return
 if name=='fpga_test':finish(uc,0 if a.fault=='token' else 0xa5);return
 if name=='native_session165':uc.mem_write(symbols['nes_run136'],struct.pack('<II',20,40));finish(uc,1);return
 if name=='f_open':
  fp=uc.reg_read(UC_ARM_REG_R0);uc.mem_write(fp,b'\0'*16);uc.mem_write(fp+12,struct.pack('<I',len(raw)));state['pos']=0;finish(uc,0);return
 if name=='f_read':
  fp=uc.reg_read(UC_ARM_REG_R0);dest=uc.reg_read(UC_ARM_REG_R1);n=uc.reg_read(UC_ARM_REG_R2);got=uc.reg_read(UC_ARM_REG_R3);chunk=raw[state['pos']:state['pos']+n];uc.mem_write(dest,chunk);state['pos']+=len(chunk);uc.mem_write(fp+8,struct.pack('<I',state['pos']));uc.mem_write(got,struct.pack('<I',len(chunk)));finish(uc,0);return
 if name=='f_lseek':
  fp=uc.reg_read(UC_ARM_REG_R0);state['pos']=uc.reg_read(UC_ARM_REG_R1);uc.mem_write(fp+8,struct.pack('<I',state['pos']));finish(uc,0);return
 if name=='f_close':finish(uc,0);return
 if name!='nes_game149_transfer':raise AssertionError(name)
 tx=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),8));rxp=uc.reg_read(UC_ARM_REG_R2);op=tx[0];at=int.from_bytes(tx[1:4],'big');v=tx[4];ops[op]+=1;rx=bytearray(8)
 if 0x60<=op<=0x6a:
  c=0
  for x in tx[:6]:c=table[c^x]
  assert tx[5]==(v^255) and tx[6]==c and tx[7]==0xa5
  rx[1]=0x78;count=state['count']
  if op==0x65:rx[2]=state['flags']
  elif op==0x60:assert state['flags']==0 and at==0 and v==2;state['flags']=1
  elif op==0x61:assert state['flags']==1 and at==state['count'] and v==expected[at];memory[at]=v;state['count']+=1
  elif op==0x62:assert state['flags']==1 and at==state['count']==0x60000;state['flags']=2
  elif op==0x66:assert state['flags']==2 and at==0;state['flags']=0x22
  elif op==0x67:assert state['flags']==0x22 and at==state['cursor'];state['flags']=0x62
  elif op==0x6a:assert state['flags']==0x62;rx[2]=0x62;rx[3]=memory[state['cursor']];count=state['cursor']
  elif op==0x68:assert state['flags']==0x62 and at==state['cursor'] and v==memory[at];state['cursor']+=1;state['flags']=0x22
  elif op==0x69:assert state['flags']==0x22 and at==state['cursor']==state['count'];state['flags']=0x82
  elif op==0x63:assert state['flags']==0x82 and at==state['count'];state['flags']=0x86
  elif op==0x64:assert state['flags']==0 and at==state['count']==0;state['flags']=0
  else:raise AssertionError(('opcode',op))
  rx[4:7]=count.to_bytes(3,'big')
 elif op==0x70:rx[1]=0xe5;rx[2]=1;rx[4:8]=(50 if state['flags']==2 else 0).to_bytes(4,'big')
 elif op==0x73:rx[1]=0xe6;rx[2]=6;rx[6]=1;rx[7]=2
 elif op==0x77:rx[1]=0xe5;rx[5]=1;rx[6]=96;rx[7]=3
 elif op==0x76:rx[1]=0xe5;rx[7]=1
 else:raise AssertionError(('aux opcode',op))
 uc.mem_write(rxp,bytes(rx));finish(uc,1)
for name in true_hooks|false_hooks|void_hooks|{'nes_cf86_fail094','slow_begin','slow_end','configured','nes_diag_fpga_pgm','fpga_test','native_session165','f_open','f_read','f_close','f_lseek','nes_game149_transfer'}:u.hook_add(UC_HOOK_CODE,hook,begin=symbols[name],end=symbols[name])
u.hook_add(UC_HOOK_CODE,hook,begin=sentinel,end=sentinel)
for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(path,image,0,out)):u.reg_write(reg,value)
u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,sentinel|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000);started=time.monotonic();u.emu_start(symbols['nes_menu_sd_probe']|1,sentinel+2,count=5000000000);assert u.reg_read(UC_ARM_REG_PC)==sentinel,'ARM instruction limit'
result=bytes(u.mem_read(out,36));safe=u.reg_read(UC_ARM_REG_R0)
assert safe==int(a.fault=='none') and result[15]==int(a.fault=='none') and result[16]==1 and result[28]==0
assert ops[0x63]==0 and ops[0x64]==1 and calls['f_open']==0 and calls['native_session165']==0 and len(config)==2
assert calls['nes_diag_leave']==int(a.fault=='none') and calls['nes_cf86_fail094']==int(a.fault!='none'),dict(calls)
r={'passed':True,'fault':a.fault,'safe_return':safe,'base_restored':result[15],'recovery_attempted':result[16],'verified':result[28],'calls':dict(calls),'config_paths':config,'firmware_sha256':sha(fw),'scope':'actual menu cleanup ARM machine code; base-only diagnostic skips payload; programmer/DONE/SPI/token/guard are modeled; no hardware recovery or reset electrical proof'}
(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
