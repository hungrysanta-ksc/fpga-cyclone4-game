# Finite packet ownership and deadline model. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,math,struct
from verify_nes_video_workloads import read_case
from build_nes_fine_scroll import fine_coord
CANDIDATE='NES-R2-PACKET-PACING-026'
SAMPLES={'fine_x':'local-fine-scroll-022','sprite':'local-sprite-replay-023',
         'split':'local-bank-patch-024','banks32':'local-chr-residency-025'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ceildiv(a,b):return (a+b-1)//b
def schedule(*,frames=60000,source_periods=(357364,357368),consumer_periods=(357364,357368),
             release_offset=326984,packet_sizes=(2328,),duration=22788,
             blank_offset=327360,guard=4,poll=112,phase=0,lag=0,
             encode_ticks=1024,clocks_per_byte=2,cdc_ticks=8,ppm=0,slots=2,slot_bytes=3072):
    # All scenario clocks are consumer ticks. Positive ppm makes the producer faster.
    assert frames>0 and slots>0 and lag>=0 and phase>=0
    assert all(p>0 for p in source_periods+consumer_periods)
    assert 0<=release_offset<min(source_periods) and 0<=blank_offset<min(consumer_periods)
    assert min(packet_sizes)>0 and min(duration,clocks_per_byte)>0
    assert max(packet_sizes)<=slot_bytes,'packet exceeds slot capacity'
    assert min(guard,poll,encode_ticks,cdc_ticks)>=0 and ppm>-1000000
    consumer=[0]
    for i in range(frames+lag):consumer.append(consumer[-1]+consumer_periods[i%len(consumer_periods)])
    source=0;link_free=0;previous_end=0;records=[];failures=[];events=[]
    for i in range(frames):
        release=phase+ceildiv((source+release_offset)*1000000,1000000+ppm)
        size=packet_sizes[i%len(packet_sizes)]
        encoded=release+encode_ticks
        transfer_start=max(encoded,link_free);transfer_end=transfer_start+size*clocks_per_byte
        link_free=transfer_end;ready=transfer_end+cdc_ticks
        blank=consumer[i+lag]+blank_offset
        start=max(blank+poll,ready,previous_end);end=start+duration
        deadline=consumer[i+lag+1]-guard
        item=dict(frame=i+1,release=release,encoded=encoded,transfer_start=transfer_start,
                  transfer_end=transfer_end,ready=ready,consume_start=start,consume_end=end,
                  deadline=deadline,margin=deadline-end,packet_bytes=size)
        records.append(item);previous_end=end
        if end>deadline:failures.append(dict(kind='deadline',time=deadline,frame=i+1,late_ticks=end-deadline))
        # A slot is claimed at production release, and freed only after consumption completes.
        events.extend([(release,1,i+1),(end,0,i+1)])
        source+=source_periods[i%len(source_periods)]
    live=set();peak=0;peak_frame=None
    for t,kind,frame in sorted(events):
        if kind==0:
            assert frame in live;live.remove(frame)
        else:
            live.add(frame)
            if len(live)>peak:peak=len(live);peak_frame=frame
            if len(live)>slots:failures.append(dict(kind='overflow',time=t,frame=frame,required_slots=len(live)))
    first=min(failures,key=lambda v:(v['time'],v['frame'],v['kind'])) if failures else None
    # After first violation later predictions have no execution meaning.
    checked=[x for x in records if first is None or x['consume_end']<=first['time']]
    endtime=first['time'] if first else max(x['consume_end'] for x in records)
    occupancy=0;peak_before=0
    for t,kind,frame in sorted(events):
        if t>endtime:break
        occupancy+=1 if kind else -1;peak_before=max(peak_before,occupancy)
    return dict(pass_without_drop_repeat_or_stall=first is None,first_violation=first,
                completed_before_failure=len(checked),frames_requested=frames,
                peak_owned_slots_through_first_violation=peak_before,
                min_margin_completed=min((x['margin'] for x in checked),default=None),
                max_release_to_commit_ticks=max((x['consume_end']-x['release'] for x in checked),default=None),
                parameters=dict(phase=phase,lag=lag,encode_ticks=encode_ticks,clocks_per_byte=clocks_per_byte,
                                cdc_ticks=cdc_ticks,ppm=ppm,slots=slots,slot_bytes=slot_bytes,duration=duration,poll=poll),
                first_frames=records[:4],last_valid=checked[-1] if checked else None)
def evidence(repo):
    workloads=repo/'analysis/local-video-workloads-021';out={}
    for case,folder in SAMPLES.items():
        frames,bg,_,_,_=read_case(workloads,case)
        run=repo/'analysis'/folder/'top';result=json.loads((run/'capture/result.json').read_text())
        anchors=[];release_offsets=[];sizes=[];records=[]
        # Reparse recorded transaction markers rather than infer a frame clock from startup.
        artifact_names={'fine_x':'fine-scroll','sprite':'sprite-replay','split':'bank-patch','banks32':'chr-residency'}
        artifact=repo/'analysis'/(artifact_names[case]+'-artifacts.json')
        manifest=json.loads(artifact.read_text())
        pinned={x['path']:x for group in ('sources','status_files','input_evidence','evidence') for x in manifest[group]}
        needed=[run/'capture'/n for n in ('frames.tsv','trace.tsv','result.json')]
        needed += [run/'build'/f'packet-{i}.bin' for i in range(1,5)]
        for path in needed:
            entry=pinned[path.relative_to(repo).as_posix()]
            assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256']
        tx=[];begin=None
        for line in (run/'capture/trace.tsv').read_text().splitlines():
            kind,*v=line.split()
            if kind!='phase':continue
            v=list(map(int,v))
            if v[0]==1:assert begin is None;begin=v
            elif v[0]==3:
                assert begin is not None
                tx.append((begin[1],begin[3],begin[4],v[1]-begin[1]));begin=None
        assert begin is None and tx==[(t['start'],t['line'],t['hclock'],t['duration_master_clocks']) for t in result['transactions']]
        captures=[list(map(int,line.split())) for line in (run/'capture/frames.tsv').read_text().splitlines()]
        observed_snes=[b[2]-a[2] for a,b in zip(captures,captures[1:])]
        for i,info in enumerate(frames,1):
            seq=[e for e in bg if e['frame']==info['frame']]
            anchor=next(e['tick']-20 for e in seq if e['line']==0 and e['dot']==5)
            release=max(e['tick'] for e in seq if fine_coord(e['line'],e['dot']) is not None)
            packet=(run/'build'/f'packet-{i}.bin').read_bytes()
            assert struct.unpack_from('<I',packet,12)[0]==release
            anchors.append(anchor);release_offsets.append(release-anchor);sizes.append(len(packet))
            records.append(dict(source_frame=info['frame'],anchor=anchor,release=release,
                                packet_bytes=len(packet),packet_sha256=sha(run/'build'/f'packet-{i}.bin')))
        observed_nes=[b-a for a,b in zip(anchors,anchors[1:])]
        assert observed_nes==[357364,357368,357364]
        assert set(observed_snes)=={357364,357368} and release_offsets==[326984]*4
        assert result['normal_pass'] and all(t['outcome']=='commit' for t in result['transactions'])
        out[case]=dict(records=records,observed_nes_frame_deltas=observed_nes,
                       observed_snes_frame_deltas=observed_snes,
                       release_offset=326984,packet_bytes=max(sizes),
                       consumer_duration=max(t['duration_master_clocks'] for t in result['transactions']),
                       max_poll_hclock=max(t['hclock'] for t in result['transactions']),
                       raw_result_sha256=sha(run/'capture/result.json'),artifact_manifest_sha256=sha(artifact))
    return out
def analyze(repo):
    inputs=evidence(repo)
    models={}
    for case,e in inputs.items():
        args=dict(packet_sizes=(e['packet_bytes'],),duration=e['consumer_duration'])
        models[case]={}
        for name,kw in [('aligned_2clocks',{}),('aligned_4clocks',dict(clocks_per_byte=4)),
                        ('one_frame_lag',dict(lag=1)),('one_slot_lag',dict(lag=1,slots=1)),
                        ('phase_half',dict(phase=178684,lag=1)),
                        ('phase_last',dict(phase=357363,lag=1))]:
            models[case][name]=schedule(frames=16,**args,**kw)
    worst=inputs['split'];args=dict(packet_sizes=(worst['packet_bytes'],),duration=worst['consumer_duration'])
    # One-line phase grid plus endpoints. This is sampled, not a proof of every continuous phase.
    sweep=[]
    for phase in sorted(set(list(range(0,357364,1364))+[357363])):
        for lag,slots in ((0,2),(1,2),(2,2),(2,3)):
            r=schedule(frames=16,phase=phase,lag=lag,slots=slots,**args)
            sweep.append(dict(phase=phase,lag=lag,slots=slots,passed=r['pass_without_drop_repeat_or_stall'],
                              violation=r['first_violation']))
    drift={}
    for ppm in (-1000,-100,0,100,1000):
        drift[str(ppm)]=schedule(phase=0,lag=1,slots=2,ppm=ppm,**args)
    budgets={}
    for case,e in inputs.items():
        # Aligned phase only, conservative short-frame deadline and observed maximum consumer duration.
        total=357364-4-e['release_offset']-e['consumer_duration']
        budgets[case]=dict(max_post_fetch_production_delivery_ticks=total,
                          after_encode1024_cdc8_ticks=total-1032,
                          largest_integer_clocks_per_byte=(total-1032)//e['packet_bytes'])
    return dict(candidate=CANDIDATE,kind='offline_parameterized_model_not_new_emulator_or_RTL_run',
                input_evidence=inputs,scenarios=models,phase_sweep=sweep,drift_scenarios=drift,
                aligned_budgets=budgets,model_sha256=sha(__file__),
                assumptions=dict(repeated_timing_only=True,content_repetition_validated=False,
                    source_frame_periods=[357364,357368],consumer_frame_periods=[357364,357368],
                    phase_clock_calibration_measured=False,encoder1024_and_cdc8_are_assumptions=True,
                    link2or4_clocks_per_byte_are_assumptions=True,source_and_consumer_period_extrapolation=True,
                    source_scratch_excluded=True,slots_claimed_at_last_fetch_not_frame_start=True,
                    consumer_wait_until_ready_not_implemented=True,consumer_code_duration_after_wait_not_remeasured=True,
                    slot_bytes_at_least2328=True,finite_60000_frame_drift_horizon=True,
                    hardware_ppm_unknown=True,queue_depth_not_adopted=True,
                    backpressure_stall_drop_repeat_speed_change_not_used=True),
                scope='Timed packet ownership lower model;complete packet after lastfetch,serial link,ready visibility,consume-to-commit release. Full frame producer scratch,actual CDC/front-end/renderer combinations not implemented.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists()
    result=analyze(Path(__file__).resolve().parents[1])
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=CANDIDATE,budgets=result['aligned_budgets'],
          drift={k:{q:v[q] for q in ('pass_without_drop_repeat_or_stall','first_violation')} for k,v in result['drift_scenarios'].items()}),indent=2))
