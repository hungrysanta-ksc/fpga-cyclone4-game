"""Run the extracted C43 RTC register and SPI protocol regressions."""
import argparse,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--iverilog',default='iverilog');p.add_argument('--vvp',default='vvp');a=p.parse_args()
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
for name,files in [('rtc',['gbc_mbc3_rtc.sv']),('rtc_spi',['gbc_mbc3_rtc.sv','gbc_spi.sv','gbc_mcu_cmd.sv'])]:
 image=out/(name+'.vvp')
 subprocess.run([a.iverilog,'-g2012','-s','tb','-o',str(image),str(ROOT/'tests'/(name+'_tb.sv'))]+[str(ROOT/'src/fpga'/f) for f in files],check=True)
 with (out/(name+'.log')).open('w') as log:subprocess.run([a.vvp,str(image)],check=True,stdout=log,stderr=subprocess.STDOUT)
 print('PASS',name)
