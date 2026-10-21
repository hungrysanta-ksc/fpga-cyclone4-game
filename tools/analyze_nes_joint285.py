# SPDX-License-Identifier: MIT
"""Checked-input planning dependencies, retimed planner cost and whole area budget."""
import argparse,csv,json,re,hashlib
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(path):pins[str(path)]=sha(path);return path
    def js(path):return json.loads(pin(path).read_text(encoding='utf-8-sig'))
    def csvrows(path):return list(csv.DictReader(pin(path).open()))
    old=js(ROOT/'analysis/joint284-verification.json');arm=js(b/'arm04/result.json');helpers=js(b/'arm05/result.json');prefix=js(b/'prefix01/result.json');lease=js(b/'lease02/result.json');reads=js(b/'reads03/result.json');complete=js(b/'arm06/result.json')
    assert all(r['passed'] for r in (old,arm,helpers,prefix,lease,reads,complete))
    assert len(arm['frames'])==len(prefix['frames'])==71 and lease['checks']==8
    ar={r['frame']:r for r in arm['frames']};pr={r['frame']:r for r in prefix['frames']}
    assert complete['metadata_bytes_per_frame']==8570 and len(complete['frames'])==71
    for r in helpers['frames']+complete['frames']:
        for k,v in ar[r['frame']].items():assert r[k]==v,(r['frame'],k)
    assert helpers['source_hash']==arm['source_hash']==sha(pin(ROOT/'tools/nes_planner285.c'))
    assert helpers['script_hash']==sha(pin(b/'arm05/probe_nes_planner285.py'))
    assert complete['script_hash']==sha(pin(ROOT/'tools/probe_nes_planner285.py'))
    assert complete['source_hash']==arm['source_hash']
    assert arm['script_hash']==sha(pin(b/'arm04/probe_nes_planner285.py'))
    assert prefix['script_sha256']==sha(pin(ROOT/'tools/probe_nes_prefix285.py'))
    assert lease['script_sha256']==sha(pin(ROOT/'tools/guard_nes_early285.py'))
    assert reads['script_sha256']==sha(pin(ROOT/'tools/probe_nes_plan_reads285.py'))
    assert reads['input_hashes']['planner.elf']==arm['ELF_sha256']
    assert all(r['raw_bytes_before_first_plan']==512 and not r['used_for_timing'] for r in reads['frames'])
    for r in (arm,helpers,prefix,complete):
        for name,h in r['input_hashes'].items():assert sha(pin(Path(name)))==h,name
    for name,h in lease['rtl_hashes'].items():assert sha(pin(BASE/'probes/nes-joint284/test05'/name))==h
    prior={int(r['frame']):r for r in csvrows(ROOT/'analysis/joint284-costs.csv')}
    window_prior={r['frame']:r for r in old['restricted_ROM']}
    schedules={}
    for tag,expected,older in [('test01',71,prior),('window01',3,window_prior)]:
        folder=b/tag;result=js(folder/'result.json');assert result['passed'] and result['frames']==expected
        assert result['input_hashes']['probe_nes_schedule285.py']==sha(pin(ROOT/'tools/probe_nes_schedule285.py'))
        for n,h in result['rtl_hashes'].items():
            assert sha(pin(folder/n))==h==sha(pin(BASE/'probes/nes-joint284/test05'/n)),n
        events=list(csv.reader(pin(folder/'joint-events.csv').open()));source={int(r['frame']):r for r in csvrows(folder/'cycles.csv')};rows=[];prev=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284'];end=[e for e in es if e[0]=='armdone284'];assert len(end)==1
            pc=next(e for e in es if e[0]=='planner285');cc=next(e for e in es if e[0]=='commit285')
            assert int(pc[2])==ar[f]['begin_instructions']+ar[f]['plan_instructions'];assert int(cc[2])==ar[f]['commit_instructions']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,prev)];prev=counters
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out;before=float(older[f]['diagnostic_serial_ms'])
            planner=(int(pc[2])+int(cc[2]))/84000
            rows.append(dict(frame=f,source_ms=src,output_including_planner_ms=out,diagnostic_serial_ms=total,prior284_ms=before,
                delta284_ms=total-before,planner_commit_CPI1_ms=planner,frozen_additive_ms=before+planner,
                retimed_minus_frozen_ms=total-before-planner,margin_ms=1000/60-total,absolute_end_ms=int(event[2])/1e9,
                E2=sum(int(e[2])==226 for e in spi),E8=sum(int(e[2])==232 for e in spi),E9=sum(int(e[2])==233 for e in spi),
                SPI_bytes=sum(int(e[3]) for e in spi),ARM_output_all_boundary_instructions=sum(int(e[5]) for e in spi)+sum(int(e[4]) for e in wait)+int(end[0][3]),
                exception_cycles=sum(int(e[6]) for e in spi)+sum(int(e[5]) for e in wait)+int(end[0][4]),
                IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
            baseline=BASE/'probes/nes-joint284'/('test04' if tag=='test01' else 'window01')
            now=js(folder/f'arm{f}.json');then=js(baseline/f'arm{f}.json')
            for op in (225,233):
                select=lambda r:[t['tx'] for t in r['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
        assert len(rows)==expected;schedules[tag]=rows
    warm=schedules['test01'][2:];worst=max(warm,key=lambda r:r['diagnostic_serial_ms'])
    # Reuse the matching final whole Lite report; no compile of unchanged RTL.
    board=BASE/'probes/nes-joint284/board02';map_result=js(board/'result.json');assert map_result['passed']
    rpt=pin(board/'output_files/board.map.rpt').read_text();own={}
    for line in rpt.splitlines():
        fields=[v.strip() for v in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    assert sum(own.values())==17765
    boundary=old['extended_control_boundary'];assert boundary['current']==4809 and boundary['budget']==2452
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_spi270.sv'):
        actual=pin(board/n).read_bytes();sim=pin(b/'test01'/n).read_bytes()
        if n=='nes_mux260.sv':
            # Existing board-only port exports a state observed hierarchically
            # by the simulator. Account for the exact glue, not arbitrary RTL.
            anchor=b' output wire tile_closed267,\n'
            assignment=b' reg tiles_closed;assign tile_closed267=tiles_closed;'
            assert actual.count(anchor)==actual.count(assignment)==1
            actual=actual.replace(anchor,b'').replace(assignment,b' reg tiles_closed;')
        assert actual==sim,n
    regions=old['regions'];retained=regions['queue']+regions['plan']+boundary['common_SPI'];hv=regions['host']+regions['validator']
    area=dict(whole_MAP=old['whole_MAP'],new_MAP=False,RTL_changed=False,deficit=2357,boundary=4809,budget=2452,reserve_target=2324,
        retained_queue_plan_SPI=retained,host_validator=hv,host_validator_budget=2452-retained,host_validator_reserve_target=2324-retained,
        required_host_validator_reduction=2357,required_host_validator_reduction_percent=2357/hv*100,
        all_queue_plan_SPI_zero_still_short=2357-retained,new_replacement_area=None,proven_area_saving=0)
    candidates=[
        dict(name='unchanged_early_E9',status='rejected_by_actual_ARM_and_RTL',early_plan=False,area_saving=0,time_saving=None),
        dict(name='sealed_bank_pending_until_COMMITTED',status='design_only',early_ROM=False,new_area=None,time_saving=None,
             reason='Must defer mailbox decode without fault, preserve generation/epoch and two-bank STOP ownership. Final geometry block leaves no earlier checked window in 68/71 frames.'),
        dict(name='geometry_first_speculative_plan_and_ROM_prefetch',status='not_implemented',new_area=None,time_saving=None,
             reason='Needs reordered geometry validation, split dirty/raw scratch lifetime, bounded speculative lease, commit/STOP drain and shared ROM/SPI arbitration.'),
        dict(name='joint_host_validator_owner',status='budget_and_retained_checks_fixed_not_implemented',new_area=None,time_saving=None,
             reason='Retain original-byte CRC, ordered reads/ACK and provisional CRC distinct from committed receipt; asynchronous SNES reads and SPI enqueue can coexist. No free single cursor or single CRC context.')]
    result=dict(passed=True,stage=285,selected=['arm04','arm05','arm06','prefix01','lease02','reads03','test01','window01'],
        planner=arm['frames'],planner_memory_helper_sensitivity=complete['frames'],metadata_bytes_per_frame=8570,early_ARM_rejects=arm['early_rejects'],
        raw_dependency_observation=reads['frames'],replacement_owners=js(ROOT/'docs/nes-boundary285-owners.json'),
        geometry_in_final_block=sum(r['tail_blocks']==0 for r in pr.values()),geometry_tail_frames=[r for r in pr.values() if r['tail_blocks']],
        prefix=prefix['frames'],late_stream_CRC_rejects=prefix['late_checksum_rejects'],lease_guards=8,
        normal=schedules['test01'],warm_max=worst,warm_over=[r['frame'] for r in warm if r['margin_ms']<0],restricted_ROM=schedules['window01'],
        area=area,candidates=candidates,board_glue='Existing tile_closed267 output exposes tiles_closed; exact port/assign delta only, all other selected RTL bytes equal.',full_path_ms=None,P2_selected=False,FIT=False,STA=False,physical=False,
        limits=['Actual unchanged M4 planner with explicit local byte-loop memory helpers; source fixtures and trace output are diagnostic storage, not target RAM.',
          'Retimed serial candidate replays planner instructions after input COMMITTED; output ARM/EXTI/WFI and ROM RTL remain live. No planner IRQ preemption or live source/planner integration.',
          '24-cycle EXTI entry/exit allocation and CPI1/84MHz are not measured hardware WCET. Source semantics expansion/fullRUN and complete program ROM remain open.',
          'CPU279 trace reused, no new live65816/activeVBlank/physical60fps. STOP/finalACK baseline RTL unchanged; new lease/CRC/early ARM rejection guards supplement prior evidence.',
          'No new host/validator replacement or Quartus compile: reuse final284 whole Lite MAP by exact source hash, savings zero; candidates have null implementation costs.'],
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('costs.csv',schedules['test01']),('restricted.csv',schedules['window01'])]:
        with (d/name).open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','warm_max','restricted_ROM','area','geometry_in_final_block')}))


if __name__=='__main__':main()
