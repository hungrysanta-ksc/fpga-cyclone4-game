# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_h1_spi import fixed_boundary,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','questa-bin','wave'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus']
 for n in files:shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
 (out/'nes_h1_board_bus.sv').write_text(fixed_boundary())
 for n in ('h1-pattern.hex','h1-program.hex'):shutil.copy2(a.build/n,out/n)
 shutil.copy2(a.wave,out/'waveform.txt');shutil.copy2(ROOT/'tests/nes-functional/h1_spi_wave_tb.sv',out/'h1_spi_wave_tb.sv')
 for label,tool,args in [('vlib','vlib',['work']),('compile','vlog',['-sv',*[n+'.sv' for n in files],'h1_spi_wave_tb.sv']),('wave','vsim',['-c','h1_spi_wave_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert cp.returncode==0,label
 log=(out/'wave.log').read_text();assert 'PASS C SPI WAVE samples=224 verified=88 rows=942' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 (out/'result.json').write_text(json.dumps({'candidate':'NES-H1-RUNTIME-038','passed':True,'samples':224,'verified_bits':88,'rows':942,'waveform_sha256':sha(out/'waveform.txt'),'boundary_sha256':sha(out/'nes_h1_board_bus.sv')},indent=2))
 print('PASS038 actual C waveform replay against unchanged036 RTL')
if __name__=='__main__':main()
