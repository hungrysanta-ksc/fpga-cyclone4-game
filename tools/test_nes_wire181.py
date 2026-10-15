# SPDX-License-Identifier: MIT
"""Actual fill -> candidate exporter -> actual SPI -> actual C receiver.

The sealed frame query and PSRAM replies are deterministic fixtures. This does
not replace the separate collector/PPU tests or claim physical/game throughput.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('baseline','mcu','out','questa-bin','gcc','arm-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True);sources={}
 pins=json.loads((ROOT/'analysis/minreject180-verification.json').read_bytes())['verification']['sources']
 for n in ('nes_native_fill165.sv','nes_native_spi165.sv'):
  assert sha(a.baseline/n)==pins[n];shutil.copy2(a.baseline/n,a.out/n);sources['baseline/'+n]=sha(a.baseline/n)
 prep=json.loads((a.mcu.parent/'preparation-minreject180.json').read_bytes())
 mp={**prep['copied'],**prep['changed'],**prep['added']}
 for n in ('nes_trace166.h','nes_trace166.c'):
  assert sha(a.mcu/n)==mp['src/'+n];shutil.copy2(a.mcu/n,a.out/n);sources['mcu/'+n]=sha(a.mcu/n)
 new=['src/nes/video/nes_native_export181.sv','src/nes/firmware/nes_native181.h','src/nes/firmware/nes_native181.c',
      'tests/nes-functional/native_spi165_tb.sv','tests/nes-functional/wire181_source.svh','tests/nes-functional/wire181_host.c']
 for n in new:
  dest=Path(n).name.replace('nes_native181.','nes_native165.')
  shutil.copy2(ROOT/n,a.out/dest);sources[n]=sha(ROOT/n)
 s=(a.out/'native_spi165_tb.sv').read_text()
 def edit(old,new):
  nonlocal s
  assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new)
 edit('reg clk=0,reset=1,ss=1,sck=0,mosi=0,valid=0,ack_ready=1;','reg clk=0,reset=1,ss=1,sck=0,mosi=0; wire valid,ack_ready;')
 edit('reg [95:0] data=0;','wire [95:0] data;')
 edit('reg [95:0] records[0:4095];integer count,n,acks=0,blocks=0,wirebytes=0,fd;','integer acks=0,blocks=0,wirebytes=0,fd;\n `include "wire181_source.svh"')
 edit('3:width=3','3:width=4')
 edit('  if(!$value$plusargs("COUNT=%d",count))$fatal(1,"COUNT missing");\n  $readmemh("records.hex",records,0,count-1);fd=$fopen("transactions.txt","w");',
      '  record_fd=$fopen("records.hex","w");fd=$fopen("transactions.txt","w");')
 edit('#100;reset=0;#(PHASE);','#100;reset=0;#(PHASE);@(negedge clk);owned=1;')
 begin=s.index('   begin\n    for(n=0;n<count;n++)');end=s.index('   begin\n    got_commit=0;',begin)
 s=s[:begin]+'   begin wait(export_finished); end\n'+s[end:]
 # Keep normal real SPI path; old post-join negatives drive the now-wired
 # producer, so transport failure behavior is tested instead by C replay.
 begin=s.index('  $fclose(fd);trace_on=0;');end=s.index(' end\n initial begin #200000000',begin)
 s=s[:begin]+'''  $fclose(fd);$fclose(record_fd);
  if(fault||acks!=1||ee||chr_count!=48||raw_count!=PATCHES*256)$fatal(1,"terminal state");
  $display("PASS WIRE181RTL patches=%0d records=%0d blocks=%0d wirebytes=%0d cycles=%0d",PATCHES,exported,blocks,wirebytes,lease_ticks);$finish;
'''+s[end:]
 (a.out/'wire181_tb.sv').write_text(s,encoding='utf8')
 def run(exe,args,name,cwd=None,timeout=180):
  cwd=cwd or a.out
  with (cwd/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  text=(cwd/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-6000:]
  return text
 run(a.questa_bin/'vlib.exe',['work'],'vlib')
 run(a.questa_bin/'vlog.exe',['-sv','nes_native_fill165.sv','nes_native_spi165.sv','nes_native_export181.sv','wire181_tb.sv'],'vlog')
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I.','nes_native165.c','nes_trace166.c','wire181_host.c','-o','host.exe'],'gcc')
 # ARM ABI and compile-only stack evidence; not a full runtime link approval.
 arm=[]
 for variant in ('old','new'):
  d=a.out/variant;d.mkdir()
  for n in ('nes_native165.h','nes_native165.c','nes_trace166.h','nes_trace166.c'):
   shutil.copy2((a.mcu if variant=='old' else a.out)/n,d/n)
  (d/'layout.c').write_text('#include "nes_native165.h"\nchar receiver_size[sizeof(struct nes_native165)];\n',encoding='utf8')
  run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-Wall','-Wextra','-Werror','-c','nes_native165.c','nes_trace166.c','layout.c'],'gcc',d)
  nm=run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','layout.o'],'nm',d)
  size=int(re.search(r'\w+\s+([0-9a-fA-F]+)\s+\w\s+receiver_size',nm)[1],16);arm.append(size)
 assert arm[0]==arm[1],arm
 results=[]
 for patches in (0,1,7):
  d=a.out/('patch'+str(patches));d.mkdir();shutil.copytree(a.out/'work',d/'work')
  s=run(a.questa_bin/'vsim.exe',['-c','work.native_spi165_tb','-gPATCHES='+str(patches),'-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],'vsim',d)
  m=re.search(r'PASS WIRE181RTL patches=(\d+) records=(\d+) blocks=(\d+) wirebytes=(\d+) cycles=(\d+)',s);assert m
  rows=[int(l,16) for l in (d/'records.hex').read_text().splitlines()]
  # Independent exact fixture records, including full counts and phase marker.
  expected=[]
  def add(k,i,v):expected.append((k<<93)|(12<<77)|(i<<64)|v)
  add(7,0,(0x1811<<48)|(1<<42)|(1<<36)|(224<<28)|(1<<20)|(1<<12)|patches)
  for k,count in enumerate((33,224,1,1,224,32)):
   for i in range(count):
    v=(3,i%8,5,(7<<19)|(36<<6),0,i)[k]
    if k==4 and i>=32 and (i-32)%24==0 and (i-32)//24<patches:v=(1<<49)|(((i-32)//24)<<50)
    add(k,i,v)
  for tile,kind in ((3,1),(5,2),(7,1)):
   for lane in range(16):add(6,tile,(kind<<12)|(lane<<8)|((tile*17+lane*5)&255))
  count=len(expected)-1;add(7,4,(count<<16)|48)
  for i in range(patches*256):add(6,i,(i*3+(i//256)*11+(i%256)//7)&63)
  add(7,1,((count+patches*256)<<16)|(48+patches*256));add(7,3,0)
  assert rows==expected,(patches,next((i for i,(x,y) in enumerate(zip(rows,expected)) if x!=y),None),len(rows),len(expected))
  host=run(a.out/'host.exe',[d/'transactions.txt',d/'records.hex',patches],'host',d)
  hm=re.search(r'PASS WIRE181 patches=\d+ pixels=(\d+) checks=(\d+) size=(\d+)',host);assert hm
  results.append(dict(patches=patches,records=int(m[2]),blocks=int(m[3]),wire_bytes=int(m[4]),modeled_cycles=int(m[5]),pixels=int(hm[1]),checks=int(hm[2]),host_size=int(hm[3]),transactions_sha256=sha(d/'transactions.txt'),records_sha256=sha(d/'records.hex')))
  print(m[0],hm[0],flush=True)
 result=dict(passed=True,cases=results,arm_old_bytes=arm[0],arm_new_bytes=arm[1],sources=sources,runner_sha256=sha(Path(__file__)),generated_bench_sha256=sha(a.out/'wire181_tb.sv'),hardware=False,full_arm_link=False,fit=False,
  scope='Deterministic sealed query + PSRAM fixture; actual selected180 fill/SPI and candidate exporter; exact records then actual C poll/prepare replay. No collector/PPU/SNES integration or physical FPS.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
