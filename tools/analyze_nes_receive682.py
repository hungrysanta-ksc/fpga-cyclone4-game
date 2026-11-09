"""Pin checked geometry receive ownership and two-phase end-to-end outcomes."""
import argparse,json
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_output664 import trace
from analyze_nes_bg674 import tile_image,preparation
from analyze_nes_frontier536 import contents
from analyze_nes_progress680 import grants
from analyze_nes_idle676 import end_timing
from analyze_nes_handoff678 import input_credit
from analyze_nes_late681 import plan_frontier,credit_frontier

def receive(folder):
    ev=read(folder/'events.json');j=read(folder/'joint.json');old=j['frames'][50]['ACK_masterclock']
    assert j['frames'][50]['generation']==955
    rows=[]
    for e in ev:
        if e['event']!='input682_return':continue
        b=e['begin'];delta=(e['next_token']-b['next_token'])&65535
        assert delta<=1 and e['passed']==1
        if b['reason']==2 and b['progress']:assert delta==0
        if delta:
            assert b['prefetch_left'] or b['receiver_state']==4
            assert e['prefetch_left']==(7 if b['receiver_state']==4 else b['prefetch_left'])-1
        if e['input_generation']!=956 or not delta:continue
        spi=[q for q in ev if q['event']=='SPI' and b['clock']<=q['start']<e['clock']]
        assert [q['opcode'] for q in spi] in (['0xd0','0xd1','0xd2','0xd0'],['0xd1','0xd2','0xd0'])
        assert spi[-1]['opcode']=='0xd0'
        rows.append(dict(reason=b['reason'],begin=b['clock'],returned=e['clock'],D0_response=spi[-1]['clock'],
            token=e['next_token'],left=e['prefetch_left'],elapsed_ms=ms(e['clock']-b['clock']),
            SPI=[{k:q[k] for k in ('opcode','start','clock')} for q in spi]))
    return dict(previous_ACK=old,checked_blocks_before_ACK=sum(r['returned']<=old for r in rows),
        D0_responses_before_ACK=sum(r['D0_response']<=old for r in rows),rows=rows)

def receive_batch(folder):
    ev=read(folder/'events.json');old=read(folder/'joint.json')['frames'][50]['ACK_masterclock'];rows=[];bursts=[]
    for e in ev:
        if e['event']=='input682_return':
            b=e['begin'];n=(e['next_token']-b['next_token'])&65535
            assert e['passed']==1 and n<=7
            if b['reason']!=2:assert n<=1
            if n:assert e['prefetch_left']==(7 if b['receiver_state']==4 else b['prefetch_left'])-n
            if n>1:bursts.append(dict(generation=e['generation'],reason=b['reason'],blocks=n,begin=b['clock'],returned=e['clock']))
        if e['event']!='input682_poll_return' or e['input_generation']!=956:continue
        b=e['begin'];n=(e['next_token']-b['next_token'])&65535
        assert e['passed']==1 and n<=1
        if not n:continue
        spi=[q for q in ev if q['event']=='SPI' and b['clock']<=q['start']<e['clock']]
        assert [q['opcode'] for q in spi] in (['0xd0','0xd1','0xd2','0xd0'],['0xd1','0xd2','0xd0'])
        rows.append(dict(begin=b['clock'],returned=e['clock'],D0_response=spi[-1]['clock'],token=e['next_token'],left=e['prefetch_left'],
            elapsed_ms=ms(e['clock']-b['clock']),SPI=[{k:q[k] for k in ('opcode','start','clock')} for q in spi]))
    assert len(rows)>=7;rows=rows[:7]
    return dict(previous_ACK=old,checked_blocks_before_ACK=sum(r['returned']<=old for r in rows),D0_responses_before_ACK=sum(r['D0_response']<=old for r in rows),rows=rows,bursts=bursts)

def blocks956(folder):
    ev=read(folder/'events.json');j=read(folder/'joint.json');old=j['frames'][50]['ACK_masterclock']
    spi=[e for e in ev if e['event']=='SPI'];reads=[e for e in spi if e.get('opcode')=='0xd1' and e.get('input_generation',e['generation'])==956][:7]
    result=[];last=None
    for d in reads:
        pop=next(e for e in spi if e.get('opcode')=='0xd2' and e['start']>=d['clock'])
        status=next(e for e in spi if e.get('opcode')=='0xd0' and e['start']>=pop['clock'])
        gap=[e for e in spi if last is not None and last<=e['start']<d['start']]
        result.append(dict(bytes=d['bytes'],READ_start=d['start'],READ_end=d['clock'],POP_start=pop['start'],POP_end=pop['clock'],status_end=status['clock'],
            READ_to_POP_prepare_ms=ms(pop['start']-d['clock']),status_after_ACK_ms=ms(status['clock']-old),
            interblock_ms=ms(d['start']-last) if last is not None else None,
            interblock_SPI_ms=ms(sum(e['clock']-e['start'] for e in gap)),interblock_SPI=[e['opcode'] for e in gap]))
        last=status['clock']
    source=next(e for e in ev if e['event']=='source_begin' and e['generation']==956)
    return dict(source=source,blocks=result,first_D1_to_seventh_D0_ms=ms(result[-1]['status_end']-result[0]['READ_start']))

def run(a):
    phases={};variants=('account','progress','credit','batch','read') if a.read else ('account','progress','credit','batch') if a.batch else ('account','progress','credit') if a.credit else ('account','progress')
    for n in (1,2):
        folders={k:a.traces/v for k,v in [('MMC666',f'nes-ready673-b{n}'),('681',f'nes-late681-mapfirst{n}'),
            ('account',f'nes-receive682-account{n}'),('progress',f'nes-receive682-progress{n}')]}
        if a.credit or a.batch or a.read:folders['credit']=a.traces/f'nes-receive682-credit{n}'
        if a.batch or a.read:folders['batch']=a.traces/f'nes-receive682-batchb{n}'
        if a.read:folders['read']=a.traces/f'nes-receive682-read{n}'
        ts={k:trace(f,a.traces/f'nes-front638-both{n}h') for k,f in folders.items()};js={k:read(f/'joint.json') for k,f in folders.items()};base=ts['MMC666'];rows={}
        for k,f in folders.items():
            c=ts[k];j=js[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['MMC666']['parameters']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:d['work'] for g,d in c['frames'].items()}=={g:d['work'] for g,d in base['frames'].items()}
            if k in variants:
                assert j['firmware_SHA256']==sha(a.probe/(k+'01/src/obj-nes-100/firmware.stm'))
                assert j['client_SHA256']==sha(a.client/'sink165.sfc')
                if k=='read':
                    pin,=[e for e in read(f/'events.json') if e['event']=='image682_start'];assert pin['firmware']==j['firmware_SHA256']
            plan=read(f/'obj-phases.json');oldplan=read(folders['681']/'obj-phases.json')
            if k!='MMC666':
                for g,p in oldplan.items():assert [(x['count'],x['first'],x['decoded']) for x in p['banks557']]==[(x['count'],x['first'],x['decoded']) for x in plan[g]['banks557']]
            cpu=csv_groups(f/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
            protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=c['details'][951]['marks']['reveal']['line']<=246,interval952=c['intervals'][952]['VBlank']==3,final_wait957=c['intervals'][957]['final_waits']==0)
            delta=c['checked']['dense_mean_ms']-base['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-base['checked']['last_ACK'])
            regress=[g for g in base['intervals'] if c['intervals'][g]['VBlank']>base['intervals'][g]['VBlank']]
            waits=[g for g in base['intervals'] if c['intervals'][g]['final_waits']>base['intervals'][g]['final_waits']]
            rows[k]=dict(protected=protected,dense_mean_ms=c['checked']['dense_mean_ms'],dense_VBlank=c['checked']['dense_VB'],last_ACK=c['checked']['last_ACK'],
                dense_delta_MMC666_ms=delta,last_ACK_delta_MMC666_ms=ack,dense_delta_681_ms=c['checked']['dense_mean_ms']-ts['681']['checked']['dense_mean_ms'],
                last_ACK_delta_681_ms=ms(c['checked']['last_ACK']-ts['681']['checked']['last_ACK']),
                timing_gate=all(protected.values()) and delta<0 and ack<0 and not regress and not waits,
                regressions=regress,new_final_waits=waits,intervals=c['intervals'],wire_B=j['wire_B'],ARM_workspace_end=j['workspace_end'],ARM_observed_stack_low=j['observed_stack_low'],input_credit=input_credit(f),input956=blocks956(f),
                details={g:dict(marks=c['details'][g]['marks'],previous_reveal=c['details'][g]['previous_reveal'],packets=c['details'][g]['packets'],
                    early_DMA_B=c['early_DMA_B'][g],idle_grants=grants(f,g,c['details'][g]['packets']),END=end_timing(f,g),plan=plan_frontier(plan[str(g)]),
                    credit_frontier=credit_frontier(f,g,c['details'][g]['packets']),BG=preparation(f,g)['BG']) for g in (955,956,957)},
                pins={p:sha(f/p) for p in ('joint.json','packets.jsonl','window.csv','events.json','obj-phases.json')})
            if k in variants:
                rows[k]['receive956']=(receive_batch if k in ('batch','read') else receive)(f)
                rows[k]['request_gate']=rows[k]['timing_gate'] and rows[k]['receive956']['checked_blocks_before_ACK']==7
        phases[n]=rows
    resources={}
    for k in variants:
        img=a.probe/(k+'01/src/obj-nes-100/firmware.stm');n=img.stat().st_size;assert n<=212992
        resources[k]=dict(firmware=sha(img),Flash_B=n,Flash_free_B=212992-n,data_B=10040,BSS_B=19544,callback_stack_B=40 if k in ('batch','read') else 32,poll_stack_B=560)
    result=dict(stage=682,phases=phases,resources=resources,client=sha(a.client/'sink165.sfc'),client_build=read(a.client/'build.json'),
        timing_gate={k:all(p[k]['timing_gate'] for p in phases.values()) for k in variants},
        guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.probe.glob('*guards*.json') if p.name!='batch-guards01.json'},
        request_gate={k:all(p[k]['request_gate'] for p in phases.values()) for k in variants},selected_physical='MMC666',new_FIT=False,new_STA=False,source_pins={p.name:sha(p) for p in Path('tools').glob('*682.py')},
        scope='Actual linked ARM/65816, modeled SPI/IRQ and fixed ROM calendar, same work and exact pixels. Not physical FPS or live wholeboard RTL.')
    known={v['firmware'] for v in resources.values()}
    for v in result['guards'].values():assert v['result']['firmware'] in known
    result['unchanged_681_evidence']=dict(SHA256=sha(Path('analysis/late681-verification.json')),client=sha(a.client/'sink165.sfc'),new_RTL=False,new_CPU=False)
    result['excluded_batch01']=read(a.probe/'batch-replay01-excluded.json') if a.batch or a.read else None
    result['read_instruction_comparison']=read(a.probe/'read-instructions.json') if a.read else None
    if a.board:
        manifest=read(a.board/'inputs680.json');assert manifest==read(Path('analysis/late681-verification.json'))['board_inputs']
        for n,h in manifest['base'].items():assert sha(a.board/n)==manifest['changed'].get(n,h)
        assert sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
        result['board_inputs']=manifest
    if a.read:
        result['merge_boundary']={}
        for phase,rs in phases.items():
            detail={}
            for k in ('MMC666','read'):
                d=rs[k]['details'][957];ps=d['packets'];i=next(i for i,p in enumerate(ps) if p['section']==2 and p['offset']==1024);end=next(i for i,p in enumerate(ps) if p['section']==2 and p['offset']==1216)
                detail[k]=dict(packet_order=[{q:p[q] for q in ('op','section','offset','expanded_B','load_line','ack')} for p in ps[i:end+1]],
                    grants1024=[g for g in d['idle_grants'] if g['offset']==1024])
            detail['incoming_957_delta_ms']=ms(rs['read']['details'][957]['previous_reveal']-rs['MMC666']['details'][957]['previous_reveal'])
            detail['own_957_interval_delta_ms']=rs['read']['intervals'][957]['ms']-rs['MMC666']['intervals'][957]['ms']
            result['merge_boundary'][phase]=detail
        result['merge_source_pins']={n:sha(Path('tools')/n) for n in ('nes_dirty212.py','nes_tile532.py','nes_progress680_scan.py')}
    result['source_comparison']=read(a.probe/'source-diff.json');result['reproduction']=read(a.probe/'repro.json')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{k:{q:r[q] for q in ('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','timing_gate','regressions','new_final_waits')} for k,r in rs.items()} for n,rs in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','probe','client','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--credit',action='store_true');p.add_argument('--batch',action='store_true');p.add_argument('--read',action='store_true');p.add_argument('--board',type=Path);run(p.parse_args())
