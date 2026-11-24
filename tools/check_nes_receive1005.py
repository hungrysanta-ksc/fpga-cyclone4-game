"""Compare measured 65816 packet service, two-slot schedules and negative cases."""
import argparse
import json
from pathlib import Path

from check_nes_credit1004 import audit_bus, counters, ledger, read, rows, sha
from nes_budget1005 import budget
from nes_receive1005 import PACKED, ORIGIN, candidate
from pack_nes_column854 import encode, decode
from test_nes_banks557 import MASTER


def packed(mode):
    body=bytearray((PACKED/'body.bin').read_bytes())
    old=len(body)
    patches,_=candidate(mode)
    for a,data in sorted(patches.items()):
        offset=a-ORIGIN
        assert 0<=offset<=len(body)
        body[offset:offset+len(data)]=data
    cfg=read(PACKED/'build.json')
    stream=encode(bytes(body),cfg['prefix_B'],2,short_pairs=True)
    assert decode(stream,cfg['prefix_B'],len(body),2,short_pairs=True)==body
    return dict(extra_code_and_table=len(body)-old,packed_delta=len(stream)-cfg['encoded_B'],
                free=cfg['physical_free_B']+cfg['encoded_B']-len(stream))


def breakdown(records,keys):
    times=[int(records[k]['clock']) for k in keys]
    assert times==sorted(times)
    return dict(zip(keys[1:],(b-a for a,b in zip(times,times[1:])),
                    strict=True),total=times[-1]-times[0])


def inspect(temp,phase):
    ref,_,jobs,events=ledger(temp,phase)
    prior=read(Path(__file__).resolve().parents[1]/'analysis/overlap1002-results.json')[str(phase)]
    stock=temp/f'nes-credit1004-control-p{phase}'
    prefix=[r for r in rows(ref/'window.csv') if int(r['g'])<912]
    vstart=prior['vblank46_start']
    runs={}
    for mode in ('stock','tile','section','both'):
        d=temp/f'nes-receive1005-{mode}-p{phase}'
        result=read(d/'result.json')
        assert result['passed'] and (result['commits'],result['last_status'])==(8,1)
        for g in range(905,913):
            assert sha(d/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
        win=rows(d/'window.csv')
        assert [r for r in win if int(r['g'])<912 and r['event']!='group1002']==prefix
        assert sum(int(r['value']) for r in prefix if (r['g'],r['op'],r['event'])==('909','-1','ppu_dma'))==624
        if mode=='stock':
            assert [r for r in win if not r['event'].startswith('rx1005_')]==rows(stock/'window.csv')
        bus=audit_bus(d,'control',jobs,events)
        details={}
        for j in jobs:
            tile=j.get('token',0)>=34
            if not tile and not (j['section']==5 and j['offset']>=1121):
                continue
            seq=bus['packets'][j['index']]['sequence']
            rec={r['event']:r for r in win if r['g']=='912' and int(r['index'])==seq}
            if tile:
                assert int(rec['consume920']['value'])==j['token']
                keys=('load','mark212920','append212920','first_read920','service920','consume920','ack')
                key='tile'+str(j['token'])
            else:
                keys=('load','rx1005_data','rx1005_accepted','ack')
                key='section5_'+str(j['span'])
            details[key]=breakdown(rec,keys)
        group,=[int(r['clock']) for r in win if (r['g'],r['event'])==('912','group1002')]
        c=counters(d,912)
        runs[mode]=dict(detail=details,service=sum(x['total'] for x in details.values()),
                        group=group,group_late_ms=round((group-vstart)*1000/MASTER,6),
                        SEAL=c['seal'],reveal=c['reveal'],ack=c['ack'],E0=bus['E0'])
    guards={}
    for mode,fault,op,status in [('both','offset',2,224),('both','bad_seal',3,224),
                                 ('both','stop_decode',3,228),('both','duplicate-checked',7,224),
                                 ('stock','duplicate-checked',7,224)]:
        d=temp/f'nes-receive1005-{mode}-p{phase}-{fault}'
        res=read(d/'result.json')
        assert res['passed'] and (res['commits'],res['last_status'])==(7,status)
        assert sha(d/'retained.rgb')==sha(ref/'frame-911.rgb')
        win=rows(d/'window.csv')
        row,=[r for r in win if int(r['g'])>=912 and r['event']=='ack' and int(r['value'])==status]
        assert int(row['op'])==op
        if op==7:
            assert any(r['event']=='rx1005_duplicate' for r in win)
            assert not any(r['index']==row['index'] and r['event'] in ('first_read920','consume920') for r in win)
        if op==3:
            assert [int(r['value']) for r in win if r['event']=='rx1005_verified']==[201,240]
        assert not any(int(r['g'])>=912 and r['event']=='reveal' for r in win)
        guards[mode+'-'+fault]=dict(op=op,status=status,retained=911)
    assert max(e['clock'] for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd2')==prior['protected']['D2_910']
    return dict(runs=runs,optimistic_budget=budget(prior),protected=prior['protected'],
                vblank_start=vstart,end246=prior['line246_end'],guards=guards)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    result=dict(phases={i:inspect(a.temp,i) for i in (1,2)},
                packing={m:packed(m) for m in ('stock','tile','section','both')})
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
