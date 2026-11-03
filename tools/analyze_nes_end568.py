# SPDX-License-Identifier: MIT
"""Join differential loader behavior, full board gates and all 32 placed epoch bits."""
import argparse
import json
from pathlib import Path
from analyze_nes_owner562 import board, read
from analyze_nes_reuse565 import table, pin_budget
from nes_raw506 import sha


def epochs(folder):
    rows=table(folder/'epoch568.tsv')
    corners={}
    for corner in sorted({r['corner'] for r in rows}):
        group=[r for r in rows if r['corner']==corner]
        legs={}
        for path, source, dest in [('input','gray','epoch_meta'),('sync','epoch_meta','epoch_sync')]:
            bits=[r for r in group if r['path']==path]
            assert sorted(int(r['bit']) for r in bits)==list(range(32))
            for r in bits:
                assert r['from'].endswith(f"|{source}[{r['bit']}]") and r['to'].endswith(f"|{dest}[{r['bit']}]")
            bits.sort(key=lambda r:int(r['bit']))
            worst=min(bits,key=lambda r:float(r['slack']))
            legs[path]=dict(slack_ns_by_bit=[float(r['slack']) for r in bits],delay_ns_by_bit=[float(r['data_delay']) for r in bits],
                            worst_bit=int(worst['bit']),worst_slack_ns=float(worst['slack']),
                            data_delay_ns=[min(float(r['data_delay']) for r in bits),max(float(r['data_delay']) for r in bits)])
        corners[corner]=dict(**legs,other=[r for r in group if r['path'] not in ('input','sync')])
    assert len(corners)==3
    return dict(corners=corners,report_sha256=sha(folder/'epoch568.tsv'))


def analyze(a):
    analysis=Path(__file__).resolve().parents[1]/'analysis'
    base=a.traces/'nes-mailbox567-board03'
    prior=read(analysis/'mailbox567-verification.json')
    control=read(analysis/'owner562-verification.json')['boards']['MMC558']
    assert sha(base/'output_files/board.sof')==prior['local_ports']['SOF']
    out=dict(base=epochs(base),cases={},replays=[])
    pins=read(analysis/'trial558-verification.json')['inputs']
    for name,b,r in [('end_only','01','02'),('phase_only','02','03'),('late_select','03','04')]:
        folder=a.traces/('nes-end568-board'+b)
        diff=read(a.traces/('nes-end568-rtl'+r)/'result.json')
        changed=[n for n in pins if sha(folder/n)!=sha(base/n)]
        assert changed==['nes_rom_loader.sv'] and sha(folder/changed[0])==diff['loader']
        assert diff['reference']==sha(base/changed[0]) and diff['epoch_rtl']==sha(folder/'nes_source_epoch207.sv')
        full=board(folder)
        regs={k:[control['rows'][k],v] for k,v in full['rows'].items() if v[0]<min(0,control['rows'][k][0])}
        assert control['rows'].keys()==full['rows'].keys()
        ucp=full['unconstrained'];old=control['unconstrained']
        assert ucp.keys()==old.keys() and all(x.keys()==old[v].keys() for v,x in ucp.items())
        no_growth=all(len(row)==len(old[v][k]) and all(n<=o for n,o in zip(row,old[v][k]))
                      for v,x in ucp.items() for k,row in x.items())
        oe={r['corner']:float(r['slack']) for r in table(folder/'arg564-paths.tsv') if r['cut']=='OE'}
        budget=pin_budget(folder)
        related=all(full['fit'][v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
        assert len(oe)==3
        out['cases'][name]=dict(changed=changed,rtl=diff,board=full,epoch=epochs(folder),regressions=regs,OE_ns=oe,
            pin_budget=budget,related_pass=related,no_ucp_growth=no_growth,board_gate=related and not regs and no_growth and min(oe.values())>=0 and budget['worst_ns']>0)
    for phase,ref in enumerate(prior['replays'],1):
        new=a.traces/f'nes-end568-play{phase}';old=a.traces/f'nes-mailbox567-play{phase}'
        assert read(new/'audit.json')==ref['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(new/f)==sha(old/f),f
        out['replays'].append(dict(phase=phase,audit=ref['audit'],intervals=ref['intervals'],dense_ms=ref['dense_ms'],last_ACK=ref['last_ACK']))
    out['scope']='Two real consumer replays of frozen ARM/IRQ/ROM arrivals. Pin RAM middle preinitialized. Epoch high-bit serial positions seeded. Raw first-stage slack and per-bit delay ranges are not MTBF or a CDC waiver.'
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
