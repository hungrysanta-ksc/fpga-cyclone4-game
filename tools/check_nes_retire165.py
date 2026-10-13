# SPDX-License-Identifier: MIT
"""Verify three exact RTL changes, executed equivalence evidence, and routed timing."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_retire165 import loader,boot,spi,retire
from check_nes_check165 import inspect

def nominal(d):
 m=json.loads((d/'nominal165-result.json').read_bytes())
 for n,h in m['preserved'].items():assert sha(d/n)==h,n
 rows=list(csv.DictReader((d/'nominal165-clocks.tsv').open(),delimiter='\t'))
 assert len({r['corner'] for r in rows})==3 and len({r['clock'] for r in rows})==4
 minima={c:{k:min(float(r['slack']) for r in rows if r['clock']==c and r['kind']==k) for k in ['setup','hold']} for c in sorted({r['clock'] for r in rows})}
 return dict(rows=len(rows),minima_ns=minima,passed=all(v[k]>=0 for v in minima.values() for k in ['setup','hold']),
  worst_setup=min((r for r in rows if r['kind']=='setup'),key=lambda r:float(r['slack'])),
  sdc_sha256=m['nominal_sdc_sha256'],preserved_files=len(m['preserved']),scope=m['scope'])

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','root','reproduced']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();root=a.root
 def d(n):return root.parent/(root.name+'-'+n)
 candidate=d('map02');m=json.loads((candidate/'preparation.json').read_bytes());rep=json.loads((a.reproduced/'preparation.json').read_bytes())
 assert m['sources']==rep['sources'] and m['baseline']==rep['baseline'] and m['variant']==rep['variant']=='serial'
 for n,h in rep['public_sources'].items():assert sha(ROOT/n)==h,n
 assert len(m['sources'])==61
 for n,h in m['sources'].items():
  assert sha(candidate/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
 assert sorted(m['changed'])==['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_spi.sv']
 for n,fn in [('nes_rom_loader.sv',loader),('nes_rom_boot.sv',boot),('nes_rom_spi.sv',spi)]:
  assert (candidate/n).read_text()==fn((a.baseline/n).read_text()),n
 def result(n):return json.loads((d(n)/'result.json').read_bytes())
 l=result('test01');s=result('serial01');r=result('retirement01');path=result('path02')
 assert l['passed'] and l['states']==52224 and l['wrong_inhibit_rejected']
 assert sha(candidate/'nes_rom_loader.sv')==l['source_sha256']
 assert sha(a.baseline/'nes_rom_loader.sv')==l['reference_sha256']
 assert s['passed'] and s['frames']==256 and s['wrong_bit_rejected']
 assert sha(d('map02')/'nes_rom_spi.sv')==s['source_sha256'] and sha(a.baseline/'nes_rom_spi.sv')==s['reference_sha256']
 assert r['passed'] and r['states']==786432 and r['wrong_fault_gate_rejected']
 assert sha(d('map03')/'nes_rom_spi.sv')==r['source_sha256'] and r['reference_sha256']==s['source_sha256']
 assert (d('map03')/'nes_rom_spi.sv').read_text()==retire((candidate/'nes_rom_spi.sv').read_text())
 assert path['passed'] and path['expected_reply_id']=='6B'
 for n,h in path['sources'].items():
  assert sha(d('path02')/'path'/n)==h,n
  if n!='game147_path_tb.sv':assert sha(candidate/n)==h,n
 # Earlier generator revisions are preserved; compare executed RTL bytes,
 # not stale generator hashes, when reusing loader and serial observations.
 for run,n in [('test01','nes_rom_loader.sv'),('serial01','nes_rom_spi.sv'),('retirement01','nes_rom_spi.sv')]:
  source=d('map03')/n if run=='retirement01' else candidate/n
  assert sha(d(run)/'candidate.sv')==sha(source),run
 for n in ['map01','map02','map03']:
  assert sha(d(n)/'board.sdc')==sha(a.baseline/'board.sdc')
  assert sha(d(n)/'secondary165-timing.tcl')==sha(ROOT/'tools/nes_secondary165_timing.tcl')
 v=inspect(candidate)
 public=['tools/nes_retire165.py','tools/test_nes_retire165.py','tools/test_nes_serial165.py','tools/test_nes_retirement165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl','tools/check_nes_check165.py','tools/check_nes_oam_port165.py','tools/test_nes_check165.py','tools/test_nes_check_path165.py','tools/test_nes_game149_spi.py','tests/nes-functional/game147_path_tb.sv','tests/nes-functional/counter131_diff_tb.sv']
 v.update(selected='map02/reproduce02',nominal=nominal(candidate),loader_only=inspect(d('map01')),rejected_retirement={**inspect(d('map03')),'nominal':nominal(d('map03')),'functional_states':786432,'adopted':False},
  functional_states=52224,serial_summary=s['summary'],spi_summary=path['summary'],negative_controls=['wrong inhibit','wrong serial bit','missing hard-fault gate (rejected variant)'],
  unchanged_files=58,source_byte_reproduction=True,clock_latency_changed=False,implementation_sdc_unchanged=True,
  cartridge_sram_reserved=True,whole_firmware_link=False,hardware_package=False,
  scope='Loader every-state sample differential; all19-bit increments and retirement priority combinations; serial coherence and actual SPI lifecycle path. Not a new SMB3 boot or complete formal proof. Extra placement budgets remain separate from exact155 clocks.',
  public_sources={n:sha(ROOT/n) for n in public})
 assert v['used_labs']<=963 and v['resources']['virtual_pins']==0
 assert not (candidate/'result.json').exists()
 (candidate/'result.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()
