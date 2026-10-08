# SPDX-License-Identifier: MIT
"""Check retained101 sources and independently interpret straight-line ARM MMIO."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_spi_boot import ROOT,sha
from test_nes_menu098 import definition

def interpret(text,seed):
 A=0x40020000;B=A+0x400;S=0x40013000;C=0x40023800
 m={A:0xa5a5a5a5^seed,A+4:0xa55a^seed,B:0x5a5a5a5a^seed,B+4:0x5aa5^seed,S:0xff^seed,C+36:0x4002^seed}
 original=dict(m);r={};writes=[];barriers=[];literal={}
 for line in text.splitlines():
  q=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]+\s+\.word\s+0x([0-9a-f]+)',line)
  if q:literal[int(q[1],16)]=int(q[2],16)
 for line in text.splitlines():
  q=re.match(r'\s*[0-9a-f]+:\s+(?:[0-9a-f]{4}\s+){1,2}([a-z][a-z.]+)\s+(.*)',line)
  if not q:continue
  op=q[1].split('.')[0];args=q[2].split('@')[0].strip()
  if op=='ldr' and '[pc,' in args:
   reg=args.split(',')[0];addr=int(re.search(r'@ \(([0-9a-f]+)',line)[1],16);r[reg]=literal[addr]
  elif op in ['ldr','str']:
   v=re.fullmatch(r'(r\d+), \[(r\d+), #(\d+)\]',args);assert v,line
   reg,base,offset=v.groups();addr=r[base]+int(offset)
   if op=='ldr':r[reg]=m[addr]
   else:m[addr]=r[reg];writes.append((addr,r[reg]))
  elif op=='movs' or op=='mov':
   v=re.fullmatch(r'(r\d+), #(\d+)',args);assert v,line;r[v[1]]=int(v[2])
  elif op in ['bic','orr','add','sub']:
   v=re.fullmatch(r'(r\d+), (r\d+), #(\d+)',args);assert v,line
   dest,src,k=v.groups();k=int(k);r[dest]={'bic':lambda:r[src]&~k,'orr':lambda:r[src]|k,'add':lambda:r[src]+k,'sub':lambda:r[src]-k}[op]()&0xffffffff
  elif op=='dsb':barriers.append(len(writes))
  elif op=='bx':assert args=='lr';break
  else:raise AssertionError(line)
 bm=original[B];b3=(bm&~192)|64;b5=(b3&~3072)|1024;b4=b5&~768
 expected=[(A+24,16),(A+4,original[A+4]&~16),(A,(original[A]&~768)|256),(B+24,8<<16),(B+24,32<<16),(B+4,original[B+4]&~40),(B,b3),(B,b5),(B,b4),(S+4,0),(S,original[S]&~64),(C+36,original[C+36]|4096)]
 assert writes==expected,(writes,expected);assert barriers==[3,9,12],barriers
 return dict(seed=seed,writes=writes,barrier_after_store=barriers)

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','pins','main','evidence101','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';e=a.evidence101
 m=json.loads((ROOT/'analysis/spi101-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files'];retained={}
 for n in ['stm32f4xx/spi.c','stm32f4xx/spi.h','fpga_spi.h','main.c','snes.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','nes_diag_runtime.h','stm32f4xx/rtc.c','stm32f4xx/uart.c','stm32f4xx/timer.c','stm32f4xx/sdnative.c','nes_cf86_session094.c']:
  assert sha(s/n)==pins['arm02/src/'+n],n;retained[n]=sha(s/n)
 for host in [a.pins,a.main]:
  assert (host/'production-platform102.c').read_text()==(s/'nes_diag_platform.c').read_text()
  assert (host/'quiesce102-original.inc').read_text()==definition((s/'nes_diag_platform.c').read_text(),'nes_diag_spi_quiesce102')
 assert (a.main/'main098.inc').read_bytes()==(e/'main02/main098.inc').read_bytes()
 assert (a.main/'load098.inc').read_bytes()==(e/'main02/load098.inc').read_bytes()
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm';d={}
 for n in ['main','nes_diag_spi_quiesce102','nes_diag_blocked','snes_reset','spi_tx_sync']:
  b=subprocess.check_output([str(a.objdump),'-d','--disassemble='+n,str(elf)]);(a.arm/(n+'-checked102.txt')).write_bytes(b);d[n]=b.decode();assert '<'+n+'>:' in d[n]
 block=d['nes_diag_blocked'];assert block.index('<snes_reset>')<block.index('<nes_diag_spi_quiesce102>')<block.index('<nes_diag_active>')<block.index('<nes_diag_progress>')
 assert '<nes_diag_blocked>' in d['main'] and 'dsb' in block and 'isb' in block
 assert '0x40020000' in d['snes_reset'] and '<nes_return_spi_wait>' in d['spi_tx_sync']
 traces=[interpret(d['nes_diag_spi_quiesce102'],x*0x1020304) for x in range(16)]
 (a.arm/'mmio-arm102.json').write_text(json.dumps(traces,indent=2)+'\n')
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),retained101=retained,arm_mmio_cases=16,ordered_stores=12,barriers=[3,9,12],terminal_quiesce_model=True,first_fault_to_quiesce_latency_proven=False,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS102 actual ARM terminal calls and16 exact ordered MMIO interpretations')
if __name__=='__main__':main()
