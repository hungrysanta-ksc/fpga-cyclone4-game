# SPDX-License-Identifier: MIT
"""Existing147 decoder at149 hardware master rising-edge sample timing.
No unchanged CPU frames or bulk PSRAM writes are rerun.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
    names=['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','nes_rom_spi.sv','nes_rom_service.sv']
    meta=json.loads((a.prepared/'result.json').read_bytes());a.out.mkdir()
    for n in names:
        assert sha(a.prepared/n)==meta['sources'][n],n
        shutil.copy2(a.prepared/n,a.out/n)
    shutil.copy2(ROOT/'tests/nes-functional/game147_path_tb.sv',a.out/'game147_path_tb.sv')
    if meta.get('prefetch'):
        tb=a.out/'game147_path_tb.sv';s=tb.read_text();needle='.cpu_data(cache_cpu_data)'
        assert s.count(needle)==1
        tb.write_text(s.replace(needle,".ppu_prefetch_valid(1'b0),.ppu_prefetch_address(22'd0),"+needle),encoding='utf8',newline='\n')
    tb=a.out/'game147_path_tb.sv';s=tb.read_text()
    before='SPI_SS=0;#120;'
    assert s.count(before)==1
    s=s.replace(before,'SPI_SS=0;#2000;')
    before='for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;end'
    assert s.count(before)==1
    s=s.replace(before,'for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#190.476;SPI_SCK=1;rx[j/8][7-j%8]=spi_miso;#190.476;SPI_SCK=0;end')
    assert s.count('#120;SPI_SS=1;#240;')==1
    s=s.replace('#120;SPI_SS=1;#240;','#2000;SPI_SS=1;#2000;')
    tb.write_text(s,encoding='utf8',newline='\n')
    def run(exe,args,log,negative=False):
        with (a.out/log).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        s=(a.out/log).read_text(errors='replace')
        if negative:assert 'PATH147 check=3 ' in s and 'PASS PATH147' not in s,(r.returncode,s[-2000:])
        else:assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2500:])
        return s
    run('vlib',['work'],'vlib.log')
    run('vlog',['-sv','-mfcu',*names,'game147_path_tb.sv'],'vlog.log')
    args=['-c','work.game147_path_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    s=run('vsim',args,'simulation.log');assert 'PASS PATH147' in s
    result=dict(passed=True,summary=re.search(r'PASS PATH147[^\r\n]+',s)[0],
                sources={n:sha(a.out/n) for n in names+['game147_path_tb.sv']},
                master_hz=2625000,half_period_ns=190.476,sample='at master rising edge; not delayed until high phase end',
                scope='Seeded count boundaries;8 actual write cycles,6 CHECK reads,19-bit SPI status/ACK rollover/finish/START,6 negative lifecycle cases,7 full-bank cache reads. Not a full384KiB write/compare or MCU integration test.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['summary'],flush=True)
if __name__=='__main__':main()
