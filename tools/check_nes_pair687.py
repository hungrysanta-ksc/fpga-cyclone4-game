"""Actual linked bounded map pairs with independent payload/credit oracle."""
import argparse,inspect,json
from pathlib import Path
import check_nes_pair683 as prior
from nes_raw506 import once,sha

def checks(src,renew=False,pending=False):
    s=inspect.getsource(prior.run)
    s=once(s,"('cold','early_cold','handoff_cold')","('cold','early_cold','handoff_cold','handoff_coldlong')")
    s=once(s,"mask=sum(1<<i for i in groups);",'''if case in ('handoff_long','handoff_coldlong','handoff_tilelong','handoff_midSTOP','handoff_badcredit','handoff_badplan','handoff_pending'):groups=list(range(18))
    if case=='handoff_gaplong':groups=list(range(3))+list(range(4,19))
    if case=='handoff_shortlong':groups=list(range(17))
    mask=sum(1<<i for i in groups);''')
    s=once(s,"if case in ('STOP','early_STOP','handoff_STOP'):","if case in ('STOP','early_STOP','handoff_STOP') or (case=='handoff_midSTOP' and len(payload)==3):")
    s=once(s,"case in ('bad_credit','early_bad_credit')","case in ('bad_credit','early_bad_credit','handoff_badcredit')")
    s=once(s,"^(case=='bad_plan')","^(case=='bad_plan' or (case=='handoff_badplan' and len(payload)==2))")
    s=once(s,"if case=='handoff_tile':","if case in ('handoff_tile','handoff_tilelong'):")
    s=once(s,"'early_bad_credit','handoff_STOP')","'early_bad_credit','handoff_STOP','handoff_midSTOP','handoff_badcredit','handoff_badplan')")
    s=once(s,"assert queries==expected,(case,queries,expected)",'''expected={'handoff_long':[2,4],'handoff_coldlong':[1,2,3,4,5],'handoff_tilelong':[1,2,3,4,5],
              'handoff_gaplong':[1,3,5],'handoff_shortlong':[2,4,5],
              'handoff_midSTOP':[2],'handoff_badcredit':[2,4],'handoff_badplan':[2],'handoff_pending':[2,3,5]}.get(case,expected)
    assert queries==expected,(case,queries,expected)
    if case=='handoff_midSTOP':assert len(payload)==3
    if case=='handoff_badcredit':assert len(payload)==4
    if case=='handoff_badplan':assert len(payload)==2''')
    if renew:s=once(s,"'handoff_tilelong':[1,2,3,4,5]","'handoff_tilelong':[1,3,5]")
    if pending:
        s=once(s,"elif tx[0]==0xe0:",'''    if case=='handoff_pending' and len(payload)==3:
                m.put(m.p,'nes_plan200','bulk_pending',1,1)
                m.put(m.p,'nes_plan200','bulk_until',sent-1,2)
        elif tx[0]==0xe0:''')
    ns=dict(vars(prior));exec(s,ns)
    cases=('handoff_long','handoff_coldlong','handoff_tilelong','handoff_gaplong','handoff_shortlong','handoff_midSTOP','handoff_badcredit','handoff_badplan')
    if pending:cases+=('handoff_pending',)
    rows=[]
    for c in cases:rows.append(ns['run'](src,c,handoff=True));print(c,'PASS',flush=True)
    if renew:
        from check_nes_bg684 import run as bg
        for c in ('pair','cold','gap','short','three','early','early_long','early_cold','early_planner','early_gap','STOP','bad_plan','credit','bad_credit','bad_identity','handoff','handoff_gap','handoff_short','handoff_tile','handoff_cold','handoff_STOP','handoff_credit'):
            rows.append(ns['run'](src,c));print(c,'PASS',flush=True)
        for c in ('normal','cold','tile','ordinary','RLE','gap','short','no_prefix','credit','bad_credit','STOP'):
            rows.append(bg(src,c));print('BG',c,'PASS',flush=True)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--renew-head',action='store_true');p.add_argument('--pending-first',action='store_true');a=p.parse_args()
    rows=checks(a.arm,a.renew_head,a.pending_first)
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,
        scope='Actual M4/window; exact query positions, CRC/sequence/payload, max4credit, STOP between paired sends, no display/EA grant. Producer mock, full timing separate.'),indent=2)+'\n')
