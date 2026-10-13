# SPDX-License-Identifier: MIT
"""Routed boundary measurements, explicit conditional bounds, no false signoff."""
from pathlib import Path
import argparse,csv,json,re
from nes_game147 import ROOT,sha
from nes_boundary165 import mailbox,joint
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def rows(d,n):return list(csv.DictReader((d/n).open(),delimiter='\t'))

def measurements(d):
 r=rows(d,'boundary165-paths.tsv');groups=sorted({x['group'] for x in r})
 assert len({x['corner'] for x in r})==3
 summary={g:dict(rows=sum(x['group']==g for x in r),max_delay_ns=max(float(x['delay']) for x in r if x['group']==g),
                min_raw_slack_ns=min(float(x['slack']) for x in r if x['group']==g)) for g in groups}
 def maximum(g,predicate=lambda x:True):
  values=[float(x['delay']) for x in r if x['group']==g and predicate(x)];assert values,g;return max(values)
 # Bounds reused from the existing digital bus model; PCB/receiver setup
 # allowances are assumptions, not measurements of this cartridge/console.
 psram_addr=17*5.952-70-maximum('psram_address')-maximum('psram_input')-4
 psram_active=16*5.952-70-maximum('psram_active')-maximum('psram_input')-4
 sin=maximum('input',lambda x:x['from'].startswith('SNES_'))
 sout=maximum('output',lambda x:x['to'].startswith('SNES_'))
 direct=maximum('combinational',lambda x:x['from'].startswith('SNES_') and x['to'].startswith('SNES_'))
 # meta -> sync -> synchronous ROM/RAM/tag; add worst phase through 3 edges.
 snes=max(3*11.904+sin+sout,direct)+6
 spi_in=maximum('input',lambda x:x['from'].startswith('SPI_'))
 spi_out=maximum('output',lambda x:x['to']=='SPI_MISO')
 # Slowest of the SPI endpoints is the NES-clock observer: 2FF+edge handling.
 spi_reply=3*45.454+spi_in+spi_out+4
 bundle={g:dict(delay_ns=maximum(g),one_rx_period_ns=period,margin_after_2ns_allowance=round(period-maximum(g)-2,3))
         for g,period in [('records',11.904),('prepared',45.454),('pad',45.454)]}
 topology=rows(d,'boundary165-topology.tsv');assert len(topology)>=9
 for x in topology:assert x['to']==x['from'][:-2]+'1]',x
 negative=[x for x in r if x['group'] in ['recovery','removal'] and float(x['slack'])<0]
 def protocol_payload(x):
  n=x['to']
  return (':native_records|' in n or ':native_prepared|' in n or ':native_spi|' in n) and not re.search(r'\|(sr|dr)\[\d\]$',n)
 payload_negative=[x for x in negative if protocol_payload(x)]
 return dict(path_rows=len(r),groups=summary,ports=rows(d,'boundary165-ports.tsv'),
  psram_address_margin_ns=round(psram_addr,3),psram_active_margin_ns=round(psram_active,3),
  psram_conditional_margin_ns=round(min(psram_addr,psram_active),3),psram_access_ns=70,pcb_round_trip_allowance_ns=4,
  snes_read_envelope_ns=round(snes,3),snes_model_sample_ns=270,snes_extra_allowance_ns=6,
  spi_reply_envelope_ns=round(spi_reply,3),spi_half_period_ns=round(1000/2.625/2,3),spi_extra_allowance_ns=4,
  bundle=bundle,first_stage_fanout_one=len(topology),negative_reset_path_count=len(negative),
  negative_reset_worst_paths=sorted(negative,key=lambda x:float(x['slack']))[:24],
  native_payload_negative_reset_path_count=len(payload_negative),
  native_payload_negative_reset_paths=sorted(payload_negative,key=lambda x:float(x['slack']))[:24],
  conditional_data_bounds_pass=min(psram_addr,psram_active)>0 and snes<270 and spi_reply<1000/2.625/2 and all(v['margin_after_2ns_allowance']>0 for v in bundle.values()),
  native_payload_reset_pass=not payload_negative,mtbf_calculated=False,full_io_signoff=False,
  scope='1000ns IO exceptions expose data delay only; their slack is not a pass criterion. Mixed-clock groups are top100 samples per pair/corner, not complete CDC coverage. Digital conditional envelopes exclude unmeasured electrical behaviour, metastability and stopped-clock response deadlines.')

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','baseline-io','candidate','reproduced','test']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.candidate;m=json.loads((d/'preparation.json').read_bytes())
 assert m==json.loads((a.reproduced/'preparation.json').read_bytes())
 assert len(m['sources'])==61 and set(m['changed'])=={'nes_native_mailbox165.sv','nes_live_joint.sv'}
 for n,h in m['sources'].items():
  assert sha(d/n)==sha(a.reproduced/n)==h,n
  assert sha(a.baseline/n)==m['baseline'][n],n
  if n not in m['changed']:assert h==m['baseline'][n],n
 assert (d/'nes_native_mailbox165.sv').read_text()==mailbox((a.baseline/'nes_native_mailbox165.sv').read_text())
 assert (d/'nes_live_joint.sv').read_text()==joint((a.baseline/'nes_live_joint.sv').read_text())
 t=json.loads((a.test/'result.json').read_bytes());assert t['passed'] and t['delivered']==450 and t['wrong_reset_rejected']
 for n,h in t['sources'].items():assert sha(d/n)==h==sha(a.test/n),n
 assert sha(d/'nes_live_joint.sv')==t['parent_sha256']
 for n,h in t['public_sources'].items():assert sha(ROOT/n)==h,n
 for src in [d,a.baseline_io]:assert sha(src/'nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
 # The read-only original DB copy must retain every routed source/database
 # byte except TimeQuest's own timing netlist and IO simulation cache.
 preserved={f.relative_to(a.baseline).as_posix():sha(f) for f in a.baseline.rglob('*') if f.is_file() and
  (f.suffix in ['.sv','.v','.vhd','.qsf','.qpf','.sdc'] or ('db' in f.parts and not f.name.endswith('.taw.rdb') and '_io_sim_cache.' not in f.name))}
 for n,h in preserved.items():assert sha(a.baseline_io/n)==h,n
 before=measurements(a.baseline_io);after=measurements(d)
 v=inspect(d);actual=nominal(d)
 adopted=v['fit_pass'] and actual['passed'] and after['conditional_data_bounds_pass'] and after['native_payload_reset_pass']
 public={**m['public_sources'],**t['public_sources']}
 for n in ['tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl']:public[n]=sha(ROOT/n)
 result={**v,'nominal':actual,'adopted':adopted,'baseline_measurements':before,'measurements':after,'functional':t,
  'source_byte_reproduction':True,'unchanged_files':59,'original_routed_files_preserved':len(preserved),
  'reset_release_latency_changed':True,'steady_state_packet_protocol_unchanged':True,'spi_identity':0x74,
  'cartridge_sram_reserved':True,'mcu_integrated':False,'hardware_package':False,'full_timing_approved':False,
  'public_sources':public,'baseline_result_sha256':m['baseline_result_sha256']}
 assert not (d/'result.json').exists();(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(adopted=adopted,fit_le=v['fit_le'],labs=v['used_labs'],nominal=actual['worst_setup'],
  conditional_io=after['conditional_data_bounds_pass'],native_payload_reset=after['native_payload_reset_pass'],
  negative_native_reset_paths=len(after['native_payload_negative_reset_paths']))))
if __name__=='__main__':main()
