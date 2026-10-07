# SPDX-License-Identifier: MIT
"""Audit frozen070 full069 C-to068 pin sessions; private evidence required."""
from pathlib import Path
import argparse,json,re
from nes_spi_boot import ROOT,sha

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def audit(e):
    e=e.resolve();meta=read(ROOT/'analysis/cf68-session-verification.json');m=read(e/'manifest.json')
    assert m['candidate']==meta['candidate']=='NES-CF68-SESSION-070'
    assert sha(e/'manifest.json')==meta['manifest_sha256'] and len(m['files'])==meta['archived_files']
    for n,h in m['files'].items():
        p=(e/n).resolve();assert p.is_relative_to(e) and sha(p)==h,n
    for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
    original=read(e/'reused069-manifest.json')
    assert sha(e/'reused069-manifest.json')==meta['reused_mcu_manifest_sha256']
    assert sha(e/'reused068-manifest.json')==meta['reused_fpga_manifest_sha256']
    for p in (e/'host').rglob('*'):
        if p.is_file():assert sha(p)==original['files']['session/'+p.relative_to(e/'host').as_posix()],p
    h=read(e/'host/result.json');assert h['candidate']=='NES-CF68-MCU-069' and h['session'] and not h['actual_stm32_execution']
    for n,v in h['files'].items():assert sha(e/'host'/n)==v,n
    fit=read(e/'reused068-fit.json');sv={n:v for n,v in fit['sources'].items() if n.endswith('.sv')}
    assert sha(e/'reused068-fit.json')==read(e/'reused068-manifest.json')['files']['fit/result.json']
    assert len(sv)==15
    boundary='SESSION BOUNDARY frames=64 writes=29 reads=0 checked=3440'
    totals=[]
    for c,total,frames,checked in [('fine_x',81920,409616,22938352),('banks32',98304,491536,27525872)]:
        out=e/('full-'+c+'-01');r=read(out/'result.json');log=(out/'simulation.log').read_text()
        assert r['full_session'] and r['limit_frames']==0 and r['case']==c
        assert r['mask_link']==r['park_legacy']==1 and r['startup_ready_wait']
        assert r['mcu_candidate']==h['candidate'] and r['fpga_candidate']=='NES-DIAG-SAFETY-068'
        assert r['host_result_sha256']==sha(e/'host/result.json')
        assert r['trace_sha256']==sha(out/'session.trace')==sha(e/'host'/(c+'.trace'))==h['traces'][c]
        assert r['fixture_sha256']==sha(e/'host'/c/'mmc3.nes')==h['fixtures'][c]
        assert r['production_sources']==sv
        assert r['fpga_manifest_sha256']==meta['reused_fpga_manifest_sha256']
        assert r['mcu_manifest_sha256']==meta['reused_mcu_manifest_sha256']
        for n,v in r['sources'].items():assert sha(out/n)==v,n
        for n,v in sv.items():assert sha(out/('production-'+n if n=='nes_h1_spi_boot.sv' else n))==v,n
        before=(out/'production-nes_h1_spi_boot.sv').read_text();after=(out/'nes_h1_spi_boot.sv').read_text()
        assert after==before.replace('.queue_clk(clock84),.host_clk(clock84),.reset(reset)',
            '.queue_clk(clock84 && cf68_session_tb.link_clocks),.host_clk(clock84 && cf68_session_tb.link_clocks),.reset(reset)')
        assert sha(out/'executed-driver.py')==r['driver_sha256']==meta['public_sources']['tools/nes_cf68_session_replay.py']
        assert sha(out/'cf68_session_tb.sv')==sha(out/'executed-testbench.sv')==meta['public_sources']['tests/nes-functional/cf68_session_tb.sv']
        expected=f'PASS SESSION FULL bytes={total} frames={frames} writes={total} reads={total} ACK={total} checked={checked} FINISH=1 STOP=1 no_RUN=1 mask_link=1 park_legacy=1'
        assert r['marker']==expected and expected in log and boundary in log
        # %t follows1ps precision even though the old label says ready_ns.
        assert 'SESSION STARTUP ready_ns=201062500 clock8_free_running=1' in log
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        assert not r['hardware_execution'] and not r['analog_PLL']
        assert r['memory_clock_mhz']==8 and r['SPI_delay_us']==2
        data=(e/'host'/c/'mmc3.nes').read_bytes()[16:]
        assert (out/'expected.hex').read_text()==''.join(f'{b:02x}\n' for b in data)
        assert len(data)==total;totals.append((total,frames,checked))
    for folder,frames,mask,park in [('baseline64-02',64,0,0),('parked8192-01',8192,1,1)]:
        out=e/folder;r=read(out/'result.json');log=(out/'simulation.log').read_text()
        assert not r['full_session'] and r['limit_frames']==frames and r['mask_link']==mask and r['park_legacy']==park
        assert boundary in log and r['marker'] in log and '** Fatal:' not in log
        assert sha(out/'cf68_session_tb.sv')==meta['public_sources']['tests/nes-functional/cf68_session_tb.sv']
        assert sha(out/'executed-driver.py')==meta['public_sources']['tools/nes_cf68_session_replay.py']
    neg=e/'mutation-response-01';r=read(neg/'result.json');log=(neg/'simulation.log').read_text()
    assert r['expected_failure'] and r['mutation']=='response' and '** Fatal:' in log and r['assertion'] in log
    assert r['assertion']=='070 MCU sample mismatch frame0 opcf bit8'
    first=(e/'baseline64-01/simulation.log').read_text();assert 'Could not find work.cf68_session_tb' in first
    assert meta['full_board_spi_replay'] and not meta['installable'] and not meta['hardware_execution'] and not meta['new_fpga_asm_pair']
    assert tuple(sum(t[i] for t in totals) for i in range(3))==(180224,901152,50464224)
    print(f'PASS070 frozen={len(m["files"])} full_CF68_C_pin_bytes=180224 frames=901152 response_bits=50464224 ACK_FINISH_STOP=2 prefix2 response_negative1 no_install')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();audit(a.evidence)
