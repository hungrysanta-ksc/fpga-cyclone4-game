# SPDX-License-Identifier: MIT
"""Actual ARM verify to actual FPGA SPI via transaction-file bridge."""
import inspect
from pathlib import Path
from nes_delta231 import ROOT
s=(ROOT/'tools/check_nes_nrom460_verify.py').read_text(encoding='utf-8')
prefix=s[:s.index('state={};stats=')]
needle="p.add_argument('--out',required=True,type=Path);a=p.parse_args()";assert prefix.count(needle)==1;prefix=prefix.replace(needle,"p.add_argument('--out',required=True,type=Path);p.add_argument('--fault',choices=('source','corrupt'),default='source');a=p.parse_args()")
run=s[s.index('def run(name,'):s.index('def fresh(')]
body=r'''
import os
source_seen=0;spi_counts=collections.Counter();rpc_seq=1
def rpc(op,data=b'',want=0):
 global rpc_seq
 root=Path('H-%06d'%rpc_seq);rpc_seq+=1
 request=bytes([op,0,0,0,len(data)&255,len(data)>>8,0,0])+data
 temp=Path(str(root)+'.tmp');req=Path(str(root)+'.req');rsp=Path(str(root)+'.rsp');temp.write_bytes(request);os.replace(temp,req)
 began=time.monotonic()
 while True:
  try:value=rsp.read_bytes();break
  except (FileNotFoundError,PermissionError):
   assert time.monotonic()-began<120,'RTL response timeout';time.sleep(.001)
 assert len(value)==want,(op,len(value),want);return value
def finish(uc,value):uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
def callback(uc,address,size,user):
 global source_seen
 if address==sentinel:uc.emu_stop();return
 if address==source_callback:
  at=uc.reg_read(UC_ARM_REG_R1);out=uc.reg_read(UC_ARM_REG_R2);assert at==source_seen;source_seen+=1
  if at==16 and a.fault=='source':finish(uc,0);return
  uc.mem_write(out,bytes([source_byte(at)^(1 if at==16 and a.fault=='corrupt' else 0)]));finish(uc,1);return
 if address==symbols['nes_cf86_monitoring094']:finish(uc,0);return
 if address!=symbols['nes_game149_transfer']:return
 tx=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),8));spi_counts[tx[0]]+=1
 rx=rpc(1,tx,8);uc.mem_write(uc.reg_read(UC_ARM_REG_R2),rx);finish(uc,1)
for address in (sentinel,source_callback,symbols['nes_cf86_monitoring094'],symbols['nes_game149_transfer']):u.hook_add(UC_HOOK_CODE,callback,begin=address,end=address)
'''
end=r'''
def report_value():
 x=bytes(u.mem_read(report,8));return {'compared':int.from_bytes(x[:4],'little'),'error':x[4],'stop_ok':x[5]}
ok=run('nes_rom_verify',io,0x60000,source_callback|1,0,stack_arg=report);rep=report_value()
assert ok==0 and rep=={'compared':16,'error':4 if a.fault=='source' else 6,'stop_ok':1} and spi_counts[0x64]==1 and spi_counts[0x67]==(16 if a.fault=='source' else 17) and spi_counts[0x68]==16 and spi_counts[0x63]==0,(ok,rep,spi_counts)
rpc(9)
r={'passed':True,'fault':a.fault,'firmware_sha256':sha(fw),'rom_sha256':sha(rom),'report':rep,'spi_counts':{hex(k):v for k,v in sorted(spi_counts.items())},'scope':'actual 418 ARM verify and SPI framing, actual 457 board RTL via file RPC; seeded loader/PSRAM; source fails or differs at 16; no actual ARM peripheral/IRQ or physical timing'}
(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
exec(compile(prefix+body+run+end,'arm461','exec'))
