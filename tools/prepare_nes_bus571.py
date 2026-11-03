# SPDX-License-Identifier: MIT
"""Keep the asynchronous aperture kill and use its host-local release as the sole reset owner."""
import argparse
from pathlib import Path
from nes_raw506 import once
from prepare_nes_gate570 import prepare as gate570


def prepare(base, out, read_mask=False, owner_mux=False):
    gate570(base,out,local_release=True)
    if read_mask:
        aperture=out/'nes_bulk_aperture188.sv'
        s=aperture.read_text()
        assert '.raw_reset(reset||stop||!active),.reset(local_reset)' in s
        s=once(s,'assign chunk_ready=enabled&&sealed[reader];',
               'assign chunk_ready=!local_reset&&sealed[reader];')
        s=once(s,'assign dir=enabled&&!read_n&&write_n&&selected;',
               'assign dir=!local_reset&&!read_n&&write_n&&selected;')
        aperture.write_text(s,newline='\n')
        return
    bulk=out/'nes_tile_bulk206.sv'
    s=bulk.read_text()
    assert 'hcancel(.clk(host_clk),.raw_reset(hr||source_failed||host_failed),.reset(hc))' in s
    s=once(s,"  .clk(host_clk),.reset(hr),.active(1'b1),.stop(hc),","""  // hc already asserts asynchronously with hr and releases after it.
  // A separate hr mask here adds an output path around that release chain.
  .clk(host_clk),.reset(1'b0),.active(1'b1),.stop(hc),""")
    bulk.write_text(s,newline='\n')

    if owner_mux:
        top=out/'fxpak_nes_screen137_top.sv'
        s=once(top.read_text(),'assign consumer_dir=!consumer_oe&&(sink_oe204?bus_dir:sink_dir204);',
               'assign consumer_dir=!core_reset&&((sink_oe204&&!bus_oe_n&&bus_dir)||(!sink_oe204&&bus_oe_n&&sink_dir204));')
        # A read grant implies exactly one owner, hence consumer_oe is low.
        # A receive-only status write must leave the data pins tri-stated.
        s=once(s,"assign SNES_DATA=SNES_DATABUS_DIR&&!SNES_DATABUS_OE?consumer_data:8'hzz;",
                 "assign SNES_DATA=consumer_dir?consumer_data:8'hzz;")
        top.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument('--'+k,type=Path,required=True)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--read-mask',action='store_true');group.add_argument('--owner-mux',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.read_mask,a.owner_mux)
