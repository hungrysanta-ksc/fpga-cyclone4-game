# SPDX-License-Identifier: MIT
"""Prove functional core/service wiring reuse after removing passive157 taps."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game156/evidence';o=a.prepared
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game156-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prep=json.loads((o/'materialization157.json').read_bytes())
 normalized={}
 for n in prep['copied']:
  assert sha(e/'asm'/n)==pins['asm/'+n]
  if n not in prep['changed']:assert sha(o/n)==sha(e/'asm'/n)
 for n in ['nes_rom_service.sv','nes_live_joint.sv','fxpak_nes_screen137_top.sv']:
  s=(o/n).read_text()
  if n=='nes_rom_service.sv':
   s=s.replace(' output wire [11:0] history_flags157,\n','')
   s=re.sub(r' //157 Passive view:.*?(?= //139 Parallel observation only\.)','',s,flags=re.S)
  elif n=='nes_live_joint.sv':
   s=s.replace('output wire [95:0] out_history157,\n','').replace('wire [11:0] history_flags157;\n','')
   s=s.replace('assign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,ppumem_addr};\n','').replace('.history_flags157(history_flags157),','')
  else:
   s=s.replace(' wire [95:0] history_sample157;\n','').replace('.out_history157(history_sample157),','').replace('.history_sample157(history_sample157),','')
  assert s==(e/'asm'/n).read_text(),n
  normalized[n]='exact156 after removal of output-only taps'
 assert set(prep['changed'])=={'nes_rom_spi.sv','nes_run_observer134.sv','nes_screen_status151.sv','nes_pad_trace156.sv','nes_rom_service.sv','nes_live_joint.sv','fxpak_nes_screen137_top.sv','board.qsf'}
 assert (o/'board.sdc').read_bytes()==(e/'asm/board.sdc').read_bytes()
 assert '.CS             (apu_cs && (cpu_rnw' in (o/'rtl/nes.v').read_text()
 a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=True,normalized=normalized,unchanged={n:sha(o/n) for n in prep['copied'] if n not in prep['changed']},apu_isolation_retained=True,service_decisions_unchanged=True,physical=False,scope='Exact source reuse after removing passive output taps, not placed gate equivalence or root-cause fix.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS157 passive service/core wiring; other156 inputs preserved')
if __name__=='__main__':main()
