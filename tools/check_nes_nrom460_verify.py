# SPDX-License-Identifier: MIT
"""Actual 418 ARM verification/START against independently modeled SPI/PSRAM."""
from pathlib import Path
import argparse,collections,json,struct,sys,time
from nes_delta231 import BASE,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
obj=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm';rom=BASE/'probes/nes-nrom428/fixture01/nrom16.nes';raw=rom.read_bytes();assert sha(fw)=='596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c';memory=bytearray(0x60000);memory[:0x4000]=raw[16:0x4010];memory[0x40000:0x42000]=raw[0x4010:0x6010]
def source_byte(at):
 return raw[16+at] if at<16384 else raw[16400+at-0x40000] if 0x40000<=at<0x42000 else 0
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000);symbols={};matches={};flash=fw.read_bytes()
with elf.open('rb') as f:
 e=ELFFile(f);segs=[x for x in e.iter_segments() if x['p_type']=='PT_LOAD'];
 layouts=[]
 for cu in e.get_dwarf_info().iter_CUs():
  for die in cu.iter_DIEs():
   n=die.attributes.get('DW_AT_name')
   if die.tag=='DW_TAG_structure_type' and n and n.value==b'nes_verify_report':
    fields={c.attributes['DW_AT_name'].value.decode():c.attributes['DW_AT_data_member_location'].value for c in die.iter_children() if 'DW_AT_name' in c.attributes and 'DW_AT_data_member_location' in c.attributes};layouts.append((die.attributes['DW_AT_byte_size'].value,fields))
 assert layouts and all(x==(8,{'compared':[35,0],'error':[35,4],'stop_ok':[35,5]}) for x in layouts),layouts
 for seg in segs:
  if seg['p_filesz']:u.mem_write(seg['p_vaddr'],seg.data())
 for x in e.get_section_by_name('.symtab').iter_symbols():
  if x.name in ('nes_rom_verify','nes_rom_verified_start','nes_rom_spi_frame','nes_rom_spi_transfer','nes_game149_transfer','nes_cf86_monitoring094'):
   address=x['st_value']&~1;size=x['st_size'];seg=next(z for z in segs if z['p_vaddr']<=address and address+size<=z['p_vaddr']+z['p_filesz']);blob=seg.data()[address-seg['p_vaddr']:address-seg['p_vaddr']+size];at=address-0x0800c000;assert at>=0 and flash[at:at+size]==blob;symbols[x.name]=address;matches[x.name]={'elf_address':address,'size':size,'stm_offset':at}
assert len(symbols)==6
sentinel=0x0807fff0;source_callback=0x0807ffe0;io=0x20001000;report=0x20001100;stack=0x2001e000
state={};stats=collections.Counter();table=[]
for b in range(256):
 c=b
 for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
 table.append(c)
def finish(uc,value):uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
def callback(uc,address,size,user):
 if address==sentinel:uc.emu_stop();return
 if address==source_callback:
  at=uc.reg_read(UC_ARM_REG_R1);out=uc.reg_read(UC_ARM_REG_R2);assert at==state['next_source'] and at<len(memory);state['next_source']+=1
  if state.get('source_fail')==at:finish(uc,0);return
  uc.mem_write(out,bytes([source_byte(at)]));finish(uc,1);return
 if address==symbols['nes_cf86_monitoring094']:finish(uc,0);return
 if address!=symbols['nes_game149_transfer']:return
 tx=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),8));rxp=uc.reg_read(UC_ARM_REG_R2);op=tx[0];at=int.from_bytes(tx[1:4],'big');value=tx[4];c=0
 for b in tx[:6]:c=table[c^b]
 assert tx[5]==(value^255) and tx[6]==c and tx[7]==0xa5;stats[op]+=1
 rx=bytearray(8);rx[1]=0x78
 if op==0x65:rx[2]=state['flags'];count=state['count']
 elif op==0x66:assert state['flags']==2 and at==0;state['flags']=0x22;count=state['count']
 elif op==0x67:assert state['flags']==0x22 and at==state['cursor'];state['flags']=0x62;count=state['count']
 elif op==0x6a:
  assert state['flags']==0x62;rx[2]=0x62;rx[3]=memory[state['cursor']]^(1 if state.get('corrupt')==state['cursor'] else 0);count=state['cursor']+(1 if state.get('bad_tag')==state['cursor'] else 0)
 elif op==0x68:assert state['flags']==0x62 and at==state['cursor'] and value==memory[at];state['cursor']+=1;state['flags']=0x22;count=state['count']
 elif op==0x69:assert state['flags']==0x22 and at==state['count'] and state['cursor']==state['count'];state['flags']=0x82;count=state['count']
 elif op==0x63:assert state['flags']==0x82 and at==state['count'];state['flags']=0x86;count=state['count']
 elif op==0x64:state['flags']=0;state['count']=0;count=0
 else:raise AssertionError(('unexpected SPI command',hex(op),at))
 rx[4:7]=count.to_bytes(3,'big');uc.mem_write(rxp,bytes(rx));finish(uc,1)
for address in (sentinel,source_callback,symbols['nes_cf86_monitoring094'],symbols['nes_game149_transfer']):u.hook_add(UC_HOOK_CODE,callback,begin=address,end=address)
def run(name,*args,stack_arg=None):
 for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,v)
 u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,sentinel|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000)
 if stack_arg is not None:u.mem_write(stack,struct.pack('<I',stack_arg))
 u.emu_start(symbols[name]|1,sentinel+2,count=3000000000);assert u.reg_read(UC_ARM_REG_PC)==sentinel,'ARM instruction limit';return u.reg_read(UC_ARM_REG_R0)
def fresh(**kwargs):state.clear();state.update(flags=2,count=0x60000,cursor=0,next_source=0,**kwargs);stats.clear()
def report_value():
 x=bytes(u.mem_read(report,8));return {'compared':int.from_bytes(x[:4],'little'),'error':x[4],'stop_ok':x[5]}
start=time.monotonic();results={}
fresh();ok=run('nes_rom_verify',io,0x60000,source_callback|1,0,stack_arg=report);rep=report_value();assert ok==1 and rep=={'compared':0x60000,'error':0,'stop_ok':0} and state['flags']==0x82 and state['cursor']==0x60000
assert run('nes_rom_verified_start',io,0x60000)==1 and state['flags']==0x86;results['complete']={'report':rep,'spi_counts':{hex(k):v for k,v in sorted(stats.items())}}
for label,kw,err in [('corrupt',{'corrupt':256},6),('tag',{'bad_tag':64},5),('source',{'source_fail':33},4)]:
 fresh(**kw);ok=run('nes_rom_verify',io,0x60000,source_callback|1,0,stack_arg=report);rep=report_value();assert ok==0 and rep['error']==err and rep['stop_ok']==1 and state['flags']==0 and stats[0x64]==1,(label,rep,state);results[label]={'report':rep,'spi_counts':{hex(k):v for k,v in sorted(stats.items())}}
r={'passed':True,'firmware_sha256':sha(fw),'elf_sha256':sha(elf),'rom_sha256':sha(rom),'linked_functions':matches,'cases':results,'wall_seconds':round(time.monotonic()-start,3),'scope':'actual linked ARM verification/START/frame code in Unicorn; SPI/PSRAM and source callback modeled; no actual FPGA or IRQ, no real-time measurement'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
