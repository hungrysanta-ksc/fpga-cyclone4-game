"""Trace fixed destination ranges across regrouped FPGA OBJ bank publications."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline947 import directory, read, ready_bytes, report, sha
from nes_supply948 import MODES, work


def describe(folder, generation, slots):
    records=read(folder/'e9931.json')
    banks=read(folder/'banks904.json')[str(generation)]['banks557']
    sends=[e for e in read(folder/'events.json') if e.get('generation')==generation and e.get('opcode')=='0xe9']
    plans={}
    for batch,(packet,bank,send) in enumerate(zip([r for r in records if r['g']==generation],banks,sends,strict=True),1):
        assert packet['seal']==bank['seal']==send['clock']
        for record in map(bytes.fromhex,packet['records']):
            if record[0]==0x81:
                slot=int.from_bytes(record[3:5],'little')
                assert slot not in plans
                plans[slot]=(batch,round(send['start']),round(bank['seal']))
    returns=dict(read(folder/'returns904.json'))
    blocked=read(folder/'rows911.json')['blocked']
    produced=ready_bytes(folder)
    demands=read(folder/'demand948.json')
    out=[]
    for slot in slots:
        token,ready=produced[generation,1,slot*32]
        assert all(produced[generation,1,i]==(token,ready) for i in range(slot*32,(slot+1)*32))
        rows=[r for r in demands if r[:2]==[generation,slot]]
        assert rows and min(r[3] for r in rows)>=plans[slot][2]
        physical=[x for row in rows for x in row[-1]]
        assert all(x[:2]==[generation,1] and x[2]<=x[3]<x[4] for x in physical)
        out.append(dict(slot=slot,token=token,E9_batch=plans[slot][0],E9_start=plans[slot][1],
                        E9_accepted=plans[slot][2],first_lookup=rows[0][3],last_row_done=rows[-1][4],
                        first_request=physical[0][2] if physical else None,
                        first_grant=physical[0][3] if physical else None,grants=len(physical),
                        demand_wait=sum(g-r for _,_,r,g,_ in physical),
                        bank_ready=ready,bank_return=round(returns[token]),
                        bank_block_start=blocked.get(str(token),[None,None])[1]))
    return out


def compare(temp,modes):
    metrics=report(temp,modes,prefix='948',work=work)
    result={k:v for k,v in metrics.items() if k!='cases'}
    result['cases']={}
    for case,group in metrics['cases'].items():
        ref=directory(temp,int(case[-1]),'935boundedfinal',case[:-1])
        ack935=read(ref/'joint.json')['frames'][-1]['ACK_masterclock']
        result['cases'][case]={}
        for mode,row in group.items():
            result['cases'][case][mode]={k:v for k,v in row.items() if k not in ('stages','late_vs935','preDMA')}
            result['cases'][case][mode]['advance_ACK_vs935']=ack935-row['final_ACK']
            result['cases'][case][mode]['gen910_D2']=row['stages'][910]['commit_D2']
    result['cold_destination_trace']={}
    for phase in (1,2):
        pair={}
        for mode,ref in [('old','935boundedfinal'),('split','947pressure_seal'),('zero_fit','948zero_fit')]:
            folder=directory(temp,phase,('948bound' if mode=='old' else '948trace')+mode,'cold')
            original=directory(temp,phase,ref,'cold')
            # A passive observer must preserve wire, ROM grants, and all bank
            # completions through the last ARM ACK.
            for name in ('window.csv','producer.jsonl','packets.jsonl','e9931.json','grants904.json','returns904.json','events.json'):
                assert sha(folder/name)==sha(original/name),(phase,mode,name)
            pair[mode]={g:describe(folder,g,slots) for g,slots in [(909,range(56,68)),(910,range(79,89))]}
        result['cold_destination_trace'][phase]=pair
    result['report_decoder']={}
    for mode in modes:
        path=work(mode)/'report948.json'
        if path.is_file():
            proof=read(path)
            assert proof['firmware']==result['cases']['warm1'][mode]['sha256'] and proof['words']==84
            result['report_decoder'][mode]=proof
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    args=p.parse_args()
    args.out.write_text(json.dumps(compare(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
