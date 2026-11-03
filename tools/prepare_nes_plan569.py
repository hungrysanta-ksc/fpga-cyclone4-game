# SPDX-License-Identifier: MIT
"""Let WAIT capture the sealed host word. Keep its reservation until the last CHECK."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_end568 import prepare as end568
from prepare_nes_mailbox567 import prepare as mailbox567


def prepare(base, out, original_loader=False):
    if original_loader:
        mailbox567(base, out, local_ports=True)
    else:
        end568(base, out)
    box = out/'nes_native_mailbox206.sv'
    s = once(box.read_text(), 'parameter WIDTH=96', 'parameter WIDTH=96, parameter CONSUMER_CAPTURE=0')
    s = once(s, ' assign dst_data=received;', ''' // In consumer-capture mode only sample dst_data on the destination clock
 // while dst_valid is high. held cannot change until the synchronized ACK.
 assign dst_data=CONSUMER_CAPTURE ? held : received;''')
    box.write_text(s, newline='\n')
    plan = out/'nes_plan_batch206.sv'
    s = once(plan.read_text(), '#(.WIDTH(16)) control', '#(.WIDTH(16),.CONSUMER_CAPTURE(1)) control')
    plan.write_text(s, newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--original-loader',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.original_loader)
