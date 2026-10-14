# SPDX-License-Identifier: MIT
"""Bind batch tests to the built MCU candidate; prior failed FPGA is not promoted."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_batch174 import converter,sink,header

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','c','snes','armcheck','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 m=json.loads((a.arm/'preparation-batch174.json').read_bytes())
 old=json.loads((a.prior/'preparation-cross174.json').read_bytes())
 op=old['copied']|old['changed']|old['added'];np=m['copied']|m['changed']|m['added']
 transforms={'src/nes_native_video165.c':converter,'src/nes_native_sink165.c':sink,'src/nes_native_video165.h':header}
 assert set(np)==set(op) and set(m['changed'])==set(transforms)
 for n,h in np.items():
  assert sha(a.arm/n)==h and sha(a.prior/n)==op[n],n
  if n in transforms:assert (a.arm/n).read_text()==transforms[n]((a.prior/n).read_text())
  else:assert h==op[n],n
 c=json.loads((a.c/'result.json').read_bytes());s=json.loads((a.snes/'result.json').read_bytes());arm=json.loads((a.armcheck/'result.json').read_bytes())
 for d,r in [(a.c,c),(a.snes,s)]:
  assert r['passed']
  for n,h in r['sources'].items():
   assert sha(d/n)==h,n
   if (a.arm/'src'/n).exists():assert sha(a.arm/'src'/n)==h,n
  for n,h in r['public_sources'].items():assert sha(ROOT/n)==h,n
 assert c['summary']=='PASS BATCH174 cases=9 old_patterns=342 batches=45 rejects=62 context=18064 plan=15888'
 assert s['pixels']==229376 and [v['commits'] for v in s['cases']]==[3,1] and [v['acks'] for v in s['cases']]==[92,60]
 assert arm['passed'] and arm['remaining_margin']==1040 and arm['ram_static']==26564 and arm['foreground_bound']==37312
 assert sha(a.arm/'src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 assert sha(a.arm/'src/obj-nes-100/sd2snes.elf')==arm['elf_sha256']
 for n,h in arm['public_sources'].items():assert sha(ROOT/n)==h,n
 prior=json.loads((ROOT/'analysis/cross174-verification.json').read_bytes())
 assert prior['nominal']['worst_setup']['slack']=='-0.807' or float(prior['nominal']['worst_setup']['slack'])==-0.807
 result=dict(candidate='174 bounded pattern batches',passed=True,deployed=False,hardware_package=False,fps_claim=False,
  baseline_cross174_sha256=sha(ROOT/'analysis/cross174-verification.json'),changed_sources={n:np[n] for n in transforms},
  source_pins=np,c=c,snes=s,arm=arm,wire_abi_changed=False,extra_context_bytes=0,save_sram_used=False,
  model_frame24_25=dict(pattern_packets_before=18,pattern_packets_after=3,all_packets_before=45,all_packets_after=30,
   pattern_payload_bytes=320,request_header_and_ack_bytes_saved=420,scope='Per-frame counts for these fixtures only; unchanged full-table SEAL. Not measured milliseconds/FPS.'),
  timing=dict(reused_failed_result=True,setup_ns=-0.807,new_fit=False,new_rtl=False),
  limitations=['No installable174 pair: unchanged FPGA memory timing failure','Full map/CGRAM/OAM/HDMA transmission remains','C failure tests use ACK model; separate actual65816 producer uses precomputed identical output bytes','No real-board throughput or held-input result'],
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_batch174.py','tools/test_nes_batch174.py','tools/test_nes_batch174_snes.py','tools/check_nes_batch174.py','tests/nes-functional/batch174_host.c']},
  raw_result_sha256={n:sha(d/'result.json') for n,d in [('c',a.c),('snes',a.snes),('arm',a.armcheck)]})
 a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('PASS BATCH174 source binding, C9 cases/62 rejects, actualSNES152 ACKs/229376 pixels, ARM margin1040; no FPGA promotion/ZIP')
if __name__=='__main__':main()
