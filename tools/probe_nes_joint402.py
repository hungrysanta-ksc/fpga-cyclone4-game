# SPDX-License-Identifier: MIT
"""Actual400 M4 on fixed-host/RAM402 with unchanged401 view/HDMA service.
Same initial capture; RAM-owned pipeline delays source by one NES clock.
Optional matched reference delays baseline admission by that one clock.
No resident CPU or physical timing claim.
"""
import argparse,json,shutil,sys
from pathlib import Path
from nes_delta231 import BASE,sha
p=argparse.ArgumentParser(add_help=False);p.add_argument('--rtl',type=Path);p.add_argument('--reference-admission-delay',action='store_true');a,rest=p.parse_known_args();sys.argv=[sys.argv[0]]+rest
RTL=a.rtl
REFERENCE_DELAY=a.reference_admission_delay
import probe_nes_control401 as previous
driver=previous.driver;driver.__file__=__file__

def fresh(d,last,cold_quantum=0):
 assert last==916 and cold_quantum==0 and RTL
 d.mkdir(parents=True,exist_ok=False);base=BASE/'probes/nes-control401/live02'
 suffixes={'.sv','.c','.h','.inc','.s','.a','.ld','.hex','.lens','.desc','.cfg','.bin','.expected','.palette','.elf'}
 for q in base.iterdir():
  if q.is_file()and(q.suffix in suffixes or q.name.startswith('model401-')):shutil.copyfile(q,d/q.name)
 m=json.loads((RTL/'manifest402.json').read_text());sources=list(m['RTL'])
 for n,h in m['RTL'].items():assert sha(RTL/n)==h;shutil.copyfile(RTL/n,d/n)
 if 'nes_byte398.sv'in sources:shutil.copyfile(RTL/'program398.hex',d/'program398.hex')
 from analyze_nes_joint400 import image
 assert image(d/'output.elf')==image(RTL/'output.elf')
 s=(base/'joint266_tb.sv').read_text();a=s.index('integer trace399;');b=s.rindex('endmodule');s=s[:a]+s[b:]
 # Both cache implementations expose the same WAIT state. Only the old
 # cache had a diagnostic alias named pending; do not require that alias.
 s=s.replace('planrom.source.cache_path.cache.pending','(planrom.source.cache_path.cache.state==planrom.source.cache_path.cache.WAIT)')
 # Diagnostic refers to the now-deleted VM fault pin; all physical/checker
 # faults retain their actual signals and normal positive-run assertions.
 if m['semantic_VM_removed']:s=s.replace('dut.flow.cpufault',"1'b0")
 if REFERENCE_DELAY:
  assert m['variant']=='reference' and s.count('.source_start_ready(start_ready)')==1
  s=s.replace('.source_start_ready(start_ready)','.source_start_ready(start_ready&&admission402)')
  anchor='  nes_native_capture365 #';assert s.count(anchor)==1
  s=s.replace(anchor,''' reg admission402=0;
 always @(posedge clk)if(reset)admission402<=0;else admission402<=owned&&geometry_valid;
'''+anchor)
 (d/'joint266_tb.sv').write_text(s,newline='\n')
 (d/'manifest402.json').write_text(json.dumps(dict(RTL=m['RTL'],ELF=sha(d/'output.elf'),worker_reference=sha(base/'executed-worker367.py'),test=sha(d/'joint266_tb.sv'),program=sha(d/'program398.hex')if'nes_byte398.sv'in sources else None,service='401/service02',base_test=sha(base/'joint266_tb.sv'),semantic_VM_removed=m['semantic_VM_removed'],source_plan_SPI_bodies_replaced=False),indent=2)+'\n',newline='\n')
 return sources

driver.prepare=fresh
if __name__=='__main__':driver.main()
