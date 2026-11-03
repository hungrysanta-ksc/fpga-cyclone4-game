# SPDX-License-Identifier: MIT
"""Join the held-word lifetime with the paths of both loader controls and the 53-screen schedule."""
import argparse
import json
from pathlib import Path
from analyze_nes_owner562 import board, read
from analyze_nes_reuse565 import pin_budget, table
from nes_raw506 import sha


def paths(folder, direct):
    assert table(folder/'plan569-registers.tsv')==[dict(held='16',saved='0' if direct else '16',fields='16')]
    rows=table(folder/'plan569.tsv')
    prefix='direct' if direct else 'saved'
    absent='saved' if direct else 'direct'
    assert not any(r['path'].startswith(absent) for r in rows)
    result={}
    for corner in sorted({r['corner'] for r in rows}):
        legs={}
        for k in ('setup','hold'):
            rr=[r for r in rows if r['corner']==corner and r['check']==k and r['path'].startswith(prefix)]
            by_bit={int(r['path'][len(prefix):]):r for r in rr}
            assert len(rr)==16 and sorted(by_bit)==list(range(16))
            for i,r in by_bit.items():
                assert r['from'].endswith(f'|held[{i}]')
                expected='reader' if i==15 else (f'batch_length[{i-5}]' if i>=5 else f'remaining[{i}]')
                assert r['to'].endswith('|'+(expected if direct else f'received[{i}]')),(i,r)
            legs[k]=dict(worst=min(rr,key=lambda r:float(r['slack'])),bit14=by_bit[14],
                         slack_ns=[float(by_bit[i]['slack']) for i in range(16)],
                         delay_ns=[float(by_bit[i]['delay']) for i in range(16)])
        result[corner]=dict(**legs,nes=[r for r in rows if r['corner']==corner and r['path']=='nes'])
    assert len(result)==3
    return result


def cost(folder, base, control, inputs, diff):
    changes={n:sha(folder/n) for n in inputs if sha(folder/n)!=sha(base/n)}
    assert sorted(changes)==['nes_native_mailbox206.sv','nes_plan_batch206.sv']
    assert all(diff['modules'][n]==h for n,h in changes.items())
    data=board(folder);old=control['rows']
    assert data['rows'].keys()==old.keys()
    reg={k:[old[k],r] for k,r in data['rows'].items() if r[0]<min(0,old[k][0])}
    ucp=data['unconstrained'];old_ucp=control['unconstrained']
    assert ucp.keys()==old_ucp.keys() and all(ucp[v].keys()==old_ucp[v].keys() for v in ucp)
    no_growth=all(len(row)==len(old_ucp[v][k]) and all(n<=b for n,b in zip(row,old_ucp[v][k]))
                  for v,x in ucp.items() for k,row in x.items())
    related=all(data['fit'][v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
    pins=pin_budget(folder)
    global_paths=table(folder/'arg564-paths.tsv')
    oe={r['corner']:float(r['slack']) for r in global_paths if r['cut']=='OE'}
    assert len(oe)==3
    return dict(changes=changes,fit=data['fit'],SOF=data['SOF'],STA=data['STA'],rows=data['rows'],worst=data['worst'],
                unconstrained=ucp,no_ucp_growth=no_growth,regressions=reg,related_pass=related,psram=pins,OE_ns=oe,
                global_endpoints=[r for r in global_paths if r['cut']=='nes' or '|clk[' in r['cut']],
                board_gate=related and no_growth and not reg and pins['worst_ns']>0 and min(oe.values())>=0)


def main():
    p=argparse.ArgumentParser()
    for key in ('traces','rtl','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();analysis=Path(__file__).resolve().parents[1]/'analysis'
    prior=read(analysis/'end568-verification.json')
    control=read(analysis/'owner562-verification.json')['boards']['MMC558']
    inputs=read(analysis/'trial558-verification.json')['inputs']
    proof=read(a.rtl/'result.json')
    assert proof['early_credit_rejected'] and all(r['E9']==3 for r in proof['direct']['phases'])
    out=dict(rtl=proof,boards={},replays=[])
    for name,old,new in [('end_only','nes-end568-board01','nes-plan569-board01'),('original','nes-mailbox567-board03','nes-plan569-board02')]:
        base=a.traces/old;folder=a.traces/new
        for f,h in proof['reference']['modules'].items():assert sha(base/f)==h
        for f,h in proof['direct']['modules'].items():assert sha(folder/f)==h
        out['boards'][name]=dict(base_registers=table(base/'plan569-registers.tsv')[0],
                                candidate_registers=table(folder/'plan569-registers.tsv')[0],
                                base_paths=paths(base,False),candidate_paths=paths(folder,True),
                                candidate=cost(folder,base,control,inputs,proof['direct']))
    for i,phase in enumerate(prior['replays'],1):
        ref=a.traces/f'nes-end568-play{i}';d=a.traces/f'nes-plan569-play{i}'
        assert read(d/'audit.json')==phase['audit']
        for f in ('arrivals.tsv','bank561.csv','window.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(ref/f)==sha(d/f),f
        out['replays'].append(phase)
    out['scope']='Real plan SPI/CRC/dual-clock decoder, scheduled generation 954 E8/E9 and external tile completion, separately replayed 53-frame consumer. No physical FPS measurement.'
    a.out.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
