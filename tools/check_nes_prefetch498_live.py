# SPDX-License-Identifier: MIT
"""Recheck completed two-frame498 artifacts after correcting a one-frame postcheck.
No RTL/CPU replay and no timing inference. Preserve the original failed postcheck.
"""
import argparse,json,re
from pathlib import Path
from nes_status495 import ROOT,sha
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['out','board','arm','client','failure-log']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();d=a.out
 failure=a.failure_log.read_text(errors='replace')
 # The original runner reached this assertion only after checking all three
 # child exit codes and absence of Lua errors. Do not accept an earlier failure.
 assert "consumer['commits']==1" in failure and failure.rstrip().endswith('AssertionError'),failure[-500:]
 assert not (d/'lua-error.txt').exists()
 host=(d/'host.log').read_text();rtl=(d/'rtl.log').read_text(errors='replace')
 marker='PASS NROM447 actual run136 START display STOP observer'
 assert marker in host and marker in rtl and 'Errors: 0' in rtl
 assert 'frames=2' in host and 'packets=68' in host
 assert '** Fatal' not in rtl and '** Error' not in rtl
 c=json.loads((d/'consumer-result.json').read_text());assert c['passed'] and c['commits']==2 and c['acks']==68 and c['retired_chunks']==4
 assert (d/'producer-done.txt').read_text().strip()=='2'
 ownership=(d/'ownership498.txt').read_text().splitlines()
 assert ownership==['COMMIT 12 ack=0 retired=0 frames=0','EA 12 ack=1 retired=0 frames=1','COMMIT 13 ack=1 retired=1 frames=1','EA 13 ack=2 retired=1 frames=2'],ownership
 assert sha(d/'nes_native_runtime165.c')==sha(a.arm/'nes_native_runtime165.c')
 for n in ['nes_live_joint.sv','nes_native_export203.sv','nes_plan_batch206.sv','nes_direct206.sv']:
  assert sha(d/n)==sha(a.board/n),n
 frames=[d/f'frame-{i}.rgb' for i in [1,2]]
 assert all(f.stat().st_size==256*239*3 for f in frames)
 prior=json.loads((ROOT/'analysis/status495-verification.json').read_text())
 assert sha(frames[0])==prior['joint']['first_pixels_SHA256']
 assert (d/'NES-first-colors.hex').is_file()
 result={'passed':True,'scope':__doc__,'consumer':c,'ownership':ownership,'host':host.strip(),
 'ROM_SHA256':sha(d/'fixture.nes'),'client_SHA256':sha(a.client/'sink165.sfc'),
 'frame_SHA256':[sha(f)for f in frames],'first_pixels_equal495':True,'second_full_pixel_oracle':False,
 'postcheck_only_reprocessed':True,'original_expected_commits':1,'actual_expected_commits':2,
 'source_ROM_hostC_SPI_65816_STOP_functional':True,'physical_M4_IRQ_common_clock':False,
 'loader_state_seeded':True,'physical_menu_return':False,
 'RTL_stop_time_ps':int(re.search(r'Time: (\d+) ps  Scope: nrom447_tb',rtl)[1]) if re.search(r'Time: (\d+) ps  Scope: nrom447_tb',rtl)else None}
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
