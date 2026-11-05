# SPDX-License-Identifier: MIT
"""Summarize matched-clock trials and check proposed reuse against literal bank history."""
import argparse
import json
from analyze_nes_map628 import csv_groups, ms, one, packets, read, sha
from pathlib import Path


def analyze(root, client, out):
    phases = []
    for phase in (1,2):
        trace = root/f'nes-seal625-tables-bg-{phase}'
        cpu = csv_groups(trace/'window.csv')
        commands = packets(trace)
        cases = []
        for flags in range(4):
            folder = root/f'nes-seal632-{flags}-{phase}a'
            r = read(folder/'audit.json')
            assert r['frames']==47 and r['client']==sha(client/'sink165.sfc')
            assert len(r['heads'])==len(commands[951])==30
            control = cases[0]['ack'] if cases else r['ack']
            subset = [e for e in cpu[951] if e['op']==3]
            after = r['heads'][-2]
            cases.append(dict(flags=flags, interval=r['interval'], seal_ms=r['seal_ms'],
                              upload_ms=r['upload_ms'], first_seal_DMA_ms=r['dma_ms'], ack=r['ack'],
                              ack_delta_control_ms=ms(r['ack']-control),
                              ack_delta_625_ms=ms(r['ack']-one(subset,'ack')['clock']),
                              last_HDMA_service_ms=ms(after['ack']-after['load']),
                              trace=r['trace'], arrivals=r['offers']))
        bank = csv_groups(trace/'seal528.csv')
        reuse = {}
        def section(gen, section):
            buf = bytearray()
            wire = 0
            for h,_,_ in commands[gen]:
                if h[1]!=section:
                    continue
                offset, n, span = [int.from_bytes(h[i:i+2],'little') for i in (10,12,14)]
                assert len(buf)==offset and len(h)==16+n and h[0] in (2,4,8) and n>0
                assert h[0]==2 or span%n==0
                buf.extend(h[16:] if h[0]==2 else h[16:]*(span//n))
                wire += len(h)+3
            return buf, wire
        for gen in (951,952,953,954,955,957):
            assert one(bank[gen],'final_credit')['bank']==one(bank[gen-2],'final_credit')['bank']
            sizes = {}
            for name, sec, n in [('palette',3,512),('OAM',4,544)]:
                before,_ = section(gen-2,sec)
                now,wire = section(gen,sec)
                assert len(before)==len(now)==n
                changes=[i for i in range(n) if before[i]!=now[i]]
                sizes[name]=dict(changed_B=len(changes),last_change=max(changes,default=None),E1_B=wire)
            reuse[gen]=sizes
        spi = [e for e in read(trace/'events.json') if e['generation']==951 and e.get('opcode')=='0xe1']
        phases.append(dict(phase=phase,cases=cases,bank_reuse= reuse,
                           final_HDMA_push_ms=ms(spi[-2]['clock']-r['cutoff']),
                           hashes={k:sha(trace/k) for k in ('events.json','packets.jsonl','window.csv')}))
    report=dict(phases=phases,build=read(client/'build.json'),client=sha(client/'sink165.sfc'),
                guards=read(root/'nes-seal632-edges-b'/'guards.json'))
    out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('root','client','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    analyze(a.root,a.client,a.out)
