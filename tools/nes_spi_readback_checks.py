# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil
from nes_spi_readback import ROOT,materialize
from nes_spi_boot import put,sha,run
from nes_rom_geometry import replace
from nes_functional import VHDL,SV
from nes_spi_live import compare_case


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--mode',choices=['fit','unit','wave','live'],required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path)
 p.add_argument('--questa-bin',type=Path);p.add_argument('--quartus-bin',type=Path)
 p.add_argument('--waveform',type=Path)
 a=p.parse_args();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 for n in ['nes_spi_readback_checks.py','nes_spi_readback.py','nes_rom_readback.py']:
  shutil.copy2(ROOT/'tools'/n,out/n)
 r=dict(candidate='NES-SPI-READBACK-059',mode=a.mode,passed=False,hardware_image=False)
 if a.mode in ['fit','live']:
  previous=json.loads((a.baseline/'result.json').read_text());assert previous['candidate']=='NES-ROM-GEOMETRY-057' and previous['passed']
  for n,h in previous['sources'].items():
   assert sha(a.baseline/n)==h,n
   (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,out/n)
  names=list(previous['sources']);materialize(out)
  r['baseline_result_sha256']=sha(a.baseline/'result.json')
  if a.mode=='live':
   s=(out/'ncr1_live_tb.sv').read_text()
   s=replace(s,'reg queue_clk=0,host_clk=0,boot_reset=1;', '''reg queue_osc=0,host_osc=0,boot_reset=1;
 wire run_enable;
 wire queue_clk=queue_osc && (boot_reset || run_enable);
 wire host_clk=host_osc && (boot_reset || run_enable);''')
   s=replace(s,'wire run_enable;wire reset_request=','wire reset_request=')
   assert s.index('wire run_enable;') < s.index('wire queue_clk=')
   s=replace(s,'always #23.280423 queue_clk=~queue_clk;','always #23.280423 queue_osc=~queue_osc;')
   s=replace(s,'forever #5.952381 host_clk=~host_clk;','forever #5.952381 host_osc=~host_osc;')
   s=s.replace("8'h54","8'h59")
   s=replace(s,"command(8'h63,total,0);status(total,6);",'''command(8'h66,0,0);
  for(integer a=0;a<total;a++)begin
   command(8'h67,a,0);command(8'h6a,24'hfedcba,0);
   if(rx[1]!=8'h59 || rx[2]!=8'h62 || rx[3] !== (a<65536?prg[a]:chr[a-65536]) ||
      {rx[4],rx[5],rx[6]}!=a || rx[7]!=0)$fatal(1,"CHECK SPI mismatch at%0d",a);
   command(8'h68,a,a<65536?prg[a]:chr[a-65536]);
   if(a%8192==8191)$display("CHECK PROGRESS bytes=%0d",a+1);
  end
  command(8'h69,total,0);status(total,8'h82);
  command(8'h63,total,0);status(total,8'h86);''')
   s=s.replace('#1000000000;if(!run_enable)','#6000000000.0;if(!run_enable)')
   put(out/'ncr1_live_tb.sv',s)
 else:
  assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
  materialize(out)
  if a.mode=='wave':
   assert a.waveform
   shutil.copy2(a.waveform,out/'waveform.txt')
   for n in ['spi_readback_pin_tb.sv','rom_boot_model.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,out/n)
   names=['nes_rom_spi.sv','nes_rom_physical.sv','nes_rom_loader.sv','nes_rom_boot.sv','nes_spi_boot.sv','rom_boot_model.sv','spi_readback_pin_tb.sv']
   r['waveform_sha256']=sha(out/'waveform.txt')
  else:
   shutil.copy2(ROOT/'tests/nes-functional/spi_readback_control_tb.sv',out/'spi_readback_control_tb.sv')
   names=['nes_rom_spi.sv','spi_readback_control_tb.sv']
 r['sources']={n:sha(out/n) for n in names}
 r['driver_sha256']=sha(Path(__file__));r['generator_sha256']=sha(ROOT/'tools/nes_spi_readback.py')
 def save():put(out/'result.json',json.dumps(r,indent=2)+'\n')
 save()
 if a.mode=='fit':
  for phase in ['map','fit']:run([a.quartus_bin/('quartus_'+phase+'.exe'),'live'],out,phase,3600)
  r['fit_summary']=(out/'output_files/live.fit.summary').read_text(errors='replace');print(r['fit_summary'])
 elif a.mode=='live':
  assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
  def sim(tool,args,folder,label,timeout=7200):
   log=run([a.questa_bin/(tool+'.exe'),*args],folder,label,timeout)
   assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log),str(folder/(label+'.log'))
   return log
  sim('vlib',['work'],out,'vlib')
  for i,n in enumerate(VHDL):sim('vcom',['-2008',n],out,f'vcom-{i:02}')
  extra=[n for n in names if n.endswith(('.sv','.v')) and n not in SV and n!='ncr1_live_tb.sv']
  sim('vlog',['-sv','-mfcu',*SV,*extra,'ncr1_live_tb.sv'],out,'vlog')
  r['cases']=[]
  for case in ['banks32','fine_x']:
   c=out/case;c.mkdir()
   for n in ['prg.hex','chr.hex','manifest.json']:shutil.copy2(a.baseline/case/n,c/n)
   put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
   print('RUN CHECK CORE '+case,flush=True)
   sim('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb','+CHR32='+str(int(case=='banks32')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation')
   verified=compare_case(out,a.baseline,case)
   verified['tick_offsets_vs057']=verified.pop('tick_offsets_vs053')
   r['cases'].append(verified);save();print('PASS CHECK CORE '+case,flush=True)
 else:
  top='spi_readback_pin_tb' if a.mode=='wave' else 'spi_readback_control_tb'
  simargs=['-c',top,*(['+WAVE=1'] if a.mode=='wave' else []),'-do','onerror {quit -code 1}; run -all; quit -f']
  for tool,args in [('vlib',['work']),('vlog',['-sv',*names]),('vsim',simargs)]:
   log=run([a.questa_bin/(tool+'.exe'),*args],out,tool,1200)
   assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log),str(out/(tool+'.log'))
  marker=re.search(r'PASS SPI CHECK (?:CONTROL|GPIO) [^\r\n]+',log);assert marker
  r['marker']=marker[0];print(marker[0])
 r['passed']=True;save()


if __name__=='__main__':main()
