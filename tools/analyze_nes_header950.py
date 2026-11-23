from pathlib import Path
import sys,json
import hashlib
from analyze_nes_deadline947 import directory,ready_bytes,report
from analyze_nes_input949 import timing
from read_nes_supply905 import decode
from nes_header950 import work

def analyze(temp,modes):
    base=json.loads((Path(__file__).resolve().parents[1]/'analysis/input949-results.json').read_bytes())
    rows=report(temp,modes,prefix='950',work=work)
    out=dict(master_Hz=rows['master_Hz'],consumer=rows['ROM'],board='914I',physical=False,
             cases={},safety=rows['recovery'])
    for case,group in rows['cases'].items():
        phase=int(case[-1]);cache=case[:-1]
        control=base['cases'][case]['held_stage']
        old=base['controls'][case]['held935']
        ref=directory(temp,phase,'949held_stage',cache)
        prior=ready_bytes(ref)
        keys=[(910,1,i) for i in range(80*32,89*32)]
        for m in modes:
            row=group[m];folder=directory(temp,phase,'950'+m,cache)
            t=timing(folder); times=ready_bytes(folder)
            hdr=json.loads((folder/'headers950.json').read_bytes())
            h=next(r for r in hdr if r['display']==909)
            assert h['D2']==t['blocks'][-1][3] and h['read']>h['D2']
            arm_events=json.loads((folder/'events.json').read_bytes())
            pages=decode(folder/'records.bin',925)
            descriptors={r['generation']:r for r in pages['rows']}
            jobs=[json.loads(l) for l in (folder/'producer.jsonl').read_text().splitlines()]
            for page in hdr:
                g=page['display']
                d2=page['D2']; start=page['read']
                rearm=next(e for e in arm_events if e.get('opcode')=='0xea' and e['generation']==g)
                decide=next(e for e in arm_events if e.get('opcode')=='0xd3' and e['input_generation']==g+1)
                e8=next(e for e in arm_events if e.get('opcode')=='0xe8' and e['start']>=rearm['clock'])
                next_plan=next(e for e in arm_events if e.get('opcode')=='0xe9' and e['generation']==g+1)
                assert rearm['clock']<=e8['start']<e8['clock']<=decide['start']<d2<start<next_plan['start']
                assert not descriptors[g].get('invalid') and descriptors[g]['last_token']>0
                page['token']=descriptors[g]['last_token']
                assert page['token']==next(j['token'] for j in reversed(jobs) if j['generation']==g)
            assert [descriptors[909]['last_offset'],descriptors[909]['last_bytes']]==t['tiles'][-1]
            eq=t['E9']==control['timing']['E9'] and t['tiles']==control['timing']['tiles']
            lag=max(times[k][1]-prior[k][1] for k in keys)
            result=dict(Flash=row['Flash'],firmware=row['sha256'],capture_line_margin=-row['D2_minus_target911'],
                capture911=row['stages'][911]['capture'],
                final_D2=h['D2'],header_after_D2=h['read']-h['D2'],same_909_groups=eq,
                advance_D2_vs949=control['timing']['blocks'][-1][3]-h['D2'],
                late_288_clocks=lag,input910=t['returned_before_show'],input909=row['stages'][909]['data_blocks_before_show'],
                preDMA=row['prior_blank_B'],coverage=row['exact_preDMA'],tail_grant=row['tail_grant'],
                current_six=row['total'],gaps=row['gaps'],final_ACK=row['final_ACK'],
                ACK_advance_vs935=old['ACK']-row['final_ACK'],ACK_advance_vs949=control['ACK']-row['final_ACK'],
                headers=hdr,late_vs935=row['late_destinations'])
            out['cases'].setdefault(case,{})[m]=result
            print(case,m,*(result[k] for k in ('Flash','capture_line_margin','late_288_clocks','input910','preDMA','current_six','ACK_advance_vs935','same_909_groups')),flush=True)
    for m in modes:
        scenario=[g[m] for g in out['cases'].values()]
        good=all(r['capture_line_margin']>=0 and r['same_909_groups'] and
                 r['late_288_clocks']<=0 and r['input910']==17 and r['preDMA']==496 and
                 r['coverage'] and r['gaps'][-2]==2 and r['tail_grant'] and (limit==13 or r['input909']==17) and r['current_six']==limit and r['ACK_advance_vs935']>0 and
                 r['Flash']<=212992 for r,limit in zip(scenario,(13,13,14,14)))
        out.setdefault('schedule_pass',{})[m]=good
    for m in modes:
        proof=work(m)/'identity950.json'
        if proof.is_file():
            out.setdefault('identity_tests',{})[m]=json.loads(proof.read_bytes())
    board=temp/'nes-port914I/nes-trial816-board914'
    wiring={'nes_sink_spi165.sv':('tr_gen=ack_work[79:64]',),
            'nes_screen_status151.sv':('.token(token903),.generation(tr_gen)',),
            'nes_direct206.sv':('token903=consume_token',),
            'nes_bulk_control194.sv':('consume_token<=staged','staged[ap[1:0]*8+:8]<=dp'),
            'nes_supply905.sv':('2:reply=generation[7:0]','12:reply=token[7:0]')}
    out['board_identity_sources']={}
    for name,signals in wiring.items():
        raw=(board/name).read_bytes()
        assert all(x.encode() in raw for x in signals)
        out['board_identity_sources'][name]=hashlib.sha256(raw).hexdigest()
    out['validated']=[m for m in modes if out['schedule_pass'][m] and
                      m in out['safety'] and m in out.get('identity_tests',{})]
    if 'bound' in modes and 'bound' in out['validated']:
        assert out['identity_tests']['bound']['unexpected_chunk_tested']
        out['selected']='bound'
    return out

if __name__=='__main__':
    temp,path,*modes=sys.argv[1:]
    Path(path).write_bytes((json.dumps(analyze(Path(temp),modes),indent=2)+'\n').encode())
