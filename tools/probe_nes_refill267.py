# SPDX-License-Identifier: MIT
"""Live Cortex-M4 serializer -> physical SPI pins ->266 queue and consumer.

The foreground executes real ARM instructions and polls live RTL credits.
CPI is an explicit sensitivity, not a measured Cortex-M4 cycle bound.
Optional ROM mode executes real E8/E9 refill and tile/reader RTL. Optional CPU
mode replays actual65816 ordinary-command bus traces. Map/tile DMA and final
display ACK still use the inherited bus model; this is not a full RUN.
"""
from pathlib import Path
import argparse,collections,csv,json,os,shutil,struct,subprocess,sys,time
from nes_delta231 import BASE,ROOT,sha,once
from probe_nes_joint266 import prepare as prior_prepare,run
from probe_nes_arm264 import ARM,build,plans,u16,verify


class Live:
 def __init__(self,d,irq=False):
  self.d=d;self.seq=0;self.before=0;self.arm=None;self.transfers=[];self.packets=[];self.now=0;self.next_irq=10000000;self.irq_rows=[];self.irq=None
  if irq:
   from probe_nes_irq267 import IRQ
   self.irq=IRQ()
 def transfer(self,tx):
  self.seq+=1;instructions=self.arm.instructions-self.before;self.before=self.arm.instructions
  irq_instructions=0
  while self.irq and self.now>=self.next_irq:
   row=self.irq.call('SysTick_Handler');row.update(due_RTL_ns=self.next_irq,service_RTL_ns=self.now);self.irq_rows.append(row)
   irq_instructions+=row['instructions'];self.next_irq+=10000000
  p=self.d/'arm-request.tmp';p.write_text(f'{len(tx)} {instructions+irq_instructions}\n'+tx.hex(' '),encoding='ascii');p.rename(self.d/f'arm-req{self.seq}')
  p=self.d/f'arm-rsp{self.seq}';deadline=time.monotonic()+180
  while True:
   try:lines=p.read_text().splitlines();break
   except (FileNotFoundError,PermissionError):
    if time.monotonic()>deadline:raise TimeoutError(f'ARM transfer {self.seq}')
    time.sleep(.001)
  low,high=map(int,lines[0].split());now=low+(high<<32);rx=bytes.fromhex(lines[1]) if tx else b'';assert len(rx)==len(tx)
  self.now=now;self.transfers.append(dict(tx=tx.hex(),rx=rx.hex(),instructions=instructions,IRQ_instructions=irq_instructions,RTL_ns=now))
  if tx and tx[0]==0xe1:self.packets.append(tx[1:-2])
  return rx


def worker(d,last,irq=False,rom=False):
 ep=Live(d,irq);arm=ARM(d/'output.elf',ep);ep.arm=arm;arm.call('reset259',[]);prior,groups=plans();rows=[]
 if rom:arm.symbols['io259']=arm.symbols['physical267']
 for f in range(905,last+1):
  deadline=time.monotonic()+600
  while not (d/f'arm-frame{f}').exists():
   if time.monotonic()>deadline:raise TimeoutError(f'frame {f}')
   time.sleep(.01)
  pp=groups[f-904];blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp)
  arm.uc.mem_write(0x20010000,blob);arm.uc.mem_write(0x20018000,(prior/f'expected-{u16(pp[0],8)}.bin').read_bytes())
  arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  if rom:
   raw=(d/f'plans{f-904}.bin').read_bytes()+bytes([3,0,1,0x83,u16(pp[0],8)&255,u16(pp[0],8)>>8]);assert len(raw)<0x10000
   arm.uc.mem_write(0x20020000,raw)
   for name,value in [('plans267',0x20020000),('plan_bytes267',len(raw)),('plan_at267',0),('plan_sent267',0),('plan_error267',0),('plan_generation267',u16(pp[0],8))]:arm.uc.mem_write(arm.symbols[name],struct.pack('<I',value))
  start=len(ep.transfers);sent=len(ep.packets);before=arm.instructions
  ok=arm.call('frame259',[0x20010000,len(blob),f-904,u16(pp[0],8)])
  state=bytes(arm.uc.mem_read(arm.symbols['state259'],20)).hex()
  (d/f'arm{f}.json').write_text(json.dumps(dict(ok=ok,state=state,transfers=ep.transfers[start:]),indent=2)+'\n')
  assert ok==1,(f,state)
  verify(pp,ep.packets[sent:])
  if rom:assert arm.call('finish267',[])==1,(f,'plan retire')
  ep.transfer(b'')
  tr=ep.transfers[start:];rows.append(dict(frame=f,instructions=arm.instructions-before,packets=len(ep.packets)-sent,
   status_reads=sum(t['tx'].startswith('e0') for t in tr),SPI_bytes=sum(len(t['tx'])//2 for t in tr),last_RTL_ns=tr[-1]['RTL_ns']))
 (d/'arm-result.json').write_text(json.dumps(dict(passed=True,frames=rows,stack_observed=0x2003f000-arm.low_sp,
  live_RTL=True,hardware_cycles=False,full_RUN=False,IRQ_body_service_boundary=irq,IRQ_cases=ep.irq_rows,
  IRQ_entry_exit_cycles=None,IRQ_preemption_modeled=False),indent=2)+'\n')


def cpu_trace(d,trace,s,pins,last):
 r=json.loads((trace/'result.json').read_text());assert r['passed'] and r['CPU']['commands']==522
 for name in ['result.json','timing.csv','bus.csv','ordinary.sfc','capture.lua','packets.hex']:
  # Host temp evidence is copied inside the private run and pinned there.
  shutil.copyfile(trace/name,d/('CPU-'+name))
 grouped=collections.defaultdict(list)
 for row in csv.DictReader((trace/'bus.csv').open()):grouped[int(row['case'])].append({k:int(v) for k,v in row.items()})
 frames=collections.defaultdict(list)
 for row in csv.DictReader((trace/'timing.csv').open()):
  case=int(row['case']);events=grouped[case];start=events[0]['clock'];words=[len(events)]
  for e in events:
   delta=e['clock']-start;assert 0<=delta<1<<24
   words.append((delta<<40)|(e['write']<<32)|(e['address']<<8)|e['value'])
  frames[int(row['serial'])+904]+=words
 for f in range(905,last+1):(d/f'cpu{f}.hex').write_text(' '.join(f'{w:016x}' for w in frames[f]+[0])+'\n')
 extra=r'''
 reg [63:0] cpu267[0:65535];integer cpu_at267=0,cpu_cases267=0;
 task ordinary_cpu267;
 integer count267,ignore267,n267,read267,head267;reg [63:0] event267;reg [7:0] byte267;
 realtime start267,target267;reg executed267;
 begin
  count267=cpu267[cpu_at267];cpu_at267++;if(count267<16)$fatal(1,"missing CPU trace");
  start267=$realtime;read267=0;executed267=0;n267=dut.flow.qlen;head267=dut.flow.queue.retired;
  for(integer e=0;e<count267;e++)begin
   event267=cpu267[cpu_at267];cpu_at267++;
   target267=start267+event267[63:40]*1000.0/21.477272727;
   if(target267+0.001<$realtime)$fatal(1,"CPU bus events overlap");
   #(target267-$realtime);bus_address=event267[31:8];
   if(event267[32])begin
    if(!executed267)begin
     if(read267!=n267)$fatal(1,"CPU missing packet bytes");
     ignore267=call263(2,n267,0);executed267=1;
    end
    bus_in=event267[7:0];bus_write=0;#100;bus_write=1;#100;
   end else begin
    bus_read=0;#100;if(!bus_valid)$fatal(1,"CPU invalid bus %h",bus_address);byte267=bus_out;
    if(byte267!==event267[7:0])$fatal(1,"CPU trace data frame%0d addr%h got%h expected%h",f,bus_address,byte267,event267[7:0]);
    if(bus_address>=24'h400000&&bus_address<=24'h4000ff)begin ignore267=call263(1,read267,byte267);read267++;end
    bus_read=1;#100;
   end
  end
  if(!executed267)$fatal(1,"CPU no ACK");
  wait(dut.flow.queue.retired!=head267);ordinary263++;cpu_cases267++;
  $fwrite(events261,"cpu267,%0d,%0d,%0t\n",f,cpu_cases267,$realtime-start267);
 end endtask
'''
 s=once(s,' task ordinary_task263;',extra+'\n task ordinary_task263;')
 s=once(s,'    ordinary_task263();','''    if(dut.flow.header[0]==2||dut.flow.header[0]==4||dut.flow.header[0]==5||dut.flow.header[0]==8)ordinary_cpu267();
    else ordinary_task263();''')
 s=once(s,'  active263=1;producer_done263=0;', '''  name=$sformatf("cpu%0d.hex",f);$readmemh(name,cpu267);cpu_at267=0;
  active263=1;producer_done263=0;''')
 s=once(s,'  wait(start_ready);\n end endtask','  if(cpu267[cpu_at267]!=0)$fatal(1,"unconsumed CPU cases");\n  wait(start_ready);\n end endtask')
 return s


def prepare(d,last,trace=None,rom=None,baseline265=False):
 if baseline265:
  from probe_nes_joint265 import prepare as previous
  src,pins,stats=previous(d,last);s=(d/'joint265_tb.sv').read_text(encoding='utf-8').replace('joint265_tb','joint266_tb').replace('PASS JOINT265','PASS JOINT266')
 else:src,pins,stats=prior_prepare(d,last);s=(d/'joint266_tb.sv').read_text(encoding='utf-8')
 s=once(s,' parameter real PHASE=3.5;', ' parameter real CPI=1.0;\n import "DPI-C" function int bridge267(input int op,input int a,input int b);\n parameter real PHASE=3.5;')
 a=s.index('  prelude_task262();',s.index(' task output_frame;'));b=s.index('  wait(flow_retired);',a)
 s=s[:a]+'''  name=$sformatf("prelude%0d.hex",f);$readmemh(name,prelude262);
  active263=1;producer_done263=0;
  fork
   tiles_task263();
   begin : live_arm267
    integer n267,ignore267,delay267;reg finished267;
    ignore267=bridge267(0,f,0);if(ignore267<0)$fatal(1,"ARM rendezvous start");finished267=0;
    while(!finished267)begin
     n267=bridge267(1,0,0);if(n267<0)$fatal(1,"ARM rendezvous request");
     delay267=bridge267(5,0,0);#(delay267*CPI*1000.0/84.0);
     if(n267==0)finished267=1;
     else begin
      for(integer j=0;j<n267;j++)tx[j]=bridge267(2,j,0);
      transfer(n267);
      for(integer j=0;j<n267;j++)ignore267=bridge267(3,j,rx[j]);
      $fwrite(events261,"arm267,%0d,%0d,%0d,%0t,%0d\\n",f,tx[0],n267,$time,delay267);
     end
     ignore267=bridge267(4,int'($time),int'($time>>32));if(ignore267<0)$fatal(1,"ARM rendezvous response");
    end
    producer_done263=1;
   end
  join
'''+s[b:]
 # BEGIN now traverses the same actual ordinary read/ACK path as other packets.
 s=s.replace('PASS JOINT266','PASS REFILL267')
 if trace:s=cpu_trace(d,trace,s,pins,last)
 if rom:
  from nes_rom267 import bind
  s=bind(d,s,src,pins,rom)
  for f in range(905,last+1):shutil.copyfile(rom/f'plans{f-904}.bin',d/f'plans{f-904}.bin')
 (d/'joint266_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 for name in ['nes_bridge267.c','probe_nes_refill267.py','nes_refill267.c','nes_rom267.py','probe_nes_irq267.py']:
  p=ROOT/'tools'/name;shutil.copyfile(p,d/name);pins[p.relative_to(BASE).as_posix()]=sha(p)
 return src,pins


def build_rom(d):
 path=ROOT/'tools/nes_refill267.c';shutil.copyfile(path,d/path.name)
 s=(d/'stubs.s').read_text().replace('io259','physical267');(d/'stubs.s').write_text(s)
 arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map','nes_output264.c','nes_refill267.c','stubs.s','-o','output.elf'],d,'build-rom')
 run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size-rom')


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--last',type=int,default=907)
 p.add_argument('--questa-bin',type=Path);p.add_argument('--cpi',type=float,default=1);p.add_argument('--worker',action='store_true')
 p.add_argument('--cpu-trace',type=Path);p.add_argument('--irq',action='store_true');p.add_argument('--plans',type=Path);p.add_argument('--rom-window',type=int,default=0);p.add_argument('--baseline265',action='store_true');a=p.parse_args()
 d=a.out.resolve()
 if a.worker:return worker(d,a.last,a.irq,bool(a.plans))
 assert not d.exists() and d.as_posix().isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins=prepare(d,a.last,a.cpu_trace,a.plans,a.baseline265);build(d)
 if a.plans:build_rom(d)
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','nes_bridge267.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint266_tb.sv'],d,'vlog')
 with (d/'arm-worker.log').open('wb') as log:
  child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--out',str(d),'--last',str(a.last)]+(['--irq'] if a.irq else [])+(['--plans',str(d)] if a.plans else []),stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   result=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'-gCPI={a.cpi}']+([f'-gROM_WINDOW={a.rom_window}'] if a.plans else [])+[f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',3600)
   assert f'PASS REFILL267 frames={a.last-904}' in result
   assert child.wait(timeout=10)==0,(d/'arm-worker.log').read_text()
  finally:
   if child.poll() is None:child.kill();child.wait()
 arm=json.loads((d/'arm-result.json').read_text())
 r=dict(passed=True,frames=a.last-904,CPI=a.cpi,ARM=arm,scope=__doc__,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,
  ELF_sha256=sha(d/'output.elf'),tb_sha256=sha(d/'joint266_tb.sv'),actual_SNES=False,actual_SNES_bus_trace_replayed=bool(a.cpu_trace),
  actual_tile_ROM=bool(a.plans),ROM_window=a.rom_window,baseline265=a.baseline265,live_NES_core=False,full_RUN=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(passed=True,frames=len(arm['frames']),SPI_bytes=sum(x['SPI_bytes'] for x in arm['frames']),
  stack_observed=arm['stack_observed'],IRQ_bodies=len(arm.get('IRQ_cases',[])),actual_tile_ROM=bool(a.plans),SNES_bus_trace=bool(a.cpu_trace))))

if __name__=='__main__':main()
