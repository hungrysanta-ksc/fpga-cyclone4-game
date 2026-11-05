"""Extend the reviewed mailbox CDC rules to the previously omitted rearm instance.
Only first synchronization data stages and the four asynchronous release pins.
No functional data path, second-stage check, or ROM IO budget is waived.
"""
import argparse
from pathlib import Path

def text():
    base='nes_live_joint:core|nes_direct206:direct_path|nes_plan_batch206:transport|nes_native_mailbox206:rearm|'
    s='# 611: rearm uses the identical mailbox206 reset/ready handshake.\n'
    for src,dst,period in [('sr[1]','up_dst[0]',45.454),('dr[1]','up_src[0]',11.904)]:
        a,b=base+src,base+dst
        s+=f'set_max_delay {period} -from [cdc181_exact {{{a}}}] -to [cdc181_exact {{{b}}}]\n'
        s+=f'set_false_path -hold -from [cdc181_exact {{{a}}}] -to [cdc181_exact {{{b}}}]\n'
    for n in ('sr[0]','sr[1]','dr[0]','dr[1]'):
        s+=f'set_false_path -to [cdc576_pin {{{base+n}}}]\n'
    return s

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(text(),newline='\n')
