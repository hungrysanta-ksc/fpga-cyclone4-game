# SPDX-License-Identifier: MIT
"""Gate passive180 witness with exact reconstruction, functional and routed IO."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_reject180 import prepare
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements


def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','fit','test','reproduce','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--io',type=Path)
    a=p.parse_args();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');r=prepare(a.baseline,a.reproduce);assert m==r
    for n,h in m['sources'].items():assert sha(a.fit/n)==sha(a.reproduce/n)==h,n
    t=load(a.test/'result.json');assert t['passed'] and t['sources']==m['sources']
    # The sole native-frame changes are output declarations and passive assigns.
    s=(a.fit/'nes_native_frame165.sv').read_text()
    s=s.replace('output reg [24:0] errors,output wire [24:0] observe_errors180,\n output wire observe_collecting180,output wire scroll_seen,','output reg [24:0] errors,output wire scroll_seen,')
    s=s.replace('assign observe_errors180={rom_fault,raster_errors,compact_errors,fetch_errors};\n assign observe_collecting180=joining || owned;\n ','')
    assert s==(a.baseline/'nes_native_frame165.sv').read_text()
    for n in ['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_export165.sv','nes_native_fill165.sv','nes_native_arbiter165.sv','sink-program.hex','board.sdc']:
        assert sha(a.fit/n)==m['baseline'][n],n
    mif,=a.fit.glob('db/board.ram*_nes_sink_bus165_*.hdl.mif')
    image={int(i):int(v,2) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M)}
    assert len(image)==4096 and bytes(image[i] for i in range(4096))==bytes.fromhex((a.baseline/'sink-program.hex').read_text())
    db={};io=None
    if a.io:
        for n,h in m['sources'].items():assert sha(a.io/n)==h,n
        db={p.relative_to(a.fit).as_posix():sha(p) for p in (a.fit/'db').rglob('*') if p.is_file() and not p.name.endswith('.taw.rdb') and '_io_sim_cache.' not in p.name}
        for n,h in db.items():assert sha(a.io/n)==h,n
        assert sha(a.io/'nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
        io=measurements(a.io)
    public=m['public_sources']|t['public_sources']
    for n,h in public.items():assert sha(ROOT/n)==h,n
    for n in ['tools/check_nes_reject180_fpga.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:public[n]=sha(ROOT/n)
    f=inspect(a.fit);nm=nominal(a.fit)
    result=dict(passed=bool(f['fit_pass'] and nm['passed'] and io and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']),fit=f,nominal=nm,io=io,
        sources=m['sources'],public_sources=public,changed=m['changed'],added=m['added'],functional=t,source_reproduced=True,
        native_frame_control_unchanged=True,snes_mif_4096_equal=True,preserved_routed_db_files=len(db),physical=False,video_fix=False,fps60=False,full_io_signoff=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],le=f['fit_le'],labs=f['used_labs'],setup=nm['worst_setup']['slack'],io_checked=io is not None)))


if __name__=='__main__':main()
