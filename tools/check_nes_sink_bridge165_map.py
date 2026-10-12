# SPDX-License-Identifier: MIT
"""Synthesize only the sink bridge to check memory inference, not full-core fit."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['verified','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();v=json.loads((a.verified/'result.json').read_bytes());assert v['passed']
 a.out.mkdir(parents=True,exist_ok=False)
 files=['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv']
 for n in files:
  path='src/nes/diagnostic/'+n;assert sha(ROOT/path)==v['public_sources'][path]
  shutil.copy2(ROOT/path,a.out/n)
 assert sha(a.verified/'sink-program.hex')==v['inputs']['sink01/client/sink-program.hex']
 shutil.copy2(a.verified/'sink-program.hex',a.out/'sink-program.hex')
 qsf='set_global_assignment -name FAMILY "Cyclone IV E"\nset_global_assignment -name DEVICE EP4CE15F17C8\nset_global_assignment -name TOP_LEVEL_ENTITY nes_sink_bridge165\nset_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files\n'
 qsf+='set_global_assignment -name NUM_PARALLEL_PROCESSORS 2\n'+''.join('set_global_assignment -name SYSTEMVERILOG_FILE '+n+'\n' for n in files)
 (a.out/'bridge.qsf').write_text(qsf);(a.out/'bridge.qpf').write_text('PROJECT_REVISION = "bridge"\n')
 with (a.out/'map.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_map.exe'),'bridge'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 log=(a.out/'map.log').read_text(errors='replace');assert r.returncode==0,log[-6000:]
 report=(a.out/'output_files/bridge.map.rpt').read_text(errors='replace')
 assert 'Analysis & Synthesis was successful' in log
 mifs=list((a.out/'db').glob('bridge.ram0_nes_sink_bus165_*.hdl.mif'));assert len(mifs)==1
 pairs=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mifs[0].read_text(),re.M);assert len(pairs)==4096
 image=bytes(int(b,2) for _,b in sorted((int(i),b) for i,b in pairs))
 assert image==bytes.fromhex((a.out/'sink-program.hex').read_text())
 assert re.search(r'program_rom_rtl_0.*M9K\s*; ROM\s*; 4096\s*; 8',report)
 assert re.search(r'buffer_rtl_0.*M9K\s*; Simple Dual Port\s*; 256\s*; 8',report)
 warnings=re.findall(r'^Warning .*',log,re.M)
 assert all('Warning (10030)' in w and 'program_rom.' in w for w in warnings),warnings
 result=dict(passed=True,rom_bytes_verified=4096,packet_ram_bytes=256,warnings=3,scope='Bridge-only Analysis & Synthesis; no fitter, parent core, board pin/timing or hardware approval.',public_sources={**{n:sha(ROOT/n) for n in v['public_sources'] if n.startswith('src/nes/diagnostic/')},'tools/check_nes_sink_bridge165_map.py':sha(Path(__file__))},report_sha256=sha(a.out/'output_files/bridge.map.rpt'),summary=[s.strip() for s in report.splitlines() if re.search('Total logic elements|Total registers|Total memory bits|Total block memory',s)])
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary']))
if __name__=='__main__':main()
