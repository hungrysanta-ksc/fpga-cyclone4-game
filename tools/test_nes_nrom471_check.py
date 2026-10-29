# SPDX-License-Identifier: MIT
import argparse,shutil,subprocess,os,json
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
shutil.copyfile(a.board/'nes_rom_spi.sv',d/'nes_rom_spi.sv');s=(ROOT/'tests/nes-functional/spi_readback_control_tb.sv').read_text().replace('[16:0]','[18:0]').replace("8'h54","8'h78").replace("8'h74","8'h78").replace("8'h59","8'h78").replace("command(8'h60,1,0)","command(8'h60,1,2)").replace("command(8'h60,0,0)","command(8'h60,0,2)");(d/'bench.sv').write_text(s)
bin=Path('C:/altera_standard/25.1std/questa_fse/win64')
for tool,args in [('vlib',['work']),('vlog',['-sv','nes_rom_spi.sv','bench.sv']),('vsim',['-c','work.spi_readback_control_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
 with(d/(tool+'.log')).open('wb') as f:r=subprocess.run([str(bin/(tool+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(d/(tool+'.log')).read_text(errors='replace')[-2500:]
s=(d/'vsim.log').read_text(errors='replace');assert 'PASS SPI CHECK CONTROL' in s and 'Errors: 0' in s;r={'passed':True,'RTL':sha(d/'nes_rom_spi.sv'),'test':sha(d/'bench.sv'),'scope':'actual serialized CHECK/READ/ACK/START/STOP and negative cases; 1clk response-stage candidate, no hardware'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
