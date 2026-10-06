# SPDX-License-Identifier: MIT
"""054 joint fit from hash-checked private053 source export; no raw inputs vendored.

This adds SPI boot to the prior actual-core resource geometry. It excludes the
H1 diagnostic program ROM/shell, physical board PLL/pins and SNES runtime consumer.
"""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,put,sha,run

def main():
 p=argparse.ArgumentParser()
 for name in ['baseline','out','quartus-bin']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();base=a.baseline.resolve();out=a.out.resolve()
 if not str(out).isascii():p.error('Use an ASCII output path')
 previous=json.loads((base/'result.json').read_text())
 if previous['candidate']!='NES-R1-ROM-BOOT-053':p.error('Expected frozen053 source export')
 out.mkdir()
 for name,digest in previous['sources'].items():
  if sha(base/name)!=digest:raise RuntimeError('Changed baseline '+name)
  dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,dest)
 for name in ['nes_rom_spi','nes_spi_boot']:shutil.copyfile(ROOT/'src/nes'/(name+'.sv'),out/(name+'.sv'))
 source=(out/'nes_live_joint.sv').read_text()
 old='input wire ext_load_begin,ext_load_chr32,ext_load_valid,ext_load_end,ext_start,ext_stop,\ninput wire [7:0] ext_load_data,'
 assert source.count(old)==1
 source=source.replace(old,'input wire ext_SPI_SS,ext_SPI_SCK,ext_SPI_MOSI,\noutput wire out_spi_miso,out_spi_selected,out_spi_fault,\noutput wire [3:0] out_spi_error,')
 source=re.sub(r'^wire (?:\[7:0\] )?(?:load_begin|load_chr32|load_valid|load_end|start|stop|load_data)=ext_[^;]+;\n','',source,flags=re.M)
 source=source.replace('nes_rom_boot physical(', 'nes_spi_boot physical(')
 for name in ['load_begin','load_chr32','load_valid','load_end','start','stop','load_data']:
  source=source.replace('.'+name+'('+name+'),\n','')
 source=source.replace('.load_ready(load_ready),', '''.SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
.spi_miso(out_spi_miso),.spi_selected(out_spi_selected),.spi_fault(out_spi_fault),.spi_error(out_spi_error),
.load_ready(load_ready),''')
 assert 'ext_load_' not in source and 'ext_start' not in source
 put(out/'nes_live_joint.sv',source)
 qsf=(out/'live.qsf').read_text()
 qsf='\n'.join(line for line in qsf.splitlines() if not re.search(r'-to (ext_load_\w+|ext_start|ext_stop)$',line))+'\n'
 for name in ['nes_rom_spi','nes_spi_boot']:qsf+='set_global_assignment -name SYSTEMVERILOG_FILE '+name+'.sv\n'
 for name in ['ext_SPI_SS','ext_SPI_SCK','ext_SPI_MOSI','out_spi_miso','out_spi_selected','out_spi_fault','out_spi_error']:
  qsf+='set_instance_assignment -name VIRTUAL_PIN ON -to '+name+'\n'
 put(out/'live.qsf',qsf)
 files=list(previous['sources'])+['nes_rom_spi.sv','nes_spi_boot.sv']
 result=dict(candidate='NES-R1-SPI-BOOT-054',baseline_candidate=previous['candidate'],
             baseline_result_sha256=sha(base/'result.json'),sources={n:sha(out/n) for n in files},
             driver_sha256=sha(Path(__file__)),phases={},hardware_image=False,
             scope='053 joint diagnostic geometry plus SPI; no H1 shell/program ROM, board PLL/pins, real SNES consumer or STA signoff')
 for phase in ['map','fit']:
  try:
   run([a.quartus_bin/('quartus_'+phase+'.exe'),'live'],out,phase)
   result['phases'][phase]=0
  except RuntimeError:
   result['phases'][phase]=1;put(out/'result.json',json.dumps(result,indent=2)+'\n');raise
  put(out/'result.json',json.dumps(result,indent=2)+'\n')
 print((out/'output_files/live.fit.summary').read_text(errors='replace'))

if __name__=='__main__':main()
