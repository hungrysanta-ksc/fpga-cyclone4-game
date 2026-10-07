# SPDX-License-Identifier: MIT
"""Audit frozen063 evidence; does not execute a new C/RTL/ARM/hardware test."""
from pathlib import Path
import argparse,json,re
from nes_spi_boot import ROOT,sha
from nes_menu_diagnostic import source
from nes_board_session import platform

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence.resolve()
 manifest=read(e/'manifest.json');assert manifest['candidate']=='NES-BOARD-SESSION-063'
 for n,h in manifest['files'].items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 host=e/'host-02';h=read(host/'result.json');assert h['host_pass'] and not h['actual_stm32_execution']
 assert (host/'nes_h1_stm32.c').read_text()==source()
 assert (host/'session-platform.c').read_text()==platform()
 for n,v in h['sources'].items():assert sha(host/n)==v,n
 assert sha(host/'executed-driver.py')==h['driver_sha256']
 reused=read(e/'reused-production.json');fit=read(e/'reused061-fit.json')
 for n,v in reused['ARM062_sources'].items():assert sha(host/n)==v,n
 for n,v in reused['unchanged_public_headers'].items():assert sha(host/n)==sha(ROOT/'src/nes/firmware'/n)==v,n
 for c,total,frames,checked,delay in [('fine_x',81920,409616,22938352,113872638000),('banks32',98304,491536,27525872,136646398000)]:
  assert f'PASS SESSION C bytes={total} frames={frames} delay_ns={delay} compared={total} no_START=1' in (host/'host.log').read_text()
  assert sha(host/(c+'.trace'))==h['traces'][c]
  out=e/('full-'+c+'-02');r=read(out/'result.json');log=(out/'simulation.log').read_text()
  assert r['full_session'] and r['case']==c and r['limit_frames']==0
  assert r['mask_link']==r['park_legacy']==1 and r['memory_clock_mhz']==8 and r['SPI_delay_us']==2
  assert not r['hardware_execution'] and not r['analog_PLL']
  assert r['host_result_sha256']==sha(host/'result.json') and r['trace_sha256']==h['traces'][c]
  link=read(out/'trace-link.json');assert link['path']=='host-02/'+c+'.trace' and link['sha256']==h['traces'][c]
  assert r['fixture_sha256']==h['fixtures'][c] and sha(e/link['path'])==h['traces'][c]
  assert r['marker'] in log and not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  expected=f'PASS SESSION FULL bytes={total} frames={frames} writes={total} reads={total} ACK={total} checked={checked} FINISH=1 STOP=1 no_RUN=1 mask_link=1 park_legacy=1'
  assert r['marker']==expected,r['marker']
  for n,v in r['sources'].items():assert sha(out/n)==v,n
  for n,v in fit['sources'].items():
   if n.endswith('.sv'):
    assert sha(out/('production-'+n if n=='nes_h1_spi_boot.sv' else n))==v,n
  before=(out/'production-nes_h1_spi_boot.sv').read_text();after=(out/'nes_h1_spi_boot.sv').read_text()
  assert after==before.replace('.queue_clk(clock84),.host_clk(clock84),.reset(reset)',
   '.queue_clk(clock84 && board_session_tb.link_clocks),.host_clk(clock84 && board_session_tb.link_clocks),.reset(reset)')
  assert sha(out/'executed-driver.py')==r['driver_sha256']
  assert sha(out/'board_session_tb.sv')==sha(ROOT/'tests/nes-functional/board_session_tb.sv')
 # Same first64 transactions, including29 physical bytes, without either clock optimization.
 boundary='SESSION BOUNDARY frames=64 writes=29 reads=0 checked=3440'
 for folder in ['prefix-baseline-02','prefix-parked-02','full-fine_x-02','full-banks32-02']:
  assert boundary in (e/folder/'simulation.log').read_text(),folder
 baseline=read(e/'prefix-baseline-02/result.json');assert baseline['mask_link']==baseline['park_legacy']==0
 current_tb=(ROOT/'tests/nes-functional/board_session_tb.sv').read_text()
 old_read="  if(psram_bhe!==reads[0]||psram_ble!==!reads[0])$fatal(1,\"063 physical read lane at%0d\",reads);"
 new_read="  // The existing reader enables the complete16-bit word, then chooses the\n  // requested byte internally. Byte-write strobes do not apply to reads.\n  if(psram_bhe!==1'b0||psram_ble!==1'b0)$fatal(1,\"063 physical read word enables at%0d\",reads);"
 assert current_tb.count(new_read)==1
 for folder in ['prefix-baseline-02','prefix-parked-02']:
  # Neither prefix reaches CHECK. Only this unexecuted read monitor differs.
  assert (e/folder/'board_session_tb.sv').read_text()==current_tb.replace(new_read,old_read)
 parked=read(e/'prefix-parked-02/result.json');assert parked['limit_frames']==8192 and not parked['full_session']
 assert 'frames=8192 writes=4093 reads=0 checked=458608' in parked['marker']
 slow=read(e/'prefix-masked-02/result.json');assert 'frames=8192 writes=4093 reads=0 checked=458608' in slow['marker']
 assert '** Fatal: 063 MCU sample mismatch frame0 opcf bit8 gotz expected0' in (e/'prefix-masked-01/simulation.log').read_text()
 assert '** Fatal: 063 physical read lane at0' in (e/'full-fine_x-01/simulation.log').read_text()
 print(f'PASS063 frozen evidence files={len(manifest["files"])}; complete80/96KiB C GPIO at8MHz/2us; legacy-domain test transform; no hardware execution')

if __name__=='__main__':main()
