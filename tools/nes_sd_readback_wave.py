# SPDX-License-Identifier: MIT
"""060 actual SD-binding GPIO traces, load and CHECK phases in044+059 RTL."""
from pathlib import Path
import argparse,json,os,re,shutil,sys
from nes_spi_boot import ROOT,RTL,integrated_boundary,h1_materialize,run,sha,put
from nes_spi_readback import materialize
from nes_sd_readback import source

def preflight():
 text=(ROOT/'tests/nes-functional/sd_readback_wave_tb.sv').read_text()
 # Questa resolves procedural task references in declaration order as well.
 for declaration in ['reg nes_clk=','wire spi_miso,','wire [3:0] boot_error,']:
  assert text.index(declaration)<text.index('task automatic prepare;'),declaration

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--host-run',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
 a=p.parse_args();preflight();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 host=a.host_run.resolve();r=json.loads((host/'result.json').read_text());assert r['host_model_pass'] and r['candidate']=='NES-SD-READBACK-060'
 assert (host/'nes_h1_stm32.c').read_text()==source()
 for n,h in r['files'].items():assert sha(host/n)==h,n
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(Path(__file__),out/'executed-driver.py')
 materialize(out);files=[n+'.sv' for n in RTL]
 for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_h1_pattern_producer']:
  shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'));files.append(n+'.sv')
 h1_materialize(out);files += [n+'.sv' for n in ['nes_snes_frontend','nes_transport','nes_h1_pattern']]
 put(out/'nes_h1_spi_boot.sv',integrated_boundary().replace('.load_ready(load_ready)', '.rom_chr32(),.load_ready(load_ready)'))
 files+=['nes_h1_spi_boot.sv','rom_boot_model.sv','sd_readback_wave_tb.sv']
 for n in ['rom_boot_model.sv','sd_readback_wave_tb.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,out/n)
 run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
  log=run([a.questa_bin/(tool+'.exe'),*args],out,tool);assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
 cases=[];rom=(host/'banks32/mmc3.nes').read_bytes();assert sha(host/'banks32/mmc3.nes')==r['fixtures']['banks32']
 for mode,wave,key in [('load','load-waveform.txt','load_waveform_sha256'),('check','waveform.txt','waveform_sha256')]:
  c=out/mode;c.mkdir();assert sha(host/wave)==r[key];shutil.copy2(host/wave,c/'waveform.txt')
  for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,c/n)
  put(c/'expected.hex',''.join(f'{b:02x}\n' for b in rom[16:]))
  put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
  log=run([a.questa_bin/'vsim.exe','-c','-ini','modelsim.ini','sd_readback_wave_tb','+CHECK='+str(int(mode=='check')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',1800)
  assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  marker=re.search(r'PASS SD GPIO[^\r\n]*',log);assert marker
  cases.append(dict(mode=mode,marker=marker[0],waveform_sha256=sha(c/'waveform.txt')));print(marker[0],flush=True)
 put(out/'result.json',json.dumps(dict(candidate='NES-SD-READBACK-060',rtl_replay=True,actual_stm32_execution=False,cases=cases,
  sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),driver_sha256=sha(out/'executed-driver.py')),indent=2)+'\n')

if __name__=='__main__':main()
