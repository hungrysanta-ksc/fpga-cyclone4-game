# SPDX-License-Identifier: MIT
"""Whole-board Lite MAP for the common SPI and short-status replacement."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,ROOT,once,sha
from nes_joint270 import patch_files,pass_ports,joint_ports,top_bus,JOINT_BIND,PLAN_BIND

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 old=BASE/'probes/nes-joint269/board03';pins={}
 for f in old.rglob('*'):
  rel=f.relative_to(old)
  if any(x in ('work','db','incremental_db','output_files') for x in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   t=d/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);pins[rel.as_posix()]=sha(f)
 patch_files(d)
 p=d/'nes_joint266.sv';p.write_text(joint_ports(p.read_text()),encoding='utf-8',newline='\n')
 p=d/'nes_plan_path267.sv';p.write_text(pass_ports(p.read_text(),'nes_plan_spi200 endpoint('),encoding='utf-8',newline='\n')
 p=d/'nes_live_joint.sv';s=p.read_text();s=once(s,'nes_joint267_board native_joint267(',top_bus('host_clk','reset','ext_SPI_SS','ext_SPI_SCK','ext_SPI_MOSI')+'nes_joint267_board native_joint267('+JOINT_BIND)
 s=once(s,'nes_plan_path267 retained_plan267(','nes_plan_path267 retained_plan267('+PLAN_BIND);p.write_text(s,encoding='utf-8',newline='\n')
 p=d/'board.qsf';p.write_text(p.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_spi270.sv\n',encoding='utf-8',newline='\n')
 for n in ['nes_joint270.py','map_nes_joint270.py']:shutil.copyfile(ROOT/'tools'/n,d/n)
 with (d/'map.log').open('wb') as f:r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 result=dict(passed=r.returncode==0 and not undriven,summary=(d/'output_files/board.map.summary').read_text(),input_hashes=pins,script_sha256=sha(Path(__file__)),undriven_outputs=undriven,FIT=False,STA=False,scope=__doc__)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['summary']);assert result['passed']

if __name__=='__main__':main()
