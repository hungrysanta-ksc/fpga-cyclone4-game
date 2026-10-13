# SPDX-License-Identifier: MIT
"""Explicit C2/C3 contract, exact reuse pins and routed release gate."""
from pathlib import Path
import argparse,json,csv
from nes_game147 import ROOT,sha
from nes_commitstage167 import transform
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements

def main():
 p=argparse.ArgumentParser()
 for n in ['pacing','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;b=a.pacing/'map04';m=json.loads((d/'preparation.json').read_bytes())
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and m['changed']==['nes_rom_spi.sv']
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h and sha(b/n)==m['baseline'][n],n
  if n!='nes_rom_spi.sv':assert h==m['baseline'][n],n
 assert (d/'nes_rom_spi.sv').read_text()==transform((b/'nes_rom_spi.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes())
 assert t['passed'] and t['wire_bits']==14016 and t['late_boundaries']==24 and not t['same_edge']
 assert t['source_sha256']==sha(d/'nes_rom_spi.sv') and t['reference_sha256']==sha(b/'nes_rom_spi.sv')
 for n,h in t['sources'].items():assert sha(a.test/n)==h,n
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:assert sha(d/n)==t['sources'][n],n
 # The functional wait-policy proofs apply to exactly the same fill/export
 # and arbiter bytes; no repeated whole-game boot or SNES diagnostic.
 old=json.loads((ROOT/'analysis/pacing167-verification.json').read_bytes())
 e=json.loads((a.pacing/'equiv02/result.json').read_bytes());r=json.loads((a.pacing/'test02/result.json').read_bytes())
 assert e==old['counter_equivalence'] and e['passed'] and r['passed']
 assert sha(a.pacing/'test02/result.json')==e['reference_result_sha256']
 assert e['candidate_sha256']==sha(d/'nes_native_fill165.sv')
 for n in ['nes_native_export165.sv','nes_native_arbiter165.sv']:assert sha(d/n)==sha(a.pacing/'test02'/n),n
 for n,h in old['public_sources'].items():assert sha(ROOT/n)==h,n
 arm=a.pacing/'arm01';ar=json.loads((a.pacing/'armcheck03/result.json').read_bytes())
 assert ar['passed'] and ar['remaining_margin']>=1024
 assert sha(arm/'src/obj-nes-100/firmware.stm')==ar['firmware_sha256']
 transport=['src/nes_game149_spi.inc','src/nes_h1_stm32.c','src/nes_rom_spi.c']
 # The actual linked transport requests SS-high/setup 2us, 84MHz/32 mode0.
 engine=(arm/transport[0]).read_text()
 assert 'io->select(io->ctx,false);io->wait_us(io->ctx,2);' in engine
 assert '(4u<<SPI_CR1_BR_Pos)' in engine and 'CONFIG_CPU_FREQUENCY != 84000000' in engine
 assert 'return nes_game149_transfer(io,tx,rx);' in (arm/transport[2]).read_text()
 v=inspect(d);nt=nominal(d)
 paths=list(csv.DictReader((d/'commitstage167-paths.tsv').open(),delimiter='\t'))
 groups=['check','loaded','accept_clear','accept_inc']
 assert len(paths)==12
 targeted={g:min(float(x['slack']) for x in paths if x['group']==g) for g in groups}
 io=measurements(d) if (d/'boundary165-paths.tsv').exists() else None
 passed=nt['passed'] and io is not None and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
 pub={**t['public_sources']}
 for n in ['tools/check_nes_commitstage167.py','tools/nes_commitstage167_paths.tcl','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:pub[n]=sha(ROOT/n)
 for n,h in pub.items():assert sha(ROOT/n)==h,n
 result=dict(passed=passed,fit=v,nominal=nt,targeted_setup_ns=targeted,io=io,functional=t,
  unchanged_files=60,byte_reproduced=True,counter_extra_cycles=1,same_edge=False,spi_identity=116,
  reused_pacing_verification_sha256=sha(ROOT/'analysis/pacing167-verification.json'),
  reused_fill_equivalence_sha256=sha(a.pacing/'equiv02/result.json'),
  reused_fill_reference_sha256=sha(a.pacing/'test02/result.json'),
  reused_arm_check_sha256=sha(a.pacing/'armcheck03/result.json'),
  reused_mcu_snes_sha256=sha(a.pacing/'mcu-reuse.json'),
  mcu_transport_pins={n:sha(arm/n) for n in transport},
  physical=False,full_io_approved=False,public_sources=pub)
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=passed,nominal=nt['worst_setup'],le=v['fit_le'],labs=v['used_labs'],targeted=targeted,io_tested=io is not None)))
if __name__=='__main__':main()
