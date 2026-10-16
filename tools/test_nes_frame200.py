# SPDX-License-Identifier: MIT
"""Batched SPI mode0 ->200 two-bank RAM decoder ->192 READ16 ->193 aperture, with drain service.
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
 for n in ('nes_tile191.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_bulk_aperture188.sv','nes_tile_bulk193.sv','nes_plan_batch200.sv','nes_plan_spi200.sv'):
  copy(ROOT/'src/nes/rtl'/n);names.append(n)
 for n in ('source_tile192_tb.sv','tile_bulk193_consumer.svh','plan196_host.c','plan200_driver.svh','spi200_bus.svh'):
  copy(ROOT/'tests/nes-functional'/n)
 for n in ('nes_plan191.h','nes_plan_wire196.h'):copy(ROOT/'src/nes/firmware'/n)
 for n in ('nes_native_video165.h','nes_native165.h','nes_trace166.h'):
  copy(ROOT.parent/'probes/nes-paired186/arm01/src'/n)
 for scene in range(8):
  for ext in ('mem','rtl','expected','plans'):copy(ref/f'scene{scene}.{ext}')
 s=(a.out/'source_tile192_tb.sv').read_text()
 s=replace(s,'module source_tile192_tb;','module plan_spi200_tb;\n parameter integer EXTERNAL=1;')
 s=replace(s,'wire out_ready=cycle%5!=0;', 'wire out_ready;\n `include "plan200_driver.svh"')
 s=replace(s,'#(.USE_CACHE(USE_CACHE))','#(.USE_CACHE(USE_CACHE),.EXTERNAL_PLAN(EXTERNAL))')
 for n,v in [('valid','pv'),('ready','pr'),('kind','kind'),('generation','gen'),('slot','slot'),('tag','tag'),('rows','rows'),('mask','mask'),('alt_mask','am'),('alt_tags','ats')]:
  s=replace(s,f'.plan_{n}({v})',f'.plan_{n}({v}196)')
 s=replace(s,'reg [7:0] memory[0:159],expected[0:32767];','reg [7:0] memory[0:159],expected[0:32767];\n `include "tile_bulk193_consumer.svh"')
 # Original CPU/source pin model and exact byte comparison stay in place.
 s=replace(s,'||ok!=kind||os!=slot||og!=gen||length!=(kind==1?32:16)','||og!=gen')
 start=s.index(' integer f,n,j,before_reads;');end=s.index(' initial begin #500000000;',start)
 s=s[:start]+''' integer f,n,j,before_reads,frame200;reg [1023:0] filename;
 initial begin
  $sformat(filename,"scene%0d.mem",SCENE);$readmemh(filename,memory,0,159);
  $sformat(filename,"scene%0d.expected",SCENE);$readmemh(filename,expected);
  repeat(5)tick();reset=0;wait(drained);tick();
  for(frame200=0;frame200<3;frame200=frame200+1)begin
   gen=16'(65534+frame200);checked=0;bus_bytes=0;chunks=0;end_count=0;
   $sformat(wname,"scene%0d-frame%0d.batch",SCENE,frame200);wf=$fopen(wname,"r");if(!wf)$fatal(1,"frame batch");
   while($fscanf(wf,"%h",wl)==1)send_batch200();$fclose(wf);
   finish_bulk();
   if(checked!=(SCENE==0?144:SCENE<5?224:288)||!core_reads)$fatal(1,"missing output");
   // RTL fixture stands in for MCU final display ACK, explicitly not real PPU here.
   repeat(100)host_tick();retire_frame200();
   if(stop||reset||fault||busy||!drained)$fatal(1,"retire disturbed source");
   $display("PASS FRAME200 frame=%0d gen=%0d bytes=%0d next_token=%0d",frame200,gen,bus_bytes,expected_token);
  end
  $display("PASS MULTI200 bytes=%0d frames=3 cycles=%0d core_reads=%0d",checked*3,cycle,core_reads);$finish;
 end
'''+s[end:]
 s=re.sub(r'\bframe200\b','frame_index200',s)
 s=replace(s,".frame_generation(16'(100+SCENE))",'.frame_generation(gen)')
 (a.out/'plan_spi200_tb.sv').write_text(s,encoding='utf8',newline='\n')
 s=(a.out/'tile_bulk193_consumer.svh').read_text()
 s=replace(s,'reg host_clk=0;always #5.952 host_clk=!host_clk;','')
 s=replace(s,'wire [11:0] chunk_length;wire [31:0] chunk_token;wire ck;wire [9:0] cs;wire [15:0] cg,sg;','')
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
 def shorten(b):
  kind=b[0];rows=int.from_bytes(b[9:15],'little')
  if kind<2 and (b[1] or any((rows>>(i*3))&7!=i//2 for i in range(16))):return b
  if kind>=2:return bytes([0x80|kind])+b[2:4]
  return bytes([0x80|kind])+b[2:8]+(b[8:9] if kind==1 else b'')
 for wire in list(a.out.glob('scene*.wire'))+[a.out/'pressure.wire']:
  plans=[shorten(bytes([int(v,16) for v in line.split()][1:-1])) for line in wire.read_text().splitlines()];frames=[]
  at=0
  while at<len(plans):
   group=[];size=0
   while at<len(plans) and len(group)<15 and size+len(plans[at])<=240:
    group.append(plans[at]);size+=len(plans[at]);at+=1
   payload=b''.join(group);n=len(payload);frame=bytes([0xe9,n&255,n>>8,len(group)])+payload+binascii.crc_hqx(payload,65535).to_bytes(2,'big');frame+=bytes([crc8(frame),0xa5])
   frames.append(f'{len(frame):03x} '+frame.hex(' '))
  wire.with_suffix('.batch').write_text('\n'.join(frames)+'\n')
 # Regenerate each frame with an explicit generation, including wrap.
 for scene in (0,2,7):
  for frame_index in range(3):
   lines=[]
   for line in (a.out/f'scene{scene}.batch').read_text().splitlines():
    b=bytearray(int(x,16) for x in line.split()[1:]);at=4;n=b[1]+256*b[2]
    for _ in range(b[3]):
     if b[at]&128:kind=b[at]&3;size=3 if kind>=2 else 8 if kind==1 else 7;g=at+1
     else:size=16+2*b[at+1].bit_count();g=at+2
     b[g:g+2]=((65534+frame_index)&65535).to_bytes(2,'little');at+=size
    assert at==n+4
    b[n+4:n+6]=binascii.crc_hqx(b[4:n+4],65535).to_bytes(2,'big');b[n+6]=crc8(b[:n+6])
    lines.append(f'{len(b):03x} '+b.hex(' '))
   (a.out/f'scene{scene}-frame{frame_index}.batch').write_text('\n'.join(lines)+'\n')
 run(a.questa_bin/'vlib.exe',['work'],'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*names,'plan_spi200_tb.sv'],'vlog')
 cases=[]
 for scene,mode,slow in [(i,0,True) for i in (0,2,7)]:
  external=1
  label=f'scene{scene}-mode{mode}-slow{int(slow)}'
  timing=['-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000'] if slow else []
  t=run(a.questa_bin/'vsim.exe',['-c','work.plan_spi200_tb',f'-gSCENE={scene}',f'-gEXTERNAL={external}',f'-gMODE={mode}',*timing,'-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  m=re.search(r'PASS BULK193 scene=(\d+) mode=(\d+) bytes=(\d+) chunks=(\d+) fullwait=(\d+) sourcewait=(\d+) wrong=(\d+)',t);assert m
  q=re.search(r'PASS MULTI200 bytes=(\d+) frames=3 cycles=(\d+) core_reads=(\d+)',t);assert q and int(q[3])>0
  assert len(re.findall(r'PASS FRAME200 frame=',t))==3
  cases.append(dict(scene=scene,frames=3,spi_mhz=2.625,bytes=int(q[1]),cycles=int(q[2]),core_reads=int(q[3])))
 assert sum(c['bytes'] for c in cases)==1968
 result=dict(passed=True,scope=__doc__,cases=cases,host=host.strip(),multi_frame_bytes=sum(c['bytes'] for c in cases),source_pins=pins,
  script_sha256=sha(Path(__file__)),generated_tb_sha256=sha(a.out/'plan_spi200_tb.sv'),
  generated_consumer_sha256=sha(a.out/'tile_bulk193_consumer.svh'),compiler_sha256=sha(gcc),
  actual_scroll_measured=False,new_fit=False,new_firmware=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(passed=True,cases=cases,multi_frame_bytes=sum(c['bytes'] for c in cases))))
if __name__=='__main__':main()
