"""Re-audit raw CHR-cache RGB, DMA phases, keys, and intentional failures.
SPDX-License-Identifier: MIT. No emulator writes or commercial inputs.
"""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snes/video_probe'))
import build_probe
from cache_patterns import pattern_audit,schedule_state

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(root):
    checks=[];summaries={};hashes={}
    for name,count in [('off',128),('on',128),('reset',64),('burst',32),('tag',32),('stale',64),('alias',64)]:
        case=root/name;build=case/'build'
        r=json.loads((case/'result.json').read_text());m=json.loads((build/'manifest.json').read_text())
        assert r['returncode']==0 and m['candidate']==r['candidate']=='NES-P1-CACHE-003'
        assert sha(build/'stream.sfc')==m['rom_sha256'] and sha(build/'manifest.json')==r['manifest_sha256']
        assert m['pattern_audit']==pattern_audit()
        assert len(r['frames'])==count and len(r['cache_tags'])==count
        meta=[list(map(int,line.split('\t'))) for line in (case/'frames.tsv').read_text().splitlines()]
        tags=[list(map(int,line.split('\t'))) for line in (case/'cache.tsv').read_text().splitlines()]
        assert len(meta)==len(tags)==count
        hashes[name]=[];different=[]
        for i,f in enumerate(r['frames']):
            want=min(i,7) if name in ('burst','tag') else i-(name=='reset' and i>=7)
            epoch=int(name=='reset' and i>=7)
            assert f['index']==i and f['frame_id']==want and f['epoch']==epoch
            assert meta[i][0]==i and meta[i][3:5]==[want,epoch] and meta[i][-2:]==[256,239]
            assert i==0 or meta[i][1]==meta[i-1][1]+1
            assert meta[i][1]==f['emulator_frame']
            expected_tags=[list(t) for t in schedule_state(want%32)[0]]
            assert tags[i][:3]==[i,want,epoch] and tags[i][3:]==sum(expected_tags,[])
            assert r['cache_tags'][i]==dict(index=i,frame_id=want,epoch=epoch,tags=expected_tags)
            expected_error=(227 if name=='burst' else 228) if name in ('burst','tag') and i>=8 else 0
            assert meta[i][6]==expected_error
            actual=(case/f'frame-{i:03}.rgb').read_bytes();expected=(build/f'expected-{want%32:02}.rgb').read_bytes()
            assert len(actual)==len(expected)==256*239*3
            bad=sum(actual[j:j+3]!=expected[j:j+3] for j in range(0,len(actual),3))
            assert bad==f['different_pixels'] and sha(case/f'frame-{i:03}.rgb')==f['sha256']
            hashes[name].append(f['sha256'])
            if bad:different.append((i,bad))
        # Parse raw phases afresh; exact DMA order and bounds, including commit-only cache writes.
        trace=[line.split('\t') for line in (case/'trace.tsv').read_text().splitlines()]
        tx=[];cur=None
        for row in trace:
            kind=row[0];v=list(map(int,row[1:]));value,clock,emu,line,hclock,display,attempt,epoch,active,pending,lo,hi,target,sl,sh=v
            if kind=='brightness':assert not(value&128)
            if kind=='phase' and value==1:
                assert cur is None
                cur=dict(attempt=attempt,start=clock,line=line,hclock=hclock,commit=False,staged=False,dmas=[],display=display)
            elif cur and kind=='phase' and value==2:
                assert not cur['commit'] and len(cur['dmas'])==2;cur['staged']=True
            elif cur and kind=='phase' and value==5:
                assert cur['staged'] and not cur['commit'];cur['commit']=True
            elif cur and kind=='dma':
                size=sl+sh*256;addr=lo+hi*256
                assert size>0 and (225 if display==255 else 240)<=line<=261
                k=len(cur['dmas'])
                expected=[(0x18,0x3010+pending*0x400,544),(0x18,0x09c0+pending*0x400,64),(0x18,0x4000+(attempt%8)*0x200,1024),(0x22,None,384),(4,None,60)][k]
                assert target==expected[0] and size==expected[2] and (expected[1] is None or addr==expected[1])
                assert cur['commit']==(k>=2)
                if k<2:assert active!=pending
                cur['dmas'].append(size)
            elif cur and kind=='phase' and value in (3,4,238):
                assert value!=3 or (cur['commit'] and len(cur['dmas'])==5)
                assert value!=4 or (not cur['commit'] and cur['dmas']==[544,64])
                assert value!=238 or not cur['dmas']
                duration=clock-cur['start'];margin=(262-cur['line'])*1364-4-cur['hclock']-duration
                assert margin>=0 and (225 if cur['display']==255 else 240)<=line<=261
                cur.update(outcome={3:'commit',4:'reset_abort',238:'halt'}[value],duration=duration,margin=margin)
                tx.append(cur);cur=None
        assert cur is None and len(tx)==len(r['transactions'])
        for raw,stored in zip(tx,r['transactions']):
            assert (raw['attempt'],raw['outcome'],sum(raw['dmas']),raw['duration'],raw['margin'])==(stored['attempt'],stored['outcome'],stored['dma_bytes'],stored['duration_master_clocks'],stored['deadline_margin_master_clocks'])
        kinds={e.split(':')[0] for e in r['errors']}
        if name in ('off','on','reset'):
            assert r['passed'] and not different and not kinds and len(tx)==count
            if name=='reset':
                assert [t['attempt'] for t in tx if t['outcome']=='reset_abort']==[7]
                assert hashes[name][6]==hashes[name][7] and r['cache_tags'][6]['tags']==r['cache_tags'][7]['tags']
            else:assert all(t['outcome']=='commit' for t in tx)
        elif name in ('burst','tag'):
            assert not r['passed'] and not different and kinds=={'host_error','frame_sequence'}
            assert len(tx)==9 and tx[-1]['outcome']=='halt' and tx[-1]['attempt']==8
            assert all(h==hashes[name][7] for h in hashes[name][8:])
        else:
            assert not r['passed'] and kinds=={'pixels'} and len(tx)==count
            wanted=[i for i in range(count) if (8<=i%32<16 if name=='stale' else i%32<23)]
            assert [i for i,_ in different]==wanted,(name,different)
        summaries[name]=dict(captured_frames=count,normal_pass=r['passed'],expected_outcome_verified=True,
            different_frames=len(different),different_pixels=sum(n for _,n in different),
            max_payload_bytes=r['max_payload_bytes'],max_duration_master_clocks=r['max_duration_master_clocks'],min_deadline_margin_master_clocks=r['min_deadline_margin_master_clocks'],
            commits=sum(t['outcome']=='commit' for t in tx),reset_aborts=sum(t['outcome']=='reset_abort' for t in tx),halts=sum(t['outcome']=='halt' for t in tx),rom_sha256=m['rom_sha256'],result_sha256=sha(case/'result.json'),tool_hashes=r['tool_hashes'])
        checks.append(name)
    assert hashes['off']==hashes['on']
    # All eight pages changing without residency/preload cannot fit, even ignoring CPU work.
    burst_dma_lower_bound_clocks=8192*8
    assert burst_dma_lower_bound_clocks>22*1364
    return dict(candidate='NES-P1-CACHE-003',audit_pass=True,cases=summaries,checked=checks,diagnostic_frames_identical=True,
        pattern_audit=pattern_audit(),simultaneous_eight_page_dma_only_clocks=burst_dma_lower_bound_clocks,
        reference_scope='effective synthetic bank events, not NES PPU/MMC3',source_height=240,displayed_height=239,
        hardware_eligible=False,source_sha256=sha(Path(__file__)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists();result=verify(a.runs)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(audit_pass=result['audit_pass'],cases=len(result['cases']),diagnostic_frames_identical=True)))
