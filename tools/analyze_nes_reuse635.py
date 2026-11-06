# SPDX-License-Identifier: MIT
"""Compare the paid command, proof schedule and final PPU transfers."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_map628 import csv_groups, ms, one, read, sha


def summarize(root, probes):
    arm=read(probes/'arm02.json')
    phases=[]
    for phase in (1,2):
        ref=read(root/f'nes-bank633-control-{phase}a/audit.json')
        runs={}
        choices={'blocking_full':('a','collapse'),'blocking_short':('b','collapse'),
                 'idle_control':('d','control'),'idle_short':('e','collapse'),
                 'idle_full':('f','collapse')}
        for name,(suffix,mode) in choices.items():
            folder=root/f'nes-reuse635-{mode}-{phase}{suffix}'
            audit=read(folder/'audit.json')
            rows=csv_groups(folder/'window.csv')
            seal=[r for r in rows[951] if r['op']==3]
            gate=one(seal,'final_upload212_same_blank212')
            q=list(csv.DictReader((folder/'queue.csv').read_text().splitlines()))
            assert max(int(x['depth']) for x in q)<=4
            assert audit['frames']==47 and len(audit['overlap']['scheduled'])==7
            proof=[r for r in rows[951] if r['event']=='proof635']
            if name=='idle_short':
                assert audit['interval']==3 and audit['show']['line']<=246 and audit['ack']<ref['ack']
                assert [r['value'] for r in proof]==list(range(0,512,16))+list(range(624,1056,16))
                head=[r for r in rows[951] if r['op']==9]
                assert all(r['op']==-1 for r in proof)
                assert proof[-1]['clock']<one(head,'load')['clock']
                control=csv_groups(root/f'nes-reuse635-control-{phase}d/window.csv')
                for g in range(905,951):
                    assert [r for r in rows[g] if r['event']!='proof635']==control[g]
                witness=read(root/f'nes-reuse635-collapse-{phase}d/audit.json')
                assert audit['ack']==witness['ack'] and audit['show']==witness['show']
            reuse=[r for r in rows[951] if r['op']==9]
            runs[name]=dict(interval=audit['interval'],reveal_line=audit['show']['line'],
                final_grant_line=gate['line'],reveal_margin_ms=ms(audit['cutoff']-audit['show']['clock']),
                seal_vs_cutoff_ms=ms(audit['seal']-audit['cutoff']),
                ACK=audit['ack'],ACK_vs_625_ms=ms(audit['ack']-ref['ack']),
                prior_reveal_delta_ms=ms(audit['previous']-ref['previous']),
                command_ms=ms(one(reuse,'ack')['clock']-one(reuse,'load')['clock']) if reuse else None,
                proof_chunks=len(proof),proof_before_command_ms=ms(one(reuse,'load')['clock']-proof[-1]['clock']) if proof and reuse else None,
                final_DMA_B=[r['value'] for r in seal if r['event']=='ppu_dma'][-2:],
                queue_max=max(int(x['depth']) for x in q),client=audit['client'],
                audit=sha(folder/'audit.json'),trace=sha(folder/'window.csv'),offers=audit['offers'])
        runs['idle_short']['ACK_vs_same_binary_control_ms']=ms(runs['idle_short']['ACK']-runs['idle_control']['ACK'])
        free=read(root/f'nes-overlap634-restore-collapse-{phase}c/audit.json')
        runs['idle_short']['ACK_vs_634_free_ms']=ms(runs['idle_short']['ACK']-free['ack'])
        phases.append(dict(phase=phase,runs=runs))
    sources=['tools/nes_reuse635.py','tools/prepare_nes_reuse635.py','tools/check_nes_reuse635_arm.py',
             'tools/replay_nes_reuse635.py','tools/check_nes_reuse635.py','tools/replay_nes_bank633.py',
             'tools/replay_nes_overlap634.py']
    return dict(source_hashes={name:sha(Path(name)) for name in sources},scope='Actual linked ARM unit producer and 47-screen actual 65816 replay; recorded ARM source schedule with explicit added command cost, no complete new FPGA/IRQ/capture run.',
                phases=phases,ARM=arm,Flash_limit_B=212992,Flash_over_B=arm['firmware_B']-212992,
                added_ARM_BSS_B=952,SPI_saved_951_B=384,
                clients={x:read(probes/x/'build.json') for x in ('client','client02','client04','client05')},
                guards=read(root/'nes-reuse635-guards04/guards.json'),
                raw_root=str(root),probes=str(probes))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('root','probes','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(summarize(a.root,a.probes),indent=2)+'\n')
