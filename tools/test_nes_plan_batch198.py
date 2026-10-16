# SPDX-License-Identifier: MIT
"""Batched SPI mode0 ->198 two-bank RAM decoder ->192 READ16 ->193 aperture, with drain service.
Same archived actual186 C pixels; synthetic source, not a scrolling workload.
No production epoch/controller or actual SNES CPU connected in this test.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from nes_clip178 import replace
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02';ref=ROOT.parent/'probes/nes-plan191/test03';pins={};names=[]
 def copy(f):
  shutil.copyfile(f,a.out/f.name);pins[f.relative_to(ROOT.parent).as_posix()]=sha(f)
 for n in ('nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv'):
  copy(board/n);names.append(n)
 for n in ('nes_tile191.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_bulk_aperture188.sv','nes_tile_bulk193.sv','nes_plan_batch198.sv','nes_plan_spi198.sv'):
  copy(ROOT/'src/nes/rtl'/n);names.append(n)
 for n in ('source_tile192_tb.sv','tile_bulk193_consumer.svh','plan196_host.c','plan198_driver.svh','spi198_bus.svh'):
  copy(ROOT/'tests/nes-functional'/n)
 for n in ('nes_plan191.h','nes_plan_wire196.h'):copy(ROOT/'src/nes/firmware'/n)
 for n in ('nes_native_video165.h','nes_native165.h','nes_trace166.h'):
  copy(ROOT.parent/'probes/nes-paired186/arm01/src'/n)
 for scene in range(8):
  for ext in ('mem','rtl','expected','plans'):copy(ref/f'scene{scene}.{ext}')
 s=(a.out/'source_tile192_tb.sv').read_text()
 s=replace(s,'module source_tile192_tb;','module plan_spi198_tb;\n parameter integer EXTERNAL=1;')
 s=replace(s,'wire out_ready=cycle%5!=0;', 'wire out_ready;\n `include "plan198_driver.svh"')
 s=replace(s,'#(.USE_CACHE(USE_CACHE))','#(.USE_CACHE(USE_CACHE),.EXTERNAL_PLAN(EXTERNAL))')
 for n,v in [('valid','pv'),('ready','pr'),('kind','kind'),('generation','gen'),('slot','slot'),('tag','tag'),('rows','rows'),('mask','mask'),('alt_mask','am'),('alt_tags','ats')]:
  s=replace(s,f'.plan_{n}({v})',f'.plan_{n}({v}196)')
 s=replace(s,'reg [7:0] memory[0:159],expected[0:32767];','reg [7:0] memory[0:159],expected[0:32767];\n `include "tile_bulk193_consumer.svh"')
 # Original CPU/source pin model and exact byte comparison stay in place.
 s=replace(s,'||ok!=kind||os!=slot||og!=gen||length!=(kind==1?32:16)','||og!=gen')
 start=s.index(' integer f,n,j,before_reads;');end=s.index(' initial begin #500000000;',start)
 s=s[:start]+''' integer f,n,j,before_reads;reg [1023:0] filename;
 initial begin
  $sformat(filename,"scene%0d.mem",SCENE);$readmemh(filename,memory,0,159);
  $sformat(filename,"scene%0d.expected",SCENE);$readmemh(filename,expected);
  repeat(5)tick();reset=0;wait(drained);tick();
  while($fscanf(wf,"%h",wl)==1)send_batch198();
  finish_bulk();
  if(checked!=(MODE==1?8192:SCENE==0?144:SCENE==1?160:SCENE<5?224:288)||!core_reads)$fatal(1,"missing output");
  $display("PASS BATCH198 plans_bytes=%0d batches=%0d spi_calls=%0d drains=%0d cycles=%0d",checked,submitted197,spi_calls197,drains197,cycle);$finish;
 end
'''+s[end:]
 (a.out/'plan_spi198_tb.sv').write_text(s,encoding='utf8',newline='\n')
 s=(a.out/'tile_bulk193_consumer.svh').read_text()
 s=replace(s,'reg host_clk=0;always #5.952 host_clk=!host_clk;','')
 s=replace(s,'wire [11:0] chunk_length;wire [31:0] chunk_token;wire ck;wire [9:0] cs;wire [15:0] cg,sg;','wire [15:0] sg;')
 s=replace(s,'chunk_ready,bulk_fault,consume_error,end_sealed;','consume_error;')
 s=replace(s,'reg ev=0,consume=0;wire er,','reg consume=0;wire ev=ev196;wire er;assign er196=er;wire ')
 s=replace(s,'while(!er)tick();@(negedge clk);ev=1;tick();@(negedge clk);ev=0;','')
 s=replace(s,'while(end_count==0||chunk_ready||bus_bytes!=checked)host_tick();','while(end_count==0||chunk_ready||bus_bytes!=checked)poll197();status197();if(!rx197[3][1])$fatal(1,"END not latched");')
 s=replace(s,'if(MODE==1)begin wait(bridge.aperture.sealed==3);repeat(200)host_tick();end','')
 s=replace(s,'wait(chunk_ready);@(negedge host_clk);','wait(chunk_ready&&allow_consume197);@(negedge host_clk);')
 s=replace(s,'consume=0;chunks++;expected_token++;','consume=0;chunks++;expected_token++;allow_consume197=0;')
 s=replace(s,'if(end_count!=1||!wrong_checks||(MODE==1&&(!full_wait||!source_wait)))','if(end_count!=1||!wrong_checks)')
 (a.out/'tile_bulk193_consumer.svh').write_text(s,encoding='utf8',newline='\n')
 env=os.environ.copy()
 def run(exe,args,label):
  env['PATH']=str(exe.parent)+os.pathsep+os.environ.get('PATH','')
  with (a.out/(label+'.log')).open('wb') as log:
   r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
  return text
 gcc=a.questa_bin.parent/'gcc-7.4.0-mingw64vc16/bin/gcc.exe'
 run(gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','plan196_host.c','-o','host.exe'],'gcc')
 host=run(a.out/'host.exe',[ref],'host');assert 'plans=97 bytes=1580 boundaries=268' in host
 import binascii
 lines=(a.out/'scene0.wire').read_text().splitlines();v=[int(x,16) for x in lines[1].split()];b=bytearray(v[1:-1]);pressure=[]
 for slot in range(1,513):
  b[4:6]=slot.to_bytes(2,'little');c=binascii.crc_hqx(b,65535)
  pressure.append(f'{len(b):02x} '+b.hex(' ')+f' {c:04x}')
 (a.out/'pressure.wire').write_text('\n'.join(pressure+[lines[-1]])+'\n')
 def crc8(data):
  c=0
  for b in data:
   c^=b
   for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
  return c
 for wire in list(a.out.glob('scene*.wire'))+[a.out/'pressure.wire']:
  plans=[bytes([int(v,16) for v in line.split()][1:-1]) for line in wire.read_text().splitlines()];frames=[]
  at=0
  while at<len(plans):
   group=[];size=0
   while at<len(plans) and len(group)<15 and size+len(plans[at])<=240:
    group.append(plans[at]);size+=len(plans[at]);at+=1
   payload=b''.join(group);n=len(payload);frame=bytes([0xe9,n&255,n>>8,len(group)])+payload+binascii.crc_hqx(payload,65535).to_bytes(2,'big');frame+=bytes([crc8(frame),0xa5])
   frames.append(f'{len(frame):03x} '+frame.hex(' '))
  wire.with_suffix('.batch').write_text('\n'.join(frames)+'\n')
 run(a.questa_bin/'vlib.exe',['work'],'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*names,'plan_spi198_tb.sv'],'vlog')
 cases=[]
 for scene,mode,slow in [(i,0,False) for i in range(8)]+[(0,1,False),(0,1,True)]:
  external=1
  label=f'scene{scene}-mode{mode}-slow{int(slow)}'
  timing=['-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000'] if slow else []
  t=run(a.questa_bin/'vsim.exe',['-c','work.plan_spi198_tb',f'-gSCENE={scene}',f'-gEXTERNAL={external}',f'-gMODE={mode}',*timing,'-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  m=re.search(r'PASS BULK193 scene=(\d+) mode=(\d+) bytes=(\d+) chunks=(\d+) fullwait=(\d+) sourcewait=(\d+) wrong=(\d+)',t);assert m
  q=re.search(r'PASS BATCH198 plans_bytes=(\d+) batches=(\d+) spi_calls=(\d+) drains=(\d+) cycles=(\d+)',t);assert q
  cases.append(dict(scene=scene,mode=mode,spi_mhz=2.625 if slow else 8,bytes=int(m[3]),chunks=int(m[4]),source_wait=int(m[6]),batches=int(q[2]),spi_calls=int(q[3]),cycles=int(q[5])))
 assert sum(c['bytes'] for c in cases[:8])==1840
 result=dict(passed=True,scope=__doc__,cases=cases,host=host.strip(),pressure_bytes=cases[-1]['bytes'],source_pins=pins,
  script_sha256=sha(Path(__file__)),generated_tb_sha256=sha(a.out/'plan_spi198_tb.sv'),
  generated_consumer_sha256=sha(a.out/'tile_bulk193_consumer.svh'),compiler_sha256=sha(gcc),
  actual_scroll_measured=False,new_fit=False,new_firmware=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(passed=True,cases=cases,pressure_bytes=cases[-1]['bytes'])))
if __name__=='__main__':main()
