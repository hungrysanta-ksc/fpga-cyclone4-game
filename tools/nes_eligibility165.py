# SPDX-License-Identifier: MIT
"""Expose exact loader READY eligibility without loaded/run recombination."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

TAG_OLD=' // Captured only when a validated READ retires. While check_busy, the'
TAG_NEW=' // Captured on queued READ; only accepted reads retain check_busy. The'

def loader(s):
    needle=' output wire rom_chr32,';assert s.count(needle)==1
    s=s.replace(needle,' output wire rom_chr32,output wire check_loaded,')
    needle=' assign run_enable=!active_reset && !fault && state==RUN;';assert s.count(needle)==1
    return s.replace(needle,needle+'''
 // loaded && !run_enable && !fault is exactly READY with reset/fault clear.
 // Export it directly so CHECK does not cascade shared loaded/run decoders.
 assign check_loaded=!active_reset && !fault && state==READY;''')

def boot(s):
    old=' wire check_active=check_enable && loaded && !loader_run && !boot_fault && !check_failed;'
    assert s.count(old)==1
    s=s.replace(old,' wire check_loaded;\n wire check_active=check_enable && check_loaded && !check_failed;')
    old='((check_enable || check_request) && (loader_run || !loaded || boot_fault))'
    assert s.count(old)==1;s=s.replace(old,'((check_enable || check_request) && !check_loaded)')
    old='nes_rom_loader loader(.commands_blocked(check_failed),';assert s.count(old)==1
    return s.replace(old,'nes_rom_loader loader(.check_loaded(check_loaded),.commands_blocked(check_failed),')

def physical(s):
    needle=' reg [2:0] state;';assert s.count(needle)==1
    s=s.replace(needle,needle+'''
 // During ACTIVE, read_last == (remaining == 1). SETUP keeps the initial
 // READ_CYCLES preload; each ACTIVE edge predicts the next terminal count.
 // This changes neither the sample edge nor HOLD/RELEASE/ACK timing.
 reg read_last;
 always @(posedge mem_clk or posedge mr)
  if(mr)read_last<=0;
  else if(state==ACTIVE)read_last<=remaining==2;
  else read_last<=(READ_CYCLES==1);''')
    needle='if(remaining==1)begin';assert s.count(needle)==1
    return s.replace(needle,'if(read_last)begin')

def prepare(baseline,tag,out):
    assert not out.exists() and str(out).isascii()
    pv=json.loads((ROOT/'analysis/predecode165-verification.json').read_bytes())
    tv=json.loads((ROOT/'analysis/tag165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==pv['raw_result_sha256']['map03']
    assert sha(tag/'result.json')==tv['raw_result_sha256']['map02']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    tagtext=(tag/'nes_rom_spi.sv').read_text();assert tagtext.count(TAG_OLD)==1
    changes={'nes_rom_loader.sv':loader((baseline/'nes_rom_loader.sv').read_text()),
             'nes_rom_boot.sv':boot((baseline/'nes_rom_boot.sv').read_text()),
             'nes_rom_spi.sv':tagtext.replace(TAG_OLD,TAG_NEW),
             'nes_rom_physical.sv':physical((baseline/'nes_rom_physical.sv').read_text())}
    for n,s in changes.items():
        old=(out/n).read_text();(out/n).write_text(s,encoding='utf8')
        (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))),encoding='utf8')
    result=dict(baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=sorted(changes),
        tag_reference_sha256=sha(tag/'result.json'),tag_spi_sha256=sha(tag/'nes_rom_spi.sv'),
        public_sources={'tools/nes_eligibility165.py':sha(Path(__file__))})
    assert sorted(n for n,h in result['sources'].items() if h!=result['baseline'][n])==result['changed']
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','tag','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.tag,a.out)
