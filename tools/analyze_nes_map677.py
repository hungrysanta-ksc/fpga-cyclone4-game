"""Reconcile bulk priority, map admission, actual DMA and total time in two starts."""
import argparse,json
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_output664 import trace
from analyze_nes_frontier536 import contents
from analyze_nes_bg674 import tile_image
from analyze_nes_idle676 import end_timing,idle,tail
from analyze_nes_bg675 import stalls

def grants(folder,g,packets):
    rows=csv_groups(folder/'window.csv')[g]
    dma=[r for r in rows if r['event']=='ppu_dma' and r['op']==-1]
    selected=[r for r in rows if r['event']=='idle524'];assert len(dma)==len(selected)
    copied=set();result=[]
    for r,s in zip(dma,selected,strict=True):
        assert 0<r['clock']-s['clock']<100
        accepted=set()
        for p in packets:
            if p['section']==2 and p['ack']<s['clock']:accepted.update(range(p['offset'],p['offset']+p['expanded_B'],64))
        ranges=[]
        for off in sorted(accepted-copied):
            if ranges and ranges[-1][0]+ranges[-1][1]==off:ranges[-1][1]+=64
            else:ranges.append([off,64])
        off=s['value']-65536 if s['value']>=65536 else None
        if off is not None:
            used=set(range(off,off+r['value'],64));assert used<=accepted-copied;copied.update(used)
        result.append(dict(clock=r['clock'],line=r['line'],bytes=r['value'],offset=off,accepted_map_B=64*len(accepted),
            remaining_map_ranges=ranges,next_packet=next((p for p in packets if p['load']>r['clock']),None)))
    return result

def map_calls(folder,g):
    ev=[e for e in read(folder/'events.json') if e['generation']==g and 'clock' in e]
    returns={e['call']:e for e in ev if e['event']=='return673'};rows=[]
    for e in ev:
        if e['event']!='call673' or e['name']!='packet_wire' or e['section']!=2:continue
        end=returns[e['call']]
        spi=[q for q in ev if q['event']=='SPI' and e['clock']<=q['start']<end['clock']]
        rows.append(dict(offset=e['offset'],bytes=e['bytes'],entry=e['clock'],returned=end['clock'],
            elapsed_ms=ms(end['clock']-e['clock']),initial_pending=(e['sent']-e['retired'])&65535,
            SPI=[{k:q[k] for k in ('opcode','start','clock','reply') if k in q} for q in spi]))
    return rows

def run(a):
    phases={};firmware=sha(a.arm/'obj-nes-100/firmware.stm')
    for n in (1,2):
        folders={'MMC666':a.traces/f'nes-ready673-b{n}','676':a.traces/f'nes-idle676-joint{n}','677':a.traces/f'nes-map677-{a.mode}{n}'}
        if a.mode=='run':folders['677-reserve']=a.traces/f'nes-map677-reserve{n}'
        t={k:trace(f,a.traces/f'nes-front638-both{n}h') for k,f in folders.items()}
        j={k:read(f/'joint.json') for k,f in folders.items()};b,c=t['MMC666'],t['677']
        assert j['677']['firmware_SHA256']==firmware
        for k,f in folders.items():
            assert j[k]['passed'] and j[k]['commits']==53 and j[k]['max_bulk_banks']<=2
            assert j[k]['parameters']==j['MMC666']['parameters'] and j[k]['client_SHA256']==j['MMC666']['client_SHA256']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:r['work'] for g,r in t[k]['frames'].items()}=={g:r['work'] for g,r in b['frames'].items()}
        # The change must not split or alter the already checked large plan banks.
        plans={k:read(f/'obj-phases.json') for k,f in folders.items()}
        for g,p in plans['676'].items():
            assert [(x['count'],x['first'],x['decoded']) for x in p['banks557']]==[(x['count'],x['first'],x['decoded']) for x in plans['677'][g]['banks557']]
        banks={}
        for g in (952,954,956,957):
            banks[g]={k:stalls(f,g)['batches'] for k,f in folders.items()}
        cpu=csv_groups(folders['677']/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            reveal951=c['details'][951]['marks']['reveal']['line']<=246,interval952=c['intervals'][952]['VBlank']==3,
            final_wait957=c['intervals'][957]['final_waits']==0)
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        regress=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        extra=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        details={}
        for g in (952,954,956,957):
            details[g]={}
            for k,f in folders.items():
                d=t[k]['details'][g]
                details[g][k]=dict(previous_reveal=d['previous_reveal'],marks=d['marks'],packets=d['packets'],
                    last_tile_ACK=d['last_tile_ACK'],last_ROM_response=d['last_ROM_response'],terms=d['terms'],
                    early_DMA_B=t[k]['early_DMA_B'][g],map_calls=map_calls(f,g),END=end_timing(f,g),
                    idle_grants=grants(f,g,d['packets']),
                    DMA=[r for r in csv_groups(f/'window.csv')[g] if r['event']=='ppu_dma'])
        phases[n]=dict(protected=protected,dense_delta_ms=dense,last_ACK_delta_ms=ack,
            selected_gate=all(protected.values()) and dense<0 and ack<0 and not regress and not extra,
            interval_regressions=regress,new_final_waits=extra,
            dense={k:dict(VBlank=v['checked']['dense_VB'],mean_ms=v['checked']['dense_mean_ms'],last_ACK=v['checked']['last_ACK']) for k,v in t.items()},
            intervals={k:v['intervals'] for k,v in t.items()},details=details,plan_banks=banks,
            idle=idle(folders['677']),drain952={k:tail(f,t[k],952) for k,f in folders.items()},
            wire_B={k:v['wire_B'] for k,v in j.items()},max_bulk_banks=j['677']['max_bulk_banks'],
            deadline911={k:one(s911,k) for k in ('load','upload165_entry')},
            pins={k:sha(folders['677']/k) for k in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl')})
    changed={p.name:sha(p) for p in a.arm.glob('nes_*.[ch]') if sha(p)!=sha(a.base_arm/p.name)}
    assert set(changed)=={'nes_plan_service200.c'}
    guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.guards}
    assert all(g['result']['firmware']==firmware for g in guards.values())
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    assert flash<=212992
    result=dict(baseline='MMC666',prior='676 joint',candidate='map677 '+a.mode,phases=phases,firmware=firmware,
        Flash_B=flash,Flash_free_B=212992-flash,ARM_data_B=10040,ARM_BSS_B=19544,progress_stack_B=32,
        extra_static_RAM_B=0,changed_vs676=changed,guards=guards,
        selected='677' if all(p['selected_gate'] for p in phases.values()) else 'MMC666',board_and_65816_unchanged=True,new_FIT_STA=False,
        source_pins={p.name:sha(p) for p in Path('tools').glob('*677.py')},
        scope='Actual linked M4/65816, CPI2/SPI/IRQ and periodic ROM calendar. Same work and independent output checks, no physical FPS claim. E0 receipt remains distinct from DMA and final display ACK.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{k:p[k] for k in ('protected','dense_delta_ms','last_ACK_delta_ms','interval_regressions','selected_gate')} for n,p in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','arm','base-arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--mode',choices=('reserve','run'),default='reserve')
    p.add_argument('--guards',type=Path,nargs='*',default=[]);run(p.parse_args())
