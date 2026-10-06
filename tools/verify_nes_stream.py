"""Audit the six NES-P1-STREAM-002 runs, including raw pixel evidence.
SPDX-License-Identifier: MIT. Expected negatives must fail for the intended reason.
"""
from pathlib import Path
import argparse,hashlib,json

def verify(root):
    names=['off','on','reset','length','overrun','selection'];results={};summary={}
    for name in names:
        p=root/name;d=json.loads((p/'result.json').read_text());results[name]=d
        build=json.loads((p/'build/manifest.json').read_text())
        assert hashlib.sha256((p/'build/manifest.json').read_bytes()).hexdigest()==d['manifest_sha256']
        assert hashlib.sha256((p/'build/stream.sfc').read_bytes()).hexdigest()==build['rom_sha256']
        for f in d['frames']:
            raw=(p/f"frame-{f['index']:03}.rgb").read_bytes()
            assert hashlib.sha256(raw).hexdigest()==f['sha256']
            expected=(p/'build'/f"expected-{f['frame_id']%16:02}.rgb").read_bytes()
            assert len(raw)==len(expected)==256*239*3
            diff=sum(raw[i:i+3]!=expected[i:i+3] for i in range(0,len(raw),3))
            assert diff==f['different_pixels']
        assert all(b['emulator_frame']==a['emulator_frame']+1 for a,b in zip(d['frames'],d['frames'][1:]))
        summary[name]=dict(expected_pass=name in ('off','on','reset'),observed_pass=d['passed'],frames=len(d['frames']),
            different_pixels=sum(f['different_pixels'] for f in d['frames']),max_payload_bytes=d['max_payload_bytes'],
            max_duration_master_clocks=d['max_duration_master_clocks'],min_deadline_margin_master_clocks=d['min_deadline_margin_master_clocks'],
            outcome_counts={k:sum(t['outcome']==k for t in d['transactions']) for k in ('commit','reset_abort','halt')},
            rom_sha256=build['rom_sha256'],result_sha256=hashlib.sha256((p/'result.json').read_bytes()).hexdigest())
    for name in ('off','on','reset'):assert results[name]['passed'] and not results[name]['errors']
    assert len(results['off']['frames'])==len(results['on']['frames'])==128
    assert [f['sha256'] for f in results['off']['frames']]==[f['sha256'] for f in results['on']['frames']]
    d=results['reset'];ab=[t for t in d['transactions'] if t['outcome']=='reset_abort']
    assert len(d['frames'])==64 and len(ab)==1 and ab[0]['attempt']==7 and ab[0]['dma_bytes']==864
    assert all(t['target']==0x18 for t in ab[0]['dmas'])
    assert d['frames'][6]['sha256']==d['frames'][7]['sha256'] and d['frames'][7]['epoch']==1
    d=results['length'];assert not d['passed'] and not any(f['different_pixels'] for f in d['frames'])
    t=next(t for t in d['transactions'] if t['attempt']==7);assert t['outcome']=='halt' and t['dma_bytes']==0
    assert 'host_error:7:226' in d['errors']
    d=results['overrun'];assert not d['passed'] and 'deadline:7' in d['errors'] and 'visible_slot_overwrite:7' in d['errors'] and 'host_error:7:225' in d['errors']
    d=results['selection'];assert not d['passed'] and d['errors'] and all(e.startswith('pixels:') for e in d['errors'])
    assert all(f['different_pixels']==55 for f in d['frames'])
    return dict(candidate='NES-P1-STREAM-002',audit_pass=True,cases=summary,
        notes=['239 displayed rows only; source row 239 remains absent','reset is a cooperative producer cancel before palette/OAM commit, not a physical reset','ROM source timing is not the FPGA/SRAM cart interface'],
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=verify(a.runs)
    with a.out.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PASS: six expected outcomes, raw RGB/ROM hashes, continuous frames, ON/OFF equality and reset/length/overrun/selection assertions')
