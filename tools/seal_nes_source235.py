# SPDX-License-Identifier: MIT
"""Seal235 endpoint evidence; local traces/netlists are never public Git inputs."""
from pathlib import Path
import argparse,json,shutil,re
from nes_delta231 import ROOT,BASE,sha

def main():
    p=argparse.ArgumentParser()
    for n in ('failed','test','guards','map','archive'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    t=read(a.test/'result.json');g=read(a.guards/'result.json');m=read(a.map/'result.json')
    assert t['passed'] and t['query71'] and g['passed'] and m['passed']
    assert not t['encoder_rtl'] and not t['whole_board'] and not m['fit'] and not m['sta']
    # Normal harness was later extended with guard-only mode; production DUT
    # hashes MUST match normal, new guards, MAP and current sources exactly.
    for name in ('spi','query'):
        f=ROOT/'src/nes/rtl'/('nes_source_'+name+'235.sv');key=str(f.relative_to(BASE))
        assert t['source_pins'][key]==g['pins'][key]==m['projects'][name]['pins'][key]==sha(f)
    prior=read(ROOT/'analysis/source234-verification.json');verified={}
    for k,h in {**prior['verified_prior_pins'],**prior['public234_pins']}.items():
        f=BASE/k if k.startswith('probes/') else ROOT/k
        assert sha(f)==h,k;verified[k]=h
    previous=BASE/'probes/nes-source234';progress=read(previous/'progress.json')
    assert sha(previous/'manifest.json')==progress['manifest_sha256']
    for n in ('spi','query'):
        summary=m['projects'][n]['summary'];expected=766 if n=='spi' else 356
        assert int(re.search(r'Total logic elements\s*:\s*(\d+)',summary)[1])==expected
    assert any('M9K' in row and '512' in row and '4096' in row for row in m['projects']['spi']['ram_rows'])
    assert all(c['records']==2229 and c['blocks']==350 and c['payload']==62967 for c in t['spi_cases'])
    assert 'reference_checks=4066624' in t['c_output']
    dest.mkdir(parents=True)
    for name,src in [('test01',a.failed),('test02',a.test),('guards01',a.guards),('map01',a.map)]:shutil.copytree(src,dest/name)
    sources=[ROOT/'src/nes/rtl'/('nes_source_'+n+'235.sv') for n in ('spi','query')]
    sources += [ROOT/'tests/nes-functional'/n for n in ('source_spi235_tb.sv','source_query235_guards_tb.sv')]
    sources += [ROOT/'tools'/n for n in ('test_nes_source235.py','test_nes_source235_guards.py','run_nes_source235.ps1','map_nes_source235.py','seal_nes_source235.py')]
    sources += [ROOT/'docs/nes-source235-contract.ko.md']
    for f in sources:
        target=dest/'source01'/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=235,files=files),indent=2)+'\n')
    result=dict(stage=235,passed=True,scope=__doc__,selected=dict(test='test02',guards='guards01',map='map01',source='source01'),
        spi=t['spi_cases'],query71=True,exact_c_files=355,c_output=t['c_output'],guard_checks=dict(spi=19,query=21),
        standalone_map=dict(spi_le=766,spi_ff=430,query_le=356,query_ff=151,spi_ram='one inferred M9K simple dual port512x8',
                            additive_estimate_le=1122,replacement_arithmetic_le=1282,residual_arithmetic_le=160,whole_board_approval=False),
        warnings=['Quartus ignores async_reg (including reused206); board synchronizer constraints/CDC/STA still required',
                  'dual-clock read-during-write undefined; valid D1 ownership excludes writes to that bank',
                  '8bit CRC polynomial07 and palette32/64 intentional width truncation; bounded query_index/fault stuck low'],
        encoder_rtl=False,actual_input_run_bound=False,full_arm_irq=False,new_fit=False,new_sta=False,new_package=False,physical=False,fps_proven=False,
        decision='Do not approve full A encoder from160LE arithmetic. Next share existing SPI control/query plumbing and bound encoder/base/raw resources vs parallel metadata B on SAME scroll; no small FIT loop. Then actual input RUN/IRQ, whole-board CDC/IO/STA and paired FIRSTLEVELSCROLL.232five VBlank bursts remain.',
        public235_pins={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in sources},verified_prior_pins=verified,
        prior234_manifest_sha256=sha(previous/'manifest.json'),prior234_full_rehash=False,
        evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        evidence_result_hashes={n:sha(dest/n/'result.json') for n in ('test02','guards01','map01')})
    for f in (dest/'verification.json',ROOT/'analysis/source235-verification.json'):f.write_text(json.dumps(result,indent=2)+'\n')
    state=dict(status='ENDPOINTS_PASS_ENCODER_RESOURCE_GATE_NOT_APPROVED',selected=result['selected'],files=len(files),manifest_sha256=result['manifest_sha256'],
               pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',pushed=False,pr_updated=False,next=result['decision'],
               preserves=['GBC164','save SRAM','227 production','prior sealed archives'])
    (dest/'progress.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))

if __name__=='__main__':main()
