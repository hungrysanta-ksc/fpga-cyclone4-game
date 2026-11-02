# SPDX-License-Identifier: MIT
"""Compare a new consumer at immutable MMC540 PUSH times; preserve both input hashes."""
import argparse,json,shutil
from pathlib import Path
import replay_nes_map527 as replay
from test_nes_map526_schedule import observer
from test_nes_tile532 import tile_observer
from nes_raw506 import sha

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False)
    source=a.trace;a.trace=root/'input';a.trace.mkdir()
    for n in ('packets.jsonl','window.csv'):
        shutil.copyfile(source/n,a.trace/n)
    for g in range(905,958):
        for n in (f'expected-{g}.bin',f'map-{g}.bin',f'frame-{g}.rgb'):
            shutil.copyfile(source/n,a.trace/n)
    shutil.copyfile(a.client/'sink165.sfc',a.trace/'client.sfc')
    a.out=root/'run';a.frames=53
    labels=json.loads((a.client/'labels.json').read_text())
    limit=str(json.loads((a.client/'build.json').read_text())['map_chunk_B'])
    replay.observer=lambda s,l:tile_observer(observer(s,l),l,limit)
    def compare(old,new):
        def acks(rows):return [r for r in rows if r['op']=='3' and r['event']=='ack']
        before,after=acks(old),acks(new)
        assert len(before)==len(after)==53
        return dict(fixed_arrival_comparison=True,last_ACK_delta_clocks=int(after[-1]['clock'])-int(before[-1]['clock']))
    # The independent replay observer already contains map and tile instrumentation.
    from test_nes_quiet528 import seal_trace
    from nes_raw506 import once
    def edit(s):
        s=seal_trace(s);return once(s,' or (pw(8)~=952 and pw(8)~=954)','')
    replay.run(a,edit_script=edit,compare_trace=compare)
    (root/'pins.json').write_text(json.dumps(dict(source_client=sha(source/'client.sfc'),candidate_client=sha(a.client/'sink165.sfc'),packets=sha(source/'packets.jsonl'),source_trace=sha(source/'window.csv')),indent=2)+'\n')
