# SPDX-License-Identifier: MIT
"""Replay actual MCU RUN command bytes into exact135 RTL, reusing loaded memory."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_functional import VHDL

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence135','host','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence135;o=a.out;assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/command135-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir()
 for n,h in pins.items():
  if n.startswith('fit03/') and Path(n).suffix in ['.sv','.v','.vhd','.qsf']:
   assert sha(e/n)==h
   d=o/n.removeprefix('fit03/');d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d)
 trace=a.host/'run-commands136.txt';shutil.copy2(trace,o/trace.name)
 frames=[[int(x,16) for x in line.split()] for line in trace.read_text().splitlines()]
 assert len(frames)==22 and [x[0] for x in frames]==[0x63,0x65]+[0x70]*16+[0x64,0x65,0x70,0x70]
 s=(ROOT/'tests/nes-functional/board134_tb.sv').read_text().replace('module board134_tb;','module run136_tb;')
 start=s.index("  command(8'h63,81920,0);");end=s.index('\n initial begin #10000000;',start)
 s=s[:start]+'''  begin
   integer f,n;reg [7:0] b[0:7],r[0:7];reg [31:0] first,last,stopped,value;
   f=$fopen("run-commands136.txt","r");ck(f!=0,"MCU trace open");first=0;last=0;stopped=0;
   for(integer frame=0;frame<22;frame++)begin
    n=$fscanf(f,"%h %h %h %h %h %h %h %h",b[0],b[1],b[2],b[3],b[4],b[5],b[6],b[7]);ck(n==8,"complete MCU frame");
    if(b[0]==8'h70 && frame<18)#1000000;
    // The actual MCU transfer waits2us for each half-bit and after each byte.
    SPI_SS=0;#2000;
    for(integer i=0;i<8;i++)begin
     for(integer bitn=7;bitn>=0;bitn--)begin
      SPI_MOSI=b[i][bitn];#2000;SPI_SCK=1;#2000;r[i][bitn]=SPI_MISO;SPI_SCK=0;
     end
     #2000;
    end
    #2000;SPI_SS=1;#2000;
    if(b[0]==8'h65)begin
     ck(r[1]==8'h59 && r[3]==0 && r[7]==0,"loader59 reply");
     ck(r[2]==(frame==1?8'h86:8'h02),"START/STOP status");
     ck({r[4],r[5],r[6]}==24'd81920,"START/STOP retained image count");
    end
    if(b[0]==8'h70)begin
     value={r[4],r[5],r[6],r[7]};ck(r[1]==8'hd4&&r[3]==0,"observerD4 clean reply");
     ck(r[2]==(frame<18?0:1),"observer reset state");
     if(frame==2)begin first=value;ck(first>0,"first CPU progress");end
     if(frame>=2&&frame<18)begin ck(value>last,"CPU progress across bounded reads");last=value;end
     if(frame==20)begin stopped=value;ck(stopped>=last,"STOP final count");end
     if(frame==21)ck(value==stopped,"STOP count retained");
    end
    ck(!dut.core.out_spi_fault,"MCU command accepted");
   end
   $fclose(f);ck(ram.writes==0,"no repeated full memory load");
   $display("PASS136 MCU22frames RUN16reads first=%0d last=%0d stopped=%0d phase_ps=%0d",first,last,stopped,phase);
  end
  $finish;
 end
'''+s[end:];s=s.replace('#10000000;','#40000000;')
 (o/'run136_tb.sv').write_text(s,encoding='utf8',newline='\n')
 qsf=(o/'board.qsf').read_text();names=re.findall(r'-name (?:VHDL_FILE|VERILOG_FILE|SYSTEMVERILOG_FILE) (.+)',qsf)
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 sv=[n for n in names if n not in VHDL and n!='nes_clock_pll123.v']
 run('vlog',['-sv','-mfcu',*sv,'rom_boot_model.sv','run133_pll_model.sv','run136_tb.sv'],'compile')
 results=[]
 for phase in [0,3500]:
  log=run('vsim',['-c','run136_tb',f'+PHASE_PS={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],'run-'+str(phase))
  assert 'PASS136 MCU22frames RUN16reads' in log and '** Fatal:' not in log
  results += [x for x in log.splitlines() if 'PASS136' in x]
 (o/'result.json').write_text(json.dumps(dict(passed=True,trace_sha256=sha(trace),results=results,seeded_load_verified=True,pll_model=True,physical=False),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-test136.py');print('\n'.join(results))
if __name__=='__main__':main()
