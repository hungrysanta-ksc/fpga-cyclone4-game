# SPDX-License-Identifier: MIT
"""Tie changed178 RTL/ROM to executed tests and routed evidence; no hardware claim."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_clip178_fpga import prepare
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','fit','raster-test','display-test','packet-test','reproduce','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--io',type=Path)
    a=p.parse_args();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');r=prepare(a.baseline,a.reproduce)
    assert m==r
    for n,h in m['sources'].items():assert sha(a.fit/n)==sha(a.reproduce/n)==h,n
    rt=load(a.raster_test/'result.json');dt=load(a.display_test/'result.json');pt=load(a.packet_test/'result.json')
    assert rt['passed'] and dt['passed'] and pt['passed']
    assert rt['candidate_sha256']==m['sources']['nes_native_raster_frame165.sv']
    assert sha(a.fit/'client178/sink165.sfc')==sha(a.display_test/'client/sink165.sfc')==pt['client_sha256']
    assert sha(a.fit/'sink-program.hex')==sha(a.display_test/'client/sink-program.hex')
    public=m['public_sources']|rt['public_sources']|dt['public_sources']|pt['public_sources']
    for n,h in public.items():assert sha(ROOT/n)==h,n
    for n in ['tools/check_nes_clip178_fpga.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:public[n]=sha(ROOT/n)
    mif,=a.fit.glob('db/board.ram*_nes_sink_bus165_*.hdl.mif')
    rows=re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M)
    image={int(i):int(v,2) for i,v in rows};assert len(image)==4096
    assert bytes(image[i] for i in range(4096))==bytes.fromhex((a.fit/'sink-program.hex').read_text())
    f=inspect(a.fit);nm=nominal(a.fit);io=None;preserved={}
    if a.io:
        for n,h in m['sources'].items():assert sha(a.io/n)==h,n
        preserved={p.relative_to(a.fit).as_posix():sha(p) for p in (a.fit/'db').rglob('*') if p.is_file() and not p.name.endswith('.taw.rdb') and '_io_sim_cache.' not in p.name}
        for n,h in preserved.items():assert sha(a.io/n)==h,n
        assert sha(a.io/'nes_boundary165_paths.tcl')==sha(ROOT/'tools/nes_boundary165_paths.tcl')
        io=measurements(a.io)
    result=dict(passed=bool(f['fit_pass'] and nm['passed'] and io and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']),fit=f,nominal=nm,io=io,public_sources=public,sources=m['sources'],changed=m['changed'],unchanged_files=len(m['sources'])-2,source_byte_reproduction=True,snes_mif_4096_equal=True,preserved_routed_db_files=len(preserved),raster=rt,display=dt,packets=pt,physical=False,fps60_proven=False,full_io_signoff=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],setup=nm['worst_setup']['slack'],le=f['fit_le'],labs=f['used_labs'],io_checked=io is not None)))
if __name__=='__main__':main()
