"""Collect separate post-fit, physical-port RTL and linked CPU replay evidence."""
import argparse
import json
import re
from pathlib import Path

from analyze_nes_overlap913 import BASE, OUT, PERIOD, audit, guards, measure, ms, peer, work
from test_nes_banks557 import host_after, MASTER


def read(path):
    return json.loads(path.read_bytes())


def area(board):
    fit=(board/'output_files/board.fit.rpt').read_text(errors='replace')
    summary=(board/'output_files/board.fit.summary').read_text()
    summary_val=lambda name:int(re.search(name+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
    def resources(name):
        return int(re.search(name+r'\s*;\s*([\d,]+) /',fit)[1].replace(',',''))
    failed=re.search(r'requires (\d+) LABs',(board/'fit.log').read_text(errors='replace'))
    result=dict(LE=summary_val('Total logic elements'),FF=summary_val('Dedicated logic registers'),
                comb=summary_val('Total combinational functions'),ram_bits=summary_val('Total memory bits'),
                LAB=int(failed[1]) if failed else None,
                fitted='Fitter Status : Successful' in summary)
    if result['fitted']:
        result['LAB']=resources('partially or completely used')
        result['M9K']=resources('M9Ks')
        report=(board/'output_files/board.sta.rpt').read_text(errors='replace')
        row=re.search(r'; Worst-case Slack\s*;([^\n]+)',report)
        result['timing_ns']=dict(zip(('setup','hold','recovery','removal','min_pulse'),
                                    map(float,row[1].strip().strip(';').split(';'))))
        result['unconstrained_io']={k:[int(a),int(b)] for k,a,b in
                                    re.findall(r'; (Unconstrained (?:Input|Output) Ports)\s*;\s*(\d+)\s*;\s*(\d+)',report)}
    return result


def score(temp,board,phase,cold,ref913):
    cache='cold' if cold else 'warm'
    def directory(tag):return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
    base=directory('907')
    reference,packets=measure(base,BASE)
    origin=int((directory('914wire')/'origin914.txt').read_text())
    events=read(directory('914wire')/'events.json')
    jobs=[j for l in (directory('914wire')/'producer.jsonl').read_text().splitlines()
          if (j:=json.loads(l))['generation']==912]
    log=(board/f'trace-{phase}-{cache}.log').read_text(errors='replace')
    assert 'PASS914 trace chunks=8 bytes=656' in log
    entries=re.findall(r'chunk=(\d+) bytes=(\d+) head=(\d+) reference_producer=(\d+) reference_return=(\d+)',log)
    pubs=re.findall(r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',log)
    rom=re.findall(r'ROM914 edge=(\d+) spec=(\d+) addr=(\d+)',log)
    assert len(pubs)==len(entries)==len(jobs)==8
    chunks=[]
    for entry,pub,j in zip(entries,pubs,jobs):
        i,n,h,_,ret=map(int,entry)
        index,size,published=map(int,pub)
        assert (index,size)==(i,n) and j['bytes']==n
        queries=[e for e in events if e['generation']==912 and e.get('opcode')=='0xe8' and
                 (r:=bytes.fromhex(e['reply']))[6] and int.from_bytes(r[14:18],'little')==j['token']]
        due=host_after(queries[0]['start']+7.5*MASTER/2625000,3)-origin
        chunks.append(dict(n=i,bytes=n,published=published,head=h,first_E8_valid=round(due),
                           reference_return=ret,late_to_E8_ms=ms(h-due),late_to_return_ms=ms(h-ret)))
    target=ref913['912bleading']['stamps']['912']['capture_ready']-240*341*4-PERIOD
    result={}
    for tag in ['914head','914ghead','914ihead']:
        folder=directory(tag)
        r=audit(folder,work('idle'),reference,packets,base)
        assert peer.sha(folder/'client.sfc')==peer.sha(OUT/'consumer/sink165.sfc')
        result[tag]={k:r[k] for k in ('intervals','ACK','ACK_delta_ms','E0','pre_bytes','exact_496','preDMA')}
        result[tag]['capture_margin_us']=round(ms(target-r['stamps'][911]['commit_D2'])*1000,3)
        result[tag]['E9_shift_clocks']=[round(a['seal']-b['seal']) for a,b in zip(
            read(folder/'banks904.json')['912']['banks557'],read(directory('914wire')/'banks904.json')['912']['banks557'])]
    result['RTL912']=dict(chunks=chunks,core_calendar='509 fill1',E8=audit_polls(log),demand_grants=sum(s=='0' for _,s,_ in rom),
                          ahead_grants=sum(s=='1' for _,s,_ in rom),hits=int(re.search(r'bytes=656 hits=(\d+)',log)[1]))
    selected=result['914ihead']
    assert selected['ACK']<reference['final_ACK'] and selected['ACK_delta_ms']<0
    assert not any(selected['E9_shift_clocks'])
    assert selected['intervals']==((16 if phase==1 else 17) if cold else 14)
    if cold:
        assert selected['exact_496']
    else:
        assert selected['capture_margin_us']>=(96.4 if phase==1 else 75.7)
    assert result['RTL912']['E8']['differences']==0
    return result


def audit_polls(log):
    row=re.search(r'E8914 compared=(\d+) different=(\d+)',log)
    assert row and int(row[1])>0
    return dict(samples=int(row[1]),differences=int(row[2]),
                examples=re.findall(r'E8914 difference [^\r\n]+',log)[:8])


def main(temp,output):
    board=temp/'nes-port914I/nes-trial816-board914'
    root=Path(__file__).resolve().parents[1]
    old=read(root/'analysis/overlap913-results.json')['comparisons']
    ledger={}
    for rev in ('906',*'ABCDEFGHI'):
        path=temp if rev in ('906','A') else temp/f'nes-port914{rev}'
        ledger[rev]=area(path/('nes-trial816-board906' if rev=='906' else 'nes-trial816-board914'))
    proof=guards(work('idle'))
    base=read(temp/'nes-port914F/base914/result.json')
    assert base['firmware_sha256']==proof['firmware'] and base['safe_return']
    for name,status in [('stop',228),('invalid-seal',224)]:
        assert read(temp/f'nes-port914I/{name}.json')==dict(commits=4,status=status)
    key_slacks=list(map(float,re.findall(r'KEY914 bit=\d+ slack=([-\d.]+)',(board/'key914.log').read_text(errors='replace'))))
    assert len(key_slacks)==11 and min(key_slacks)>0
    assert peer.sha(board/'sink-program.hex')==peer.sha(OUT/'consumer/sink-program.hex')
    assert 'PASS914 SPI' in (board/'spi914.log').read_text(errors='replace')
    assert 'PASS914 checked' in (board/'sim914.log').read_text(errors='replace')
    results={f'{p}-{c}':score(temp,board,p,c=='cold',old[f'{p}-{c}']) for p in (1,2) for c in ('warm','cold')}
    proof.update(consumer=peer.sha(OUT/'consumer/sink165.sfc'),consumer_hex=peer.sha(board/'sink-program.hex'),
                 board_sof=peer.sha(board/'output_files/board.sof'),bundled_key_slack_ns=key_slacks,
                 bad_SEAL=224,upload_STOP=228,base_released=True)
    proof['board_source']={p.name:peer.sha(p) for p in (board/'nes_plan_batch206.sv',board/'nes_source_tile192.sv',
                            board/'nes_direct206.sv',board/'nes_e9_scan914.sv',board/'nes_e9_rows914.sv',
                            board/'nes_plan_spi200.sv')}
    lead={f'{g}-{p}':audit_polls((board/f'lead-{g}-{p}-warm.log').read_text(errors='replace'))
          for g in (910,911) for p in (1,2)}
    assert all(row['differences']==0 for row in lead.values())
    assert ledger['I']['fitted'] and min(ledger['I']['timing_ns'].values())>0
    output.write_text(json.dumps(dict(board=ledger,guards=proof,cases=results,warm_lead=lead),indent=2)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();main(args.temp,args.output)
