"""Materialize the registered destination of the held EB mailbox on the 963 board."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once
from prepare_nes_frame900 import fit, QUARTUS


def project(temp):
    old = temp/'nes-trial816-board963'
    new = temp/'nes-trial816-board964'
    new.mkdir()
    for name in ('rtl','sys'):
        shutil.copytree(old/name,new/name)
    for f in old.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(f,new/f.name)
    direct = new/'nes_direct206.sv'
    direct.write_text(once(direct.read_text(),'.WIDTH(26),.CONSUMER_CAPTURE(1)',
                           '.WIDTH(26),.CONSUMER_CAPTURE(0)'),newline='\n')
    # The consumer sees only the destination-domain register. The source holds
    # every bit until the acknowledged transfer returns through two flops.
    name='nes_live_joint:core|nes_direct206:direct_path|nes_native_mailbox206:page_mail963|'
    constraints=[]
    def bound(a,b,limit):
        paths=f'-from [cdc181_exact {{{name+a}}}] -to [cdc181_exact {{{name+b}}}]'
        constraints.extend([f'set_max_delay {limit} {paths}',f'set_false_path -hold {paths}'])
    for bit in range(26):
        bound(f'held[{bit}]',f'received[{bit}]',23.808)
    for a,b in [('request','req_sync[0]'),('acknowledge','ack_sync[0]'),
                ('dr[1]','up_src[0]'),('sr[1]','up_dst[0]')]:
        bound(a,b,11.904)
    # Only the asynchronous clear pins of the two reset-release chains.
    # Recovery from their local second stage to the functional flops stays timed.
    for domain in ('sr','dr'):
        for i in range(2):
            constraints.append(f'set_false_path -to [cdc576_pin {{{name}{domain}[{i}]}}]')
    with (new/'board.sdc').open('a',newline='\n') as f:
        f.write('\n'+'\n'.join(constraints)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--fit',action='store_true')
    a=p.parse_args()
    project(a.temp)
    if a.fit:
        fit(a.temp,964,QUARTUS)
