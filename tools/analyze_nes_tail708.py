"""Actual linked prefix issuance versus707, including consumer cost and VBlank."""
import argparse,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_frontier536 import contents
from analyze_nes_bg674 import tile_image
from analyze_nes_seal686 import receive_batch,blocks956

def supply(folder,detail):
    events=read(folder/'events.json')
    imm=next(e for e in events if e.get('generation')==951 and e['event']=='immutable673')
    begin=imm['clock'];end=detail['last_tile_ACK'];cursor=begin;busy={};gaps=[];rows=[]
    for e in events:
        if e['event']!='SPI' or e['start']>=end or e['clock']<=begin:continue
        if e['start']>cursor:gaps.append(dict(begin=cursor,end=e['start'],ms=ms(e['start']-cursor)))
        busy[e['opcode']]=busy.get(e['opcode'],0)+ms(min(end,e['clock'])-max(begin,e['start']))
        cursor=max(cursor,e['clock']);rows.append(e)
    if cursor<end:gaps.append(dict(begin=cursor,end=end,ms=ms(end-cursor)))
    assert abs(sum(busy.values())+sum(v['ms'] for v in gaps)-ms(end-begin))<1e-6
    # Packet ACK outstanding is not the same as unsent SPI payload.
    outstanding=[p for p in detail['packets'] if p['ack']>end]
    unsent=[p for p in detail['packets'] if p['start']>end]
    inflight=[p for p in detail['packets'] if p['start']<=end<p['push']]
    return dict(immutable=imm,interval_ms=ms(end-begin),SPI_service_ms=busy,
        bus_nonoccupied_ms=sum(v['ms'] for v in gaps),gaps=gaps,SPI=rows,
        outstanding_ACK_packets=len(outstanding),outstanding_ACK_wire_B=sum(p['wire_B'] for p in outstanding),
        not_started_E1_packets=len(unsent),not_started_E1_wire_B=sum(p['wire_B'] for p in unsent),inflight_E1=inflight,
        scope='SPI nonoccupied does not mean ARM/credit free. SPI service includes wire and driver allocation. Outstanding ACK bytes can already have been transmitted.')

def run(a):
    result={};all_gate=True
    for phase in (1,2):
        folders=dict(base=a.temp/f'nes-bg707-step{phase}',candidate=a.temp/f'nes-tail708-{a.mode}{phase}')
        ts={k:trace(f,a.temp/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};rows={}
        for k,f in folders.items():
            t=ts[k];j=js[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['base']['parameters'] and j['client_SHA256']==js['base']['client_SHA256']
            assert contents(f)==contents(folders['base']) and tile_image(f)==tile_image(folders['base'])
            assert {g:v['work'] for g,v in t['frames'].items()}=={g:v['work'] for g,v in ts['base']['frames'].items()}
            if k=='candidate':assert j['firmware_SHA256']==sha(a.arm/'src/obj-nes-100/firmware.stm')
            cpu=csv_groups(f/'window.csv');s911=[v for v in cpu[911] if v['op']==3]
            protection=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=t['details'][951]['marks']['reveal']['line']<=246,
                interval952=t['intervals'][952]['VBlank']==3,final_wait957=t['intervals'][957]['final_waits']==0)
            receive=receive_batch(f)
            rows[k]=dict(protected=protection,dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
                intervals=t['intervals'],all_warm=t['all_warm'],dense=t['dense'],
                details={g:t['details'][g] for g in (951,952,954,955,956,957)},
                first951=supply(f,t['details'][951]),receive956=receive,
                early_DMA_B={g:t['early_DMA_B'][g] for g in (951,952,954,955,956,957)},
                wire=j['wire_B'],ARM_instructions=j['ARM_instructions'],stack_low=j['observed_stack_low'],
                pins={n:sha(f/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv')})
        c=rows['candidate'];b=rows['base']
        c['delta']=dict(dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),
            frame951_tail_ms=c['details'][951]['last_tile_to_SEAL_load_ms']-b['details'][951]['last_tile_to_SEAL_load_ms'])
        c['timing_gate']=all(c['protected'].values()) and c['delta']['dense_ms']<0 and c['delta']['last_ACK_ms']<0 and c['receive956']['checked_blocks_before_ACK']==7
        c['relative_VBlank_regressions']=[g for g,v in c['intervals'].items() if v['VBlank']>b['intervals'][g]['VBlank']]
        all_gate &= c['timing_gate'];result[phase]=rows
    before=a.base/'src';after=a.arm/'src'
    changed=[p.name for p in before.glob('nes_*.[ch]') if sha(p)!=sha(after/p.name)]
    assert changed==['nes_native_sink165.c'],changed
    r=dict(stage=708,mode=a.mode,phases=result,timing_gate=all_gate,firmware=sha(after/'obj-nes-100/firmware.stm'),
        Flash_B=(after/'obj-nes-100/firmware.stm').stat().st_size,Flash_limit=212992,
        source_changed=changed,source_pins={n:sha(after/n) for n in changed},
        inherited_board='analysis/bg707-verification.json',RTL_changed=False,new_FIT_STA=False,CPU_changed=False,new_hardware=False,
        scope=__doc__+' Separate actual ARM/65816 with SPI/IRQ/ROM calendar; no simultaneous NES/PSRAM RTL or physical FPS.')
    a.out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(dict(mode=a.mode,gate=all_gate,Flash=r['Flash_B'],phases={p:dict(delta=v['candidate']['delta'],protected=v['candidate']['protected'],input_blocks=v['candidate']['receive956']['checked_blocks_before_ACK']) for p,v in result.items()})))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','arm','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',default='prefix')
    run(p.parse_args())
