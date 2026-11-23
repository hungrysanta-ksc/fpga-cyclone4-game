"""Match physical ROM grants and an E8 descriptor to the consuming 65816 packet."""
import argparse
import bisect
import json
import re
from pathlib import Path

from analyze_nes_chr951 import board_cost, logtext
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from check_nes_blank959 import directory, read, rows, sha, summary
from nes_blank960 import PACKED, WORK
from test_nes_banks557 import MASTER, host_after
from test_nes_service509_schedule import Calendar


def milliseconds(ticks):
    return round(ticks*1000/MASTER,6)


def hardware(folder,g):
    path=folder/f'gen{g}'
    origin=int((path/'origin914.txt').read_text())
    log=logtext(path/'tail961.log')
    assert 'PASS914 trace' in log and 'Errors: 0' in log
    def records(expr):
        return [tuple(map(int,m)) for m in re.findall(expr,log)]
    requests=records(r'REQ961 at=(\d+) addr=(\d+)')
    grants=records(r'ROM914 edge=(\d+) spec=0 addr=(\d+)')
    replies=records(r'REPLY961 at=(\d+) addr=(\d+)')
    aux=records(r'AUX952 at=(\d+) address=(\d+)')
    samples=records(r'E8914 compared=(\d+) different=(\d+)')
    assert len(samples)==1
    waits=[]
    # Only foreground requests with an observed matching physical completion.
    for i,(at,addr) in enumerate(requests):
        end=requests[i+1][0] if i+1<len(requests) else float('inf')
        grant=next((edge for edge,a in grants if a==addr and at<=edge<end),None)
        if grant is None:
            continue
        reply=next(edge for edge,a in replies if a==addr and edge>=grant)
        waits.append(dict(tag=addr//16,row=addr%16,request=origin+at,grant=origin+grant,
                          reply=origin+reply,wait_ms=milliseconds(grant-at)))
    return dict(samples=samples[0],foreground_reads=len(waits),
                longest=max(waits,key=lambda r:r['wait_ms'],default=None),
                auxiliary=[(origin+x,a) for x,a in aux]),origin,log


def trace(folder):
    h,origin,log=hardware(folder,908)
    jobs=[r for r in map(json.loads,(folder/'producer.jsonl').read_text().splitlines()) if r['generation']==908]
    job=jobs[-1]
    assert job['kind']==1 and job['bytes']==544 and job['token']==13
    local=len(jobs)
    ready=origin+int(re.search(rf'PUB914 token={local} bytes=544 at=(\d+)',log)[1])
    sample=origin+int(re.search(rf'DESC914 edge=(\d+) local_token={local} kind=1 bytes=544 slot=39 gen=908',log)[1])
    spi=[e for e in read(folder/'events.json') if e.get('generation')==908]
    first=next(e for e in spi if e.get('opcode')=='0xe8' and bytes.fromhex(e['reply'])[6]
               and int.from_bytes(bytes.fromhex(e['reply'])[14:18],'little')==job['token'])
    assert round(host_after(first['start']+7.5*MASTER/2625000,3))==sample
    packets=[(end,bytes.fromhex(raw)) for _,end,raw,_ in map(json.loads,(folder/'packets.jsonl').read_text().splitlines())]
    end,packet=next((end,b) for end,b in packets if b[:2]==bytes([7,1]) and int.from_bytes(b[8:10],'little')==908
                    and int.from_bytes(b[16:20],'little')==job['token'])
    assert int.from_bytes(packet[10:12],'little')==39*32 and int.from_bytes(packet[14:16],'little')==544
    send=next(e for e in spi if e.get('opcode')=='0xe1' and e['packet_opcode']==7 and abs(e['clock']-end)<=1)
    section=[r for r in rows(folder/'window.csv') if r['g']=='908' and r['op']=='7' and r['section']=='1']
    load=next(r for r in section if r['event']=='load' and int(r['clock'])>=end)
    ack=next(r for r in section if r['event']=='ack' and r['index']==load['index'])
    clocks=dict(publication=ready,E8_sample=sample,E8_done=round(first['clock']),E1_start=round(send['start']),
                E1_done=end,SNES_load=int(load['clock']),SNES_return=int(ack['clock']))
    assert list(clocks.values())==sorted(clocks.values())
    h['tail']=dict(generation=908,token=13,byte_count=544,load_line=int(load['line']),clocks=clocks,
                   ready_to_E8_sample_ms=milliseconds(sample-ready),ready_to_load_ms=milliseconds(int(load['clock'])-ready))
    return h


def analyze(temp):
    board=temp/'nes-trial816-board961'
    calendar=Calendar(temp/'nes-service509-rom03')
    out=dict(master_Hz=MASTER,board={'960':board_cost(temp/'nes-trial816-board960'),'961':board_cost(board)},phases={})
    assert 'PASS952 16 actual' in logtext(board/'row961.log')
    assert 'PASS914 checked' in logtext(board/'guards951.log')
    out['redirect_STOP_failed_reply_changed_ROM']=True
    menu=read(board/'menu961.json')
    base=read(board/'base961/result.json')
    assert base['safe_return'] and base['base_restored'] and menu['rows']['normal']['released']
    assert base['firmware_sha256']==menu['firmware']==sha(WORK/'link/src/obj-nes-100/firmware.stm')
    out.update(firmware=menu['firmware'],consumer=sha(PACKED/'sink165.sfc'),base_restore=base['config_paths'])
    for phase in (1,2):
        cases={}
        for cache in ('cold','warm'):
            base='960closed' if cache=='cold' else '960static'
            reference=directory(temp,phase,base,cache)
            tags=(base,'961pair','961wirebase2','961wirepair') if cache=='cold' else (base,'961pair')
            for tag in tags:
                folder=directory(temp,phase,tag,cache)
                metrics,checks=measure(folder,WORK)
                if tag==base:
                    reference_checks=checks
                else:
                    assert checks==reference_checks
                s=summary(folder,reference)
                assert sha(folder/'client.sfc')==sha(PACKED/'sink165.sfc')
                case=dict(reveals=s['reveals'],six=s['six'],ACK912=s['ACK912'],D2=s['D2_before_911_reveal'],
                          RGB=s['RGB'],VRAM_B=s['VRAM_B'])
                for g in (908,909):
                    fr=metrics['frames'][g]
                    case[g]=dict(first_D1=fr['first_D1'],last_D2=fr['commit_D2'],SEAL=fr['clocks']['SEAL'],
                                 load_line=fr['line'][0],DMA_start=fr['clocks']['DMA_start'],DMA_end=fr['clocks']['DMA_end'],
                                 show=fr['clocks']['show'],last_OBJ=fr['clocks']['last_OBJ'],ACK=fr['clocks']['ACK'])
                last=metrics['frames'][912]
                case['prior_DMA912']=len(coverage([r for r in last['preDMA'] if r[3]==last['VBlank'][3]-1]))
                if cache=='cold':
                    case['RTL908']=trace(folder)
                    case['RTL909']=hardware(folder,909)[0]
                    if tag.startswith('961wire'):
                        assert all(case[k]['samples'][1]==0 for k in ('RTL908','RTL909'))
                    request=case['RTL909']['longest']['request']
                    before=bisect.bisect_left(calendar.starts,request%calendar.period)
                    previous=(request//calendar.period-int(before==0))*calendar.period+calendar.starts[before-1]
                    batches=read(folder/'e9931.json')
                    first_nearby=next(b for b in batches if any(
                        r[0]==0x81 and 3072<=int.from_bytes(r[5:7],'little')<=3075
                        for r in map(bytes.fromhex,b['records'])))
                    batch=next(b for b in batches if b['g']==909)
                    assert first_nearby==batch
                    assert any(r[0]==0x81 and int.from_bytes(r[5:7],'little')==3074 for r in map(bytes.fromhex,batch['records']))
                    case['first_E9_909']=dict(first_generation_with_tags_3072_3075=batch['g'],
                                               seal=round(batch['seal']),previous_calendar_grant=previous,
                                               after_grant_ms=milliseconds(batch['seal']-previous))
                    prior=base if tag==base or tag.startswith('961wirebase') else '961pair'
                    source=directory(temp,phase,prior,cache)
                    if tag.startswith('961wire'):
                        # The first corrected edge is in 908. Verify the prior
                        # generation's complete stimulus before reusing its RAM.
                        for f in ('origin914.txt','polls914.txt','tokens914.txt','batch914.txt',
                                  'cap914.txt','chr914.hex','expected914.hex','grants914.txt',
                                  'sizes914.txt','wire914.hex'):
                            assert sha(folder/'gen907'/f)==sha(source/'gen907'/f)
                        case['feedback']=read(folder/'matched961.json')
                    aux=hardware(source,907)[0]['auxiliary']
                    case['prefetched_907']=[(clock,a//16,a%16) for clock,a in aux]
                    if tag=='961pair':
                        assert {addr for _,addr in aux if 6256<=addr//16<=6257}=={16*t+r for t in (6256,6257) for r in range(8)}
                        for label,status in [('stop908',228),('bad-seal',224)]:
                            sub=folder/('guard-'+label)
                            result=read(sub/'result.json')
                            assert result['passed'] and result['commits']==3 and result['last_status']==status
                            assert sha(sub/'retained.rgb')==sha(folder/'frame-907.rgb')
                        case['cancel_retains_generation']=907
                cases[cache+'_'+tag]=case
        baseline=cases['cold_961wirebase2']
        trial=cases['cold_961wirepair']
        delta=trial['ACK912']-baseline['ACK912']
        cases['wire_delta']=dict(six=trial['six']-baseline['six'],ACK912_clocks=delta,
                                 ACK912_ms=milliseconds(delta))
        out['phases'][phase]=cases
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    print(json.dumps(analyze(p.parse_args().temp),indent=2))
