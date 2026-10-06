"""Audit raw SNES residency captures, inactive-page DMA and atomic switches.
SPDX-License-Identifier: MIT. Original synthetic fixture only.
"""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snes/video_probe'))
import build_probe
from resident_model import resident_snapshot,working_set_audit,pattern_audit

CASES={'off':128,'on':128,'reset':64,'unannounced':32,'late':32,'stale':64,'owner':64}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify(root):
    summaries={};hashes={}
    for name,count in CASES.items():
        case=root/name;build=case/'build';m=json.loads((build/'manifest.json').read_text());r=json.loads((case/'result.json').read_text())
        assert r['candidate']==m['candidate']=='NES-P1-RESIDENT-004' and r['returncode']==0
        assert sha(build/'stream.sfc')==m['rom_sha256'] and sha(build/'manifest.json')==r['manifest_sha256']
        assert m['pattern_audit']==pattern_audit() and m['working_set']==working_set_audit()
        meta=[list(map(int,s.split('\t'))) for s in (case/'frames.tsv').read_text().splitlines()]
        keys=[list(map(int,s.split('\t'))) for s in (case/'cache.tsv').read_text().splitlines()]
        assert len(meta)==len(keys)==len(r['frames'])==count
        hashes[name]=[];bad_frames=[]
        for i,f in enumerate(r['frames']):
            want=min(i,7) if name in ('unannounced','late') else i-(name=='reset' and i>=8)
            epoch=int(name=='reset' and i>=8)
            assert f['index']==i and f['frame_id']==want and f['epoch']==epoch
            assert meta[i][0]==i and meta[i][3:5]==[want,epoch] and meta[i][-2:]==[256,239]
            assert meta[i][1]==f['emulator_frame'] and (i==0 or meta[i][1]==meta[i-1][1]+1)
            assert meta[i][6]==(229 if name in ('unannounced','late') and i>=8 else 0)
            expected=resident_snapshot(want,name)
            flat=sum(expected['keys'],[])+expected['masks']+expected['sets']+[expected['active_page'],expected['preload_page']]
            assert keys[i]==[i,want,epoch]+flat
            assert r['cache_tags'][i]==dict(index=i,frame_id=want,epoch=epoch,**expected)
            actual=(case/f'frame-{i:03}.rgb').read_bytes();ref=(build/f'expected-{want%32:02}.rgb').read_bytes()
            assert len(actual)==len(ref)==256*239*3
            bad=sum(actual[j:j+3]!=ref[j:j+3] for j in range(0,len(actual),3))
            assert bad==f['different_pixels'] and sha(case/f'frame-{i:03}.rgb')==f['sha256']
            hashes[name].append(f['sha256'])
            if bad:bad_frames.append((i,bad))
        # Reparse raw observation, independent of runner transaction summaries.
        tx=[];cur=None;admission=None;admissions=[];owner_violations=[];switches=[];last_base=4
        names=['value','clock','emulator_frame','line','hclock','display','attempt','epoch','active_slot','pending_slot','lo','hi','target','size_lo','size_hi','bg_page','preload_page','bg_base','ready0','ready1','set0','set1']
        for row in (case/'trace.tsv').read_text().splitlines():
            parts=row.split('\t');kind=parts[0];t=dict(zip(names,map(int,parts[1:])));v=t['value']
            if kind=='brightness':assert not(v&128)
            if kind=='phase' and v==7:
                assert admission is None and cur is None and t['line']<240
                admission=dict(start=t['clock'],attempt=t['attempt'])
            elif kind=='phase' and v==8:
                assert admission is not None and t['line']<240
                admission['duration']=t['clock']-admission['start'];admission['admitted']=True
                admissions.append(admission);admission=None
            elif kind=='phase' and v==1:
                assert cur is None
                rejected=admission is not None
                if rejected:assert name in ('unannounced','late') and t['attempt']==8;admission=None
                else:assert admissions[-1]['attempt']==t['attempt']
                cur=dict(attempt=t['attempt'],start=t['clock'],line=t['line'],hclock=t['hclock'],display=t['display'],dmas=[],phase=1,bases=[],rejected=rejected)
            elif cur and kind=='phase' and v==2:
                assert cur['phase']==1 and cur['dmas']==[544,64];cur['phase']=2
            elif cur and kind=='phase' and v==5:
                assert cur['phase']==2;cur['phase']=5
            elif cur and kind=='bgbase':
                wanted_page=(cur['attempt']//8)%2
                assert cur['phase']==5 and cur['dmas']==[544,64,384,60]
                assert v==4+wanted_page and t['bg_page']==wanted_page
                assert t['ready'+str(wanted_page)]==255 and t['set'+str(wanted_page)]==(cur['attempt']//8)%4
                assert 240<=t['line']<=261
                if v!=last_base:switches.append(cur['attempt'])
                last_base=v;cur['bases'].append(v)
            elif cur and kind=='phase' and v==6:
                assert cur['phase']==5 and len(cur['bases'])==1;cur['phase']=6
            elif kind=='dma' and cur:
                assert admission is None
                size=t['size_lo']+256*t['size_hi'];addr=t['lo']+256*t['hi'];k=len(cur['dmas'])
                page=(cur['attempt']//8)%2;dest=page^1;w=cur['attempt']%8;slot=t['pending_slot']
                expected=[(24,0x3010+slot*0x400,544),(24,0x09c0+slot*0x400,64),(34,None,384),(4,None,60),(24,0x4000+dest*0x1000+w*0x200,1024)][k]
                assert t['target']==expected[0] and size==expected[2] and 240<=t['line']<=261
                if k<2:assert cur['phase']==1 and slot!=t['active_slot']
                elif k<4:assert cur['phase']==5
                else:assert cur['phase']==6 and t['bg_page']==page and t['preload_page']==dest and t['bg_base']==4+page
                bad_owner=k==4 and (addr!=expected[1] or (addr-0x4000)//0x1000==page)
                if bad_owner:
                    assert name=='owner' and cur['attempt']%32==3 and addr==0x4000+page*0x1000+w*0x200
                    owner_violations.append(cur['attempt'])
                else:assert expected[1] is None or addr==expected[1]
                cur['dmas'].append(size)
            elif kind=='dma':
                # Startup forced blank DMA precedes the first admission; no DMA during scanout validation.
                assert not admissions and admission is None and not tx
            elif cur and kind=='phase' and v in (3,4,238):
                if v==3:assert cur['phase']==6 and cur['dmas']==[544,64,384,60,1024]
                elif v==4:assert cur['phase']==2 and not cur['bases'] and cur['attempt']==8 and name=='reset'
                else:assert cur['rejected'] and not cur['dmas']
                duration=t['clock']-cur['start'];margin=(262-cur['line'])*1364-4-cur['hclock']-duration
                assert margin>=0 and 240<=t['line']<=261
                cur.update(outcome={3:'commit',4:'reset_abort',238:'halt'}[v],duration=duration,margin=margin);tx.append(cur);cur=None
        assert cur is None and len(tx)==len(r['transactions'])
        for raw,stored in zip(tx,r['transactions']):
            assert (raw['attempt'],raw['outcome'],sum(raw['dmas']),raw['duration'],raw['margin'])==(stored['attempt'],stored['outcome'],stored['dma_bytes'],stored['duration_master_clocks'],stored['deadline_margin_master_clocks'])
        kinds={e.split(':')[0] for e in r['errors']}
        if name in ('off','on','reset'):
            assert r['passed'] and not kinds and not bad_frames and not owner_violations and len(tx)==count
            assert [t['attempt'] for t in tx if t['outcome']=='reset_abort']==([8] if name=='reset' else [])
            if name=='reset':assert hashes[name][7]==hashes[name][8] and keys[7][3:]==keys[8][3:]
        elif name in ('unannounced','late'):
            assert not r['passed'] and kinds=={'host_error','frame_sequence'} and not bad_frames
            assert len(tx)==9 and tx[-1]['outcome']=='halt' and tx[-1]['attempt']==8
            assert all(h==hashes[name][7] for h in hashes[name][8:])
        else:
            assert not r['passed'] and len(tx)==count and all(t['outcome']=='commit' for t in tx)
            assert kinds==({'pixels'} if name=='stale' else {'pixels','cache_ownership'})
            assert [i for i,_ in bad_frames]==[i for i in range(count) if (8<=i%32<16 if name=='stale' else 3<=i%32<16)]
            assert owner_violations==([] if name=='stale' else [3,35])
        committed=[t['attempt'] for t in tx if t['outcome']=='commit']
        assert switches==[f for f in committed if f>0 and f%8==0]
        summaries[name]=dict(captured_frames=count,normal_pass=r['passed'],expected_outcome_verified=True,
            different_frames=len(bad_frames),different_pixels=sum(n for _,n in bad_frames),bank_set_switches=len(switches),ownership_violations=owner_violations,
            commits=sum(t['outcome']=='commit' for t in tx),reset_aborts=sum(t['outcome']=='reset_abort' for t in tx),halts=sum(t['outcome']=='halt' for t in tx),
            max_payload_bytes=r['max_payload_bytes'],max_vblank_duration_master_clocks=r['max_duration_master_clocks'],min_deadline_margin_master_clocks=r['min_deadline_margin_master_clocks'],
            max_admission_master_clocks=max(a['duration'] for a in admissions),rom_sha256=m['rom_sha256'],result_sha256=sha(case/'result.json'),tool_hashes=r['tool_hashes'])
    assert hashes['off']==hashes['on']
    repeat=None
    if (root/'owner-repeat').exists():
        case=root/'owner-repeat';r=json.loads((case/'result.json').read_text());original=json.loads((root/'owner/result.json').read_text())
        assert r['manifest_sha256']==original['manifest_sha256'] and r['source_hashes']==original['source_hashes'] and r['tool_hashes']==original['tool_hashes']
        assert r['returncode']==0 and not r['passed'] and r['errors']==original['errors']
        assert len(r['frames'])==64
        for i,f in enumerate(r['frames']):
            assert f['sha256']==hashes['owner'][i]==sha(case/f'frame-{i:03}.rgb')
            assert f['frame_id']==i and (i==0 or f['emulator_frame']==r['frames'][i-1]['emulator_frame']+1)
        repeat=dict(frames=64,all_rgb_hashes_identical=True,result_sha256=sha(case/'result.json'))
    return dict(candidate='NES-P1-RESIDENT-004',audit_pass=True,cases=summaries,diagnostic_frames_identical=True,
        working_set=working_set_audit(),pattern_audit=pattern_audit(),ownership_repeat=repeat,source_sha256=sha(__file__),hardware_eligible=False,
        scope='Immutable ROM supplier with eight-frame advance availability; no causal NES/FPGA producer proof',source_height=240,displayed_height=239)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    result=verify(a.runs);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(audit_pass=True,cases=len(result['cases']),switches=result['cases']['off']['bank_set_switches'],max_admission=result['cases']['on']['max_admission_master_clocks'])))
