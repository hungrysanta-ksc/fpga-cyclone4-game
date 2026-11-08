"""Linked empty-query grant, ready descriptor and receipt-only distinction."""
import argparse,json
from pathlib import Path
from check_nes_pair687 import checks
from check_nes_supply485_arm import ARM,sha

def owner(src,case):
    m=ARM(src,'bad_E8_CRC' if case=='bad_CRC' else 'normal');m.setup()
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',2,1)]:m.put(m.p,'nes_plan200',k,v,n)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.s,'nes_native_sink165','map_pair683',0,1)
    if case=='receipt_only':
        m.put(m.p,'nes_plan200','bulk_valid',1,1)
        m.u.mem_write(m.p+m.layout['nes_plan200']['bulk']+1,b'\x01')
        m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes((2,2)))
    if case=='done':m.endpoint.end=True
    if case=='ready':m.endpoint.jobs=[(0,16,16,1)]
    if case=='STOP':m.endpoint.mode='STOP_after_E9';m.endpoint.accepted=1
    ok=bool(m.call('nes_plan200_progress',[m.p,2]))
    flag=m.get(m.s,'nes_native_sink165','map_pair683')
    assert ok==(case not in ('bad_CRC','STOP')),(case,ok)
    assert flag==int(case=='empty'),(case,flag)
    ops=[int(x[:2],16) for x in m.endpoint.calls]
    assert ops.count(0xe8)==int(case not in ('receipt_only','STOP')),(case,ops)
    if case=='ready':assert m.get(m.p,'nes_plan200','bulk_pending') and m.endpoint.bulk==1
    assert not m.get(m.s,'nes_native_sink165','displayed') and not m.endpoint.rearmed
    return dict(case=case,passed=True,operations=ops,empty_grant=flag,bulk_pending=m.get(m.p,'nes_plan200','bulk_pending'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=checks(a.arm,renew=True,pending=False)
    extra=[owner(a.arm,c) for c in ('empty','receipt_only','done','ready','bad_CRC','STOP')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,owner=extra,
        replaced_fixture='687 injected pending after E1 was not a real producer response; real ready descriptor and receipt-only cases replace that artificial mutation.'),indent=2)+'\n')
    print('PASS688',len(rows),'+',len(extra),'linked guards')
