# SPDX-License-Identifier: MIT
"""Join the reader differential, repeated continuous schedule and full-board STA."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from analyze_nes_transfer512 import fpga
from verify_nes_trial533 import timing
from nes_raw506 import sha


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def board(folder):
    rows,worst,ucp=timing(folder)
    with (folder/'owner562-paths.tsv').open() as f:
        paths=list(csv.DictReader(f,delimiter='\t'))
    return dict(fit=fpga(folder),worst=worst,rows=rows,unconstrained=ucp,paths=paths,
                SOF=sha(folder/'output_files/board.sof'),STA=sha(folder/'output_files/board.sta.summary'))


def read_latency(path,n):
    # Two scrub-completion reads and an intentionally canceled request precede
    # the trace. Pair the remaining events by time, address and order.
    events=[line.split() for line in path.read_text().splitlines()]
    assert [e[0] for e in events[:5]]==['ACCEPT562','REPLY562','ACCEPT562','ACCEPT562','REPLY562']
    reads=events[5:]
    assert len(reads)==2*n
    ps=[]
    for accept,reply in zip(reads[::2],reads[1::2]):
        assert accept[0]=='ACCEPT562' and reply[0]=='REPLY562' and accept[3]==reply[3]
        ps.append(int(reply[2])-int(accept[2]))
    return dict(min_ps=min(ps),max_ps=max(ps),sum_ps=sum(ps),reads=n)


def analyze(a):
    root=Path(__file__).resolve().parents[1]
    old=read(root/'analysis/close561-verification.json')
    inputs=read(root/'analysis/trial558-verification.json')['inputs']
    changed=sorted(n for n in inputs if sha(a.board/n)!=sha(a.previous/n))
    assert changed==['nes_live_joint.sv','nes_rom_boot.sv','nes_rom_physical.sv']
    boards={k:board(d) for k,d in [('MMC558',a.physical),('561',a.previous),('562',a.board)]}
    assert boards['561']['SOF']==old['boards']['candidate']['sof']
    for k in ('561','562'):
        assert boards[k]['unconstrained']==boards['MMC558']['unconstrained']
    assert sum(r['cut']=='loader_to_request' for r in boards['561']['paths'])==3
    assert sum(r['cut']=='scrub_to_memory_reset' for r in boards['561']['paths'])==3
    assert not any(r['cut'] in ('loader_to_request','scrub_to_memory_reset') for r in boards['562']['paths'])
    initial=boards['MMC558']['rows'];final=boards['562']['rows']
    assert set(initial)==set(final)
    bad={k:[initial[k],v] for k,v in final.items() if v[0]<min(initial[k][0],0)}
    fit=boards['562']['fit']
    local_pass=all(fit[v+'_'+check+'_ns']>=0 for v in ('implementation','nominal') for check in ('setup','hold'))
    bus=read(a.rtl/'result.json')
    phases=[]
    for i in (1,2):
        previous=old['phases'][i-1]
        ref=a.traces/f'nes-close561-run{i}';trial=a.traces/f'nes-owner562-run{i}'
        for n,h in previous['early']['pins'].items():
            assert sha(ref/n)==sha(trial/n)==h
        pixels=[sha(trial/f'frame-{g}.rgb') for g in range(905,958)]
        assert pixels==[sha(ref/f'frame-{g}.rgb') for g in range(905,958)]
        x=bus[f'new{i}'];assert x==bus[f'ref{i}'] and x['reads']==480 and x['events']==965
        stimulus=(root/'tests/nes-functional'/f'owner562-reads{i}.txt').read_text(encoding='ascii')
        latencies=[]
        for design in ('ref','new'):
            path=a.rtl/design/f'bus{i}.txt'
            assert sha(path)==x['bus']
            applied=a.rtl/design/f'reads{i}.txt'
            assert sha(applied)==x['input'] and applied.read_text(encoding='ascii')==stimulus
            latencies.append(read_latency(path,x['reads']))
        assert latencies[0]==latencies[1]
        assert previous['timing_gate']
        phases.append(dict(start=read(trial/'joint.json')['parameters']['start'],pins=previous['early']['pins'],
            RGB53=hashlib.sha256(''.join(pixels).encode('ascii')).hexdigest(),bus=x,reader_latency=latencies[1],
            stimulus_LF_SHA256=hashlib.sha256(stimulus.encode('ascii')).hexdigest(),
            dense_VB=previous['early']['dense_VB'],dense_ms=previous['early']['dense_ms'],
            last_ACK=previous['early']['last_ACK'],vs_MMC558=previous['delta'],
            waits=previous['early']['waits'],wait957=previous['early']['waits957']))
    return dict(changed=changed,source_SHA256={n:sha(a.board/n) for n in changed},boards=boards,
                phases=phases,regressed_negative_STA_rows=bad,related_STA_pass=local_pass,trial_gate=local_pass and not bad,
                scope='Boot RTL and continuous M4/Mesen schedule are separate executions. Same routed device, seed and constraints.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('physical','previous','board','traces','rtl','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
