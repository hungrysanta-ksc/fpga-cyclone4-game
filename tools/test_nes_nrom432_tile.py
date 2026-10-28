# SPDX-License-Identifier: MIT
"""Run actual 227 tile source against 430 plan and own ROM with core arbitration."""
import argparse,json,os,re,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--planner',required=True,type=Path);p.add_argument('--snes',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
r=json.loads((a.planner/'result.json').read_text());assert r['passed'] and r['rom_sha256']==sha(a.rom) and r['plans_sha256']==sha(a.planner/'plans.bin')
names=['nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv','nes_tile191.sv','nes_tile205.sv','nes_source_tile192.sv','nes_chr_cache192.sv']
for n in names:shutil.copyfile(a.board/n,d/n)
plans=(a.planner/'plans.bin').read_bytes();assert len(plans)==80;rows=[];expected=bytearray();rom=a.rom.read_bytes();chr=rom[16400:]
for off in range(0,len(plans),40):
 q=struct.unpack('<HHHBB16B8H',plans[off:off+40]);gen,slot,tag,kind,mask=q[:5];rv=q[5:21];alt=q[21:];packed=sum(v<<(3*i) for i,v in enumerate(rv));am=sum((v!=65535)<<i for i,v in enumerate(alt));ats=sum((0 if v==65535 else v)<<(13*i) for i,v in enumerate(alt));rows.append(f'{kind:x} {gen:x} {slot:x} {tag:x} {mask:x} {packed:x} {am:x} {ats:x}')
 for y in range(8):
  lo=tag if alt[y]==65535 else alt[y]
  expected.extend((chr[lo*16+rv[y*2]],chr[tag*16+8+rv[y*2+1]]) if kind!=2 and (mask>>y)&1 else (0,0))
(d/'frame.rtl').write_text('\n'.join(rows)+'\n');(d/'frame.mem').write_text(''.join(f'{x:02x}\n' for x in chr[:160]));(d/'frame.expected').write_text(''.join(f'{x:02x}\n' for x in expected))
s=(ROOT/'tests/nes-functional/source_tile192_tb.sv').read_text();s=s.replace(".frame_generation(16'(100+SCENE))", ".frame_generation(16'd4)")
start=s.index(' integer f,n,j,before_reads;');end=s.index(' initial begin #500000000;',start)
s=s[:start]+''' integer f,n;
 initial begin
  $readmemh("frame.mem",memory,0,159);$readmemh("frame.expected",expected,0,31);
  f=$fopen("frame.rtl","r");if(!f)$fatal(1,"plan missing");
  repeat(5)tick();reset=0;wait(drained);tick();
  while(!$feof(f))begin @(negedge clk);n=$fscanf(f,"%h %h %h %h %h %h %h %h\\n",kind,gen,slot,tag,mask,rows,am,ats);if(n==8)begin submit();complete();end else if(n!=-1&&n!=0)$fatal(1,"plan format");end
  $fclose(f);if(tiles!=2||checked!=32||reads!=16||!core_reads||!stall)$fatal(1,"missing coverage tiles=%0d checked=%0d reads=%0d core=%0d stall=%0d",tiles,checked,reads,core_reads,stall);
  $display("PASS NROM432 tiles=%0d bytes=%0d reads=%0d core=%0d stalls=%0d cycles=%0d",tiles,checked,reads,core_reads,stall,cycle);$finish;
 end
'''+s[end:];(d/'tile_tb.sv').write_text(s)
exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
for name,cmd in [('vlib',['vlib','work']),('vlog',['vlog','-sv',*names,'tile_tb.sv']),('simulation',['vsim','-L','altera_mf_ver','-c','work.source_tile192_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run([str(exe/(cmd[0]+'.exe')),*cmd[1:]],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-4000:]
log=(d/'simulation.log').read_text(errors='replace');assert 'PASS NROM432' in log and 'Errors: 0' in log,log[-4000:]
snes=json.loads((a.snes/'result.json').read_text());assert snes['passed'] and snes['fixture_sha256']==sha(a.rom)
actual=bytes.fromhex((d/'frame.expected').read_text());files=sorted(a.snes.glob('tile-*.bin'));assert len(files)==2 and b''.join(f.read_bytes() for f in files)==actual
result={'passed':True,'rom_sha256':sha(a.rom),'plan_sha256':sha(a.planner/'plans.bin'),'board_source_sha256':sha(a.board/'nes_source_tile192.sv'),'output_sha256':sha(d/'frame.expected'),'snes_tile_files':{f.name:sha(f) for f in files},'scope':'actual 227 source tile RTL, 430 real plan and ROM with physical-reader pin model and scheduled core contention; direct plan submission, not SPI/65816 or whole board'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
