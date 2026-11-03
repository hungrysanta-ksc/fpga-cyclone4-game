# SPDX-License-Identifier: MIT
"""Materialize the 565 board, then use the local mailbox state for receiver retirement."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_reuse565 import prepare as prepare565


def prepare(base, out, local_ports=False):
    prepare565(base, out)
    if local_ports:
        # Use the existing 206 implementation under the instance type named
        # by the board's exact CDC endpoint constraints.
        path = out / 'nes_native_mailbox165.sv'
        impl = (out / 'nes_native_mailbox206.sv').read_text()
        source = once(impl, 'module nes_native_mailbox206', 'module nes_native_mailbox165')
        assert source == path.read_text().replace('=!reset&&', '=')
        path.write_text(source, newline='\n')
        return
    path = out / 'nes_native_mailbox165.sv'
    path.write_text(once(path.read_text(), 'if(dst_valid&&dst_ready)begin', '''// dr/up_dst qualify this block. dst_reset clears valid asynchronously;
    // the raw reset mask on the external port need not feed the next-state mux.
    if(valid&&dst_ready)begin'''), newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('base', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--local-ports', action='store_true')
    args = parser.parse_args()
    prepare(args.base, args.out, args.local_ports)
