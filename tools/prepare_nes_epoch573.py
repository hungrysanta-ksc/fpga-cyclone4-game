# SPDX-License-Identifier: MIT
"""Compare fitter register-control mapping and uninterrupted Gray sampling on 572 START."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_start572 import prepare as start572


def prepare(base, out, mode):
    start572(base, out, 'loader')
    if mode == 'pair':
        # The physical MMC558 pair occupies two adjacent LEs in this LAB.
        # Leave the publishing register and all other synchronizers unconstrained.
        qsf = out / 'board.qsf'
        with qsf.open('a', newline='\n') as f:
            for stage, n in [('epoch_meta',9),('epoch_sync',7)]:
                target = 'nes_live_joint:core|nes_spi_boot:loader_boot|nes_source_epoch207:content_lifetime|' + stage + '[23]'
                f.write(f'\nset_location_assignment FF_X26_Y22_N{n} -to {target}\n')
        return
    path = out / 'nes_source_epoch207.sv'
    s = path.read_text()
    if mode == 'mapping':
        s = once(s, 'SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS',
                 'SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS; -name ALLOW_SYNCH_CTRL_USAGE OFF')
    else:
        first = s.index(' always @(posedge nes_clk or posedge cold_reset)')
        end = s.index(' always @(posedge nes_clk or posedge held)', first)
        s = s[:first] + ''' // Both data flops only sample; their contents become visible after two
 // fresh NES edges. STOP clears the validity pipe even without a clock.
 reg [1:0] sample_valid;
 always @(posedge nes_clk)begin
  epoch_meta<=gray;
  epoch_sync<=epoch_meta;
 end
 wire [31:0] visible_epoch=sample_valid[1]?epoch_sync:32'd0;
 always @(posedge nes_clk or posedge cold_reset)begin
  if(cold_reset)begin sample_valid<=0;previous<=0;end
  else begin sample_valid<={sample_valid[0],1'b1};previous<=visible_epoch;end
 end
''' + s[end:]
        s = once(s, 'admitted<=epoch_sync==previous;', 'admitted<=visible_epoch==previous;')
        s = once(s, 'assign live_epoch=epoch_sync;', 'assign live_epoch=visible_epoch;')
    path.write_text(s, newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=['mapping', 'sampling', 'pair'], required=True)
    a = p.parse_args()
    prepare(a.base,a.out,a.mode)
