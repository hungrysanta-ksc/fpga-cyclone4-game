# SPDX-License-Identifier: MIT
"""Actual CPU-driven rendering transitions; ideal memory, not SMB3 or hardware."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,sha

def program():
 code=bytearray();labels={};fix=[]
 def emit(*v):code.extend(v)
 def sta(a):emit(0x8d,a&255,a>>8)
 def lda(v):emit(0xa9,v)
 def label(s):labels[s]=len(code)
 def branch(op,s):emit(op,0);fix.append((len(code)-1,s))
 emit(0x78,0xd8,0xa2,255,0x9a);lda(0)
 for a in [0x2000,0x2001,0x4015]:sta(a)
 lda(0x40);sta(0x4017)
 emit(0xa2,0);label('fill');emit(0xbd,0,0xe0,0x9d,0,2,0xe8);branch(0xd0,'fill')
 lda(0);sta(0x2003);lda(2);sta(0x4014)
 lda(0x3f);sta(0x2006);lda(0);sta(0x2006)
 emit(0xa2,32);label('palette');emit(0x8a);sta(0x2007);emit(0xca);branch(0xd0,'palette')
 lda(0);sta(0x2005);sta(0x2005)
 # CPU toggles PPUMASK, writes OAMADDR/CPU data, reads OAMDATA and restores
 # rendering. X/Y delays deliberately cross PPU evaluation/row boundaries.
 emit(0xa2,0);label('outer');lda(0);sta(0x2001)
 emit(0x8a,0x29,0xf8,0x09,0x08);sta(0x2003)
 emit(0x8a);sta(0x2004);emit(0xad,4,0x20);sta(0x10)
 lda(0x1e);sta(0x2001);emit(0xa0,48);label('delay');emit(0x88);branch(0xd0,'delay')
 emit(0xe8);branch(0xd0,'outer')
 lda(255);sta(0x21);label('end');emit(0x4c,(0x8000+labels['end'])&255,(0x8000+labels['end'])>>8)
 for at,s in fix:
  distance=labels[s]-at-1;assert -128<=distance<=127;code[at]=distance&255
 prg=bytearray([0xea])*32768;prg[:len(code)]=code
 for i in range(256):prg[0x6000+i]=((i//4)*3 if i%4==0 else (i*17+3))&255
 prg[0x1000]=0x40
 for a in [0x7ffa,0x7ffc,0x7ffe]:prg[a:a+2]=(0x8000 if a==0x7ffc else 0x9000).to_bytes(2,'little')
 return prg

TB='''// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nes_tb;
reg clk=0;always #23.280423 clk=~clk;
reg reset_nes=1,cold_reset=1;
reg [7:0] cpumem_din=0,ppumem_din=0;
reg [4:0] joypad1_data=0,joypad2_data=0;
__PORTS__
nes_probe dut(.*);
reg [7:0] prg[0:32767],ram[0:2047];
integer tick=0,i,fd,fc,fo,render_ticks=0,copies=0,cpuwrites=0,maskwrites=0,halves=0,done=0;
reg started=0;reg [63:0] half_inputs;
wire [63:0] read_inputs={23'd0,dut.core.ppu.spriteeval.oam_read_addr,
 dut.core.ppu.spriteeval.oam_row_last,dut.core.ppu.spriteeval.oam_addr_ex,
 dut.core.ppu.spriteeval.oam_addr,dut.core.ppu.spriteeval.Savestate_OAMAddr,
 dut.core.ppu.spriteeval.ce,dut.core.ppu.spriteeval.Savestate_OAMRdEn,
 dut.core.ppu.spriteeval.oam_copy_write,dut.core.ppu.spriteeval.oam_cpu_write,
 dut.core.ppu.spriteeval.Savestate_OAMWrEn,1'b0};
always @(negedge clk)half_inputs=read_inputs;
always @(posedge clk)begin
 tick=tick+1;
 if(cpumem_read)begin
  if(cpumem_addr<262144)cpumem_din<=prg[cpumem_addr[14:0]];
  else if(cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)cpumem_din<=ram[cpumem_addr[10:0]];
  else cpumem_din<=0;
 end
 if(ppumem_read)ppumem_din<=ppumem_addr[7:0]^ppumem_addr[15:8]^8'h5a;
 if(cpumem_write && cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)ram[cpumem_addr[10:0]]<=cpumem_dout;
 if(!reset_nes && dut.core.cart_ce && dut.core.cpu_addr==16'h8000 && dut.core.cpu_rnw && dut.core.internal_data_bus==8'h78)started=1;
 if(started)begin
  if(read_inputs!==half_inputs)$fatal(1,"half-cycle input changed");halves++;
  if(dut.core.ppu.spriteeval.ce)begin
   if(dut.core.ppu.spriteeval.rendering)render_ticks++;
   if(dut.core.ppu.spriteeval.oam_copy_write)copies++;
   if(dut.core.ppu.spriteeval.oam_cpu_write)cpuwrites++;
   $fwrite(fd,"%0d %0d %0d %h %h %h %h %h %h %h %h\\n",tick,scanline,cycle,color,emphasis,
    dut.core.ppu.spriteeval.oam_bus,dut.core.ppu.spriteeval.oam_bus_ex,
    dut.core.ppu.spriteeval.sprite0,dut.core.ppu.spriteeval.overflow,
    dut.core.ppu.spriteeval.in_range,dut.core.ppu.spriteeval.oam_data);
  end
  if(dut.core.cart_ce)begin
   $fwrite(fc,"%0d %h %b %h\\n",tick,dut.core.cpu_addr,dut.core.cpu_rnw,dut.core.internal_data_bus);
   if(!dut.core.cpu_rnw && dut.core.cpu_addr==16'h2001)maskwrites++;
   if(dut.core.prg_write && dut.core.prg_addr==16'h21 && dut.core.prg_din==255)done=1;
  end
 end
 if(done)begin
  if(render_ticks<100000 || copies<100 || cpuwrites<500 || maskwrites<512)$fatal(1,"coverage render=%0d copy=%0d cpu=%0d mask=%0d",render_ticks,copies,cpuwrites,maskwrites);
  for(i=0;i<256;i++)$fwrite(fo,"%0d %h\\n",i,dut.core.ppu.spriteeval.oam_read(i));
  $fclose(fd);$fclose(fc);$fclose(fo);
  $display("PASS OAMRENDER181 half=%0d render=%0d copy=%0d cpu=%0d mask=%0d",halves,render_ticks,copies,cpuwrites,maskwrites);$finish;
 end
end
initial begin
 $readmemh("prg.hex",prg);for(i=0;i<2048;i++)ram[i]=0;
 fd=$fopen("ppu.tsv","w");fc=$fopen("cpu.tsv","w");fo=$fopen("oam.tsv","w");
 #20000;reset_nes=0;cold_reset=0;
 #100000000;$fatal(1,"render timeout");
end
endmodule
'''

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--altera-mf',type=Path);p.add_argument('--reference',type=Path)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 m=json.loads((a.prepared/'preparation.json').read_bytes());prg=program();(a.out/'prg.bin').write_bytes(prg)
 header=(a.prepared/'nes_probe.sv').read_text().split('module nes_probe(',1)[1].split(');',1)[0]
 ports=['wire [7:0] native_oam_address=0;wire chr_32k=0;'];direction=signed=width=''
 for part in header.split(','):
  part=part.strip();decl=re.fullmatch(r'(input|output)\s+wire\s+(signed\s+)?(\[[^\]]+\]\s*)?(\w+)',part)
  if decl:direction,signed,width,name=decl.groups();signed=signed or '';width=width or ''
  else:assert re.fullmatch(r'\w+',part),part;name=part
  if direction=='output':ports.append(f'wire {signed}{width}{name};')
 tb=TB.replace('__PORTS__','\n'.join(ports));results={}
 for label,folder in [('baseline',a.baseline),('candidate',a.prepared)]:
  if label=='baseline' and a.reference:
   ref=json.loads((a.reference/'result.json').read_bytes());assert ref['passed'] and ref['rom_sha256']==sha(a.out/'prg.bin')
   assert (a.reference/'baseline/nes_tb.sv').read_text()==tb
   for n in VHDL+SV+['cart_nrom.sv','nes_probe.sv']:assert sha(a.reference/'baseline'/n)==m['baseline_oamread_sources'][n]
   for n,h in ref['results']['baseline']['files'].items():assert sha(a.reference/'baseline'/n)==h
   results[label]=ref['results']['baseline'];continue
  d=a.out/label;d.mkdir()
  for n in VHDL+SV+['cart_nrom.sv','nes_probe.sv']:
   expected=m['sources'][n] if label=='candidate' else m['baseline_oamread_sources'][n]
   assert sha(folder/n)==expected,n;dest=d/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/n,dest)
  (d/'prg.hex').write_text(''.join(f'{b:02x}\n' for b in prg))
  (d/'nes_tb.sv').write_text(tb,encoding='utf8',newline='\n')
  def run(exe,args,n):
   with (d/(n+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=240)
   s=(d/(n+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
  run('vlib',['work'],'vlib')
  for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
  extra=[]
  if a.altera_mf:shutil.copy2(a.altera_mf,d/'altera_mf.v');extra=['altera_mf.v']
  run('vlog',['-sv','-mfcu',*extra,*SV,'cart_nrom.sv','nes_probe.sv','nes_tb.sv'],'compile')
  log=run('vsim',['-c','work.nes_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
  match=re.search(r'PASS OAMRENDER181 half=(\d+) render=(\d+) copy=(\d+) cpu=(\d+) mask=(\d+)',log);assert match
  results[label]=dict(counts=list(map(int,match.groups())),files={n:sha(d/n) for n in ['cpu.tsv','ppu.tsv','oam.tsv']})
 assert results['baseline']==results['candidate'],results
 result=dict(passed=True,results=results,rom_sha256=sha(a.out/'prg.bin'),source_sha256=sha(a.prepared/'rtl/ppu.sv'),
  runner_sha256=sha(Path(__file__)),scope=__doc__,physical=False,
  baseline_reused_sha256=sha(a.reference/'result.json') if a.reference else None,
  altera_mf_sha256=sha(a.altera_mf) if a.altera_mf else None)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
