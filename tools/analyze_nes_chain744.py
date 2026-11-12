# SPDX-License-Identifier: MIT
"""Check matched map offers, actual PPU writes, DMA setup and retained display."""
import argparse
import json
from pathlib import Path
from analyze_nes_bitmap743 import cpu_frame, csv_groups, ms, read, records, sha
from build_nes_bitmap743 import assemble, codec, optimal
from replay_nes_beam741 import replacements
from replay_nes_chain744 import code
from replay_nes_gap740 import schedule


def offers(folder, section):
    out=[]
    for row in (folder/'arrivals.tsv').read_text().splitlines():
        t,h,p=row.split('\t')
        if h!='FINISH' and bytes.fromhex(h)[1]==section:
            out.append((int(t),h,p))
    return out


def check_run(folder,base):
    result=read(folder/'result.json')
    assert result['passed'] and read(folder/'audit.json')['frames']==result['commits']==53
    assert result['first_packet_poll_masterclock']==read(base/'result.json')['first_packet_poll_masterclock']
    assert sha(folder/'client.sfc')==sha(base/'client.sfc')
    assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
    cur={g:cpu_frame(folder,g) for g in (907,908,910,911,950,951,952,953,954,955,956,957)}
    intervals={g:cur[g]['reveal']['frame']-cur[g-1]['reveal']['frame'] for g in (908,911,951,952,953,954,955,956,957)}
    assert intervals=={908:2,911:2,951:3,952:3,953:3,954:3,955:3,956:3,957:3}
    assert cur[951]['reveal']['line']<=246 and cur[957]['final_wait']==0
    maps={g:next(x for x in cur[g]['prefix'] if x['size']==1536 and x['offset']==67584) for g in (952,957)}
    tile=[x for x in records(folder/'tile532.csv') if x['g']==957 and 19104<=x['src']<19392]
    final=sum(x['bytes'] for x in records(folder/'seal528.csv') if x['g']==957 and x['event']=='dma' and 19104<=x['src']<19392)
    assert final+sum(x['n'] for x in tile)==288
    obs=records(folder/'chain744.csv')
    start=next(x for x in obs if x['event']=='map_start')
    assert start['clock']==maps[957]['start']
    result=dict(first_poll=result['first_packet_poll_masterclock'],map_DMA=maps,intervals=intervals,public951=cur[951]['reveal']['line'],
                final_wait957=0,final_OBJ_B=final,final_ACK=cur[957]['ACK'],map_start_owner=start,
                dense_ms=ms(cur[957]['reveal']['clock']-cur[951]['reveal']['clock'])/6,
                trace=sha(folder/'window.csv'),offers=sha(folder/'arrivals.tsv'),reads=sha(folder/'chain744.csv'))
    if tile:
        assert len(tile)==1 and tile[0]['n']==64
        dma=next(x for x in obs if x['event']=='DMA')
        transfer=next(x for x in cur[957]['prefix'] if x['start']==dma['clock'])
        assert transfer['size']==64 and transfer['last_line']<=261
        setup=[r for r in obs if maps[957]['end']<r['clock']<dma['clock']]
        result.update(OBJ_start=dma['clock'],line=dma['line'],h=dma['h'],OBJ_last_line=transfer['last_line'],
                      OBJ_last=transfer['end'],map_to_OBJ_us=ms(dma['clock']-maps[957]['end'])*1000,
                      successor_desc_byte_reads=[r['addr'] for r in setup if r['event']=='read' and 0x7e4018<=r['addr']<=0x7e401d],
                      channel_writes=[r['addr'] for r in setup if r['event']=='set'])
    return result


def rom_cost(client):
    source=(client/'body.bin').read_bytes()
    labels=read(client/'labels.json')
    result={}
    for name in ('stock','combined'):
        edits=replacements(client,'budget')
        if name=='stock':
            at=(labels['dma_continue680']&65535)+9
            edits={at:edits[at]}
        body=bytearray(source)
        for addr,data in sorted(edits.items()):
            i=addr-codec.DEST
            assert i<=len(body)
            body[i:i+len(data)]=data
        if name=='combined':
            body=bytearray(assemble(bytes(body),labels)[0])
        site=(labels['whole526']&65535)+10-codec.DEST
        assert body[site:site+3]==bytes.fromhex('8d5212')
        target=codec.DEST+len(body)
        body[site:site+3]=bytes([0x4c])+target.to_bytes(2,'little')
        routine=code(labels,target)
        body.extend(routine)
        result[name]=dict(routine_B=len(routine),body_B=len(body),over_at_727_prefix_B=codec.BOOT+512+len(optimal(bytes(body),512))-codec.STORED)
    return result


def analyze(a):
    out=dict(stage=744,retained=727,packing=rom_cost(a.client),phases={})
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        def path(tag):return a.temp/f'nes-chain744-{tag}{n}'
        ref=path('ref')
        reference_packets=[r.split('\t',1)[1] for r in (ref/'arrivals.tsv').read_text().splitlines()]
        map_offers=offers(ref,2)
        assert map_offers
        runs={}
        for tag in ('ref','stocktail','stockearlybase','stockearly','base','final','feedback'):
            folder=path(tag)
            runs[tag]=check_run(folder,base)
            assert offers(folder,2)==map_offers
            assert [r.split('\t',1)[1] for r in (folder/'arrivals.tsv').read_text().splitlines()]==reference_packets
        assert runs['stocktail']['trace']==runs['ref']['trace']==sha(base/'window.csv')
        assert runs['base']['trace']==sha(a.temp/f'nes-bitmap743-early{n}/window.csv')
        assert runs['base']['offers']==runs['final']['offers']==runs['stockearly']['offers']==runs['stockearlybase']['offers']
        cur=runs['final']
        assert cur['map_DMA']==runs['base']['map_DMA'] and cur['line']<=257 and cur['final_OBJ_B']==224
        assert len(cur['successor_desc_byte_reads'])==len(set(cur['successor_desc_byte_reads']))==6
        assert cur['channel_writes']==[0x4302,0x4303,0x4305,0x4306]
        actual_ack=max(r['clock'] for r in csv_groups(path('final')/'window.csv')[957] if r['event']=='ack' and r['section']==2)
        priced=read(path('final')/'receipt742.json')
        assert priced['E0_starts'][-2]<=actual_ack<priced['E0_starts'][-1]<priced['OBJ_push']
        assert priced['hypothetical_lead_clocks']==0
        f=path('feedback')
        pulse=int((f/'pulse741.txt').read_text().splitlines()[0])
        scroll=next(t for t,h,_ in offers(f,5) if int.from_bytes(bytes.fromhex(h)[8:10],'little')==957)
        assert abs(scroll-pulse-schedule(base,n,'first')['callback_masterclocks'])<=1
        begin=runs['feedback']['map_DMA'][957]
        assert begin['start']<scroll<begin['end'] and runs['feedback']['final_OBJ_B']==288
        out['phases'][n]=dict(runs=runs,E0=priced,observed_map_ACK=actual_ack,scroll_during_DMA=scroll,
                                dense_delta_us=(cur['dense_ms']-runs['ref']['dense_ms'])*1000,
                                ACK_delta_us=ms(cur['final_ACK']-runs['ref']['final_ACK'])*1000)
        assert cur['dense_ms']<runs['ref']['dense_ms'] and cur['final_ACK']<runs['ref']['final_ACK']
    out['guards']={}
    for n in (1,2):
        guards=out['guards'][n]={}
        for tag,status in [('pre',0),('mid',0),('stale',224)]:
            f=a.temp/('nes-chain744-'+tag+str(n))
            j=read(f/'result.json')
            assert j['passed'] and j['commits']==52 and j['last_status']==status
            assert sha(f/'retained.rgb')==sha(a.temp/f'nes-pair727-a{n}/frame-956.rgb')
            rows=records(f/'chain744.csv')
            if tag=='pre':
                assert any(r['event']=='fault' for r in rows) and not any(r['event']=='DMA' for r in rows)
            if tag=='mid':
                shot=int((f/'fault741.txt').read_text())
                target=out['phases'][n]['runs']['final']
                assert target['OBJ_start']<shot<target['OBJ_last']
                assert sum(r['event']=='DMA' for r in rows)==1
            guards[tag]=dict(status=status,commits=52,retained=sha(f/'retained.rgb'))
        f=a.temp/f'nes-chain744-head{n}'
        r=records(f/'chain744.csv')
        at=next(x['clock'] for x in r if x['event']=='fault')
        next_head=next(x for x in csv_groups(f/'window.csv')[957] if x['clock']>at and x['event'] in ('load','ppu_dma'))
        assert next_head['event']=='load' and next_head['section']==5 and read(f/'audit.json')['frames']==53
        guards['new_head']=next_head
    for trial in (690,704):
        j=read(a.temp/f'nes-chain744-menu{trial}.json')
        assert len(j['rows'])==5 and j['marker_cases']==4 and all(bool(v['released'])==(k=='normal') for k,v in j['rows'].items())
        out['guards'][f'menu{trial}']=dict(firmware=j['firmware'],cases=list(j['rows']),markers=4)
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','client','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
