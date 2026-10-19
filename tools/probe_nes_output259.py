# SPDX-License-Identifier: MIT
"""Actual ARM instructions -> SPI pins -> RTL shared staging + bus consumer.

The service endpoint executes ordinary copy/fill and DMA bus operations; its
delays and ARM CPI are allocations, not an actual65816/full-MCU timing proof.
"""
import argparse,json,os,re,shutil,subprocess,time
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_output259 import sources
from probe_nes_arm259 import ARM,build,plans,verify,u16,u32,struct

TCL=r'''
onerror {quit -code 1}
set root sim:/output259_tb
run 10 us
set f [open ready.txt w];puts $f ready;close $f
set seq 1
while {$seq<10000} {
 if {![file exists req$seq]} {after 1;continue}
 set f [open req$seq r];set cmd [read $f];close $f
 lassign $cmd delay hex
 if {$hex eq "DONE"} {
  run 100 us
  if {[examine -radix unsigned $root/finished]!=1} {error "no final display retirement"}
  quit -code 0
 }
 run $delay ns
 set f [open spi-tx.hex w]
 foreach {a b} [split $hex {}] {puts $f "$a$b"}
 close $f
 set n [expr {[string length $hex]/2}]
 force -deposit $root/transfer_length 10#$n
 force -deposit $root/transfer_start 1
 run 10 ns
 force -deposit $root/transfer_start 0
 set duration [expr {$n*3047.616+1000}]
 run $duration ns
 if {[examine -radix unsigned $root/transfer_done]!=1} {error "SPI engine timeout"}
 set f [open spi-rx.txt r];set reply [read $f];close $f
 set f [open rsp$seq.tmp w];puts $f $reply;close $f;file rename rsp$seq.tmp rsp$seq
 incr seq
}
error "RPC count exceeded"
'''

class RTL:
 def __init__(self,d,sim,cpi):self.d=d;self.sim=sim;self.seq=0;self.packets=[];self.transfers=[];self.instruction_last=0;self.cpi=cpi
 def transfer(self,tx):
  self.seq+=1;instructions=self.arm.instructions-self.instruction_last
  self.instruction_last=self.arm.instructions
  f=self.d/'request.tmp';f.write_text(f'{instructions*self.cpi*1000/84:.3f} {tx.hex()}');f.rename(self.d/f'req{self.seq}')
  limit=time.monotonic()+120;r=self.d/f'rsp{self.seq}'
  while True:
   assert self.sim.poll() is None,(self.d/'vsim.log').read_text(errors='replace')[-3000:]
   assert time.monotonic()<limit,'SPI RPC timeout';time.sleep(.002)
   try:
    rx=bytes.fromhex(r.read_text());break
   except (FileNotFoundError,PermissionError):continue
  assert len(rx)==len(tx);self.transfers.append((tx,rx,instructions))
  if tx[0]==0xe1:self.packets.append(tx[1:-2])
  return rx

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--frame',type=int,default=954);p.add_argument('--cpi',type=int,default=1);p.add_argument('--fetch-wait',type=int,default=4)
 p.add_argument('--queue-seed',type=int,default=0)
 a=p.parse_args();assert 0<=a.queue_seed<=65535;d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True);build(d)
 prior,groups=plans();serial=a.frame-904;packets=groups[serial];gen=u16(packets[0],8)
 (d/'expected.hex').write_text((prior/f'expected-{gen}.bin').read_bytes().hex(' '));(d/'prior.hex').write_text(((prior/f'expected-{gen-2}.bin').read_bytes() if gen>2 else bytes(8570)).hex(' '))
 alltiles=bytearray();descs=[];inputs={}
 for f in sorted(prior.glob('req-*.bin')):
  b=f.read_bytes()
  if u32(b,4)!=serial:continue
  inputs[str(f.relative_to(BASE))]=sha(f)
  if b[0]==7:
   tf=prior/f.name.replace('req-','tile-');tile=tf.read_bytes();assert len(tile)==u16(b,14);inputs[str(tf.relative_to(BASE))]=sha(tf)
   descs.append((b[1]<<48)|((u16(b,10)//(32 if b[1] else 16))<<32)|len(tile));alltiles+=tile
 (d/'tiles.hex').write_text(alltiles.hex(' '));(d/'tile-desc.hex').write_text('\n'.join(f'{v:016x}' for v in descs)+'\n');(d/'sizes.txt').write_text(f'{len(descs)} {len(alltiles)}')
 src=sources()
 for n,s in src.items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 for n in ['nes_domain_reset124.sv','nes_native_mailbox206.sv','nes_bulk_aperture188.sv']:
  f=BASE/'probes/nes-mux258/test07'/n;shutil.copyfile(f,d/n);src[n]=''
 shutil.copyfile(ROOT/'tests/nes-functional/output259_tb.sv',d/'output259_tb.sv');(d/'rpc.do').write_text(TCL,newline='\n')
 def run(exe,args,label):
  with (d/(label+'.log')).open('wb') as out:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  log=(d/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-4000:]
 run('vlib',['work'],'vlib');run('vlog',['-sv',*src,'output259_tb.sv'],'vlog')
 with (d/'vsim.log').open('wb') as log:
  sim=subprocess.Popen([str(a.questa_bin/'vsim.exe'),'-c','-voptargs=+acc','work.output259_tb',f'-gSERIAL={serial}',f'-gGEN={gen}',f'-gFETCH_WAIT={a.fetch_wait}',f'-gQUEUE_SEED={a.queue_seed}','-do','do rpc.do'],cwd=d,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   limit=time.monotonic()+60
   while not (d/'ready.txt').exists():assert sim.poll() is None and time.monotonic()<limit;time.sleep(.02)
   endpoint=RTL(d,sim,a.cpi);arm=ARM(d/'output.elf',endpoint);endpoint.arm=arm;arm.call('reset259',[])
   if a.queue_seed:arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',a.queue_seed,a.queue_seed))
   blob=b''.join(len(p).to_bytes(2,'little')+p for p in packets);arm.uc.mem_write(0x20010000,blob)
   arm.uc.mem_write(0x20018000,(prior/f'expected-{gen}.bin').read_bytes());arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
   ok=arm.call('frame259',[0x20010000,len(blob),serial,gen]);assert ok==1,bytes(arm.uc.mem_read(arm.symbols['state259'],20)).hex()
   verify(packets,endpoint.packets)
   f=d/'done.tmp';f.write_text('0 DONE');f.rename(d/f'req{endpoint.seq+1}');code=sim.wait(timeout=30)
  finally:
   if sim.poll() is None:sim.kill();sim.wait()
 text=(d/'vsim.log').read_text(errors='replace');assert code==0 and 'PASS OUTPUT259' in text and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:]
 m=re.search(r'PASS OUTPUT259 ticks=(\d+) bytes=(\d+) chunks=(\d+) ordinary=(\d+) tilewait=(\d+) mapwait=(\d+)',text);assert m
 observed=dict(zip(['host_ticks','DMA_bytes','DMA_chunks','ordinary','tile_wait_ticks','map_wait_ticks'],map(int,m.groups())))
 (d/'transfers.json').write_text(json.dumps([(tx.hex(),rx.hex(),ins) for tx,rx,ins in endpoint.transfers]))
 result=dict(passed=True,frame=a.frame,scope=__doc__,CPI_assumed=a.cpi,tile_fetch_wait_NES_cycles=a.fetch_wait,ARM_instructions=arm.instructions,SPI_bytes=sum(len(tx) for tx,rx,ins in endpoint.transfers),packets=len(endpoint.packets),status_reads=sum(tx[0]==0xe0 for tx,rx,ins in endpoint.transfers),observed=observed,rtl_hashes={n:sha(d/n) for n in src},input_hashes=inputs,source_sha256=sha(ROOT/'tools/nes_output259.c'),actual_SNES=False,full_RUN=False,physical=False)
 result['queue_seed']=a.queue_seed;result['queue_final_sent']=int.from_bytes(arm.uc.mem_read(arm.symbols['state259'],2),'little')
 result['stack_observed']=0x2003f000-arm.low_sp
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rtl_hashes','input_hashes')}))

if __name__=='__main__':main()
