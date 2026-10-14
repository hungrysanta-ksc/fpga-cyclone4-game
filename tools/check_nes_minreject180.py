# SPDX-License-Identifier: MIT
"""Reconstruct three-bit episode witness and verify actual routed gates."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_minreject180 import prepare,CHANGED
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements


def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','fit','test','reproduce','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--io',type=Path)
    a=p.parse_args();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');assert prepare(a.baseline,a.reproduce)==m
    old=load(ROOT/'analysis/reject180-verification.json');v=old['verification']
    assert m['baseline']==v['sources'] and v['native_frame_control_unchanged'] and v['functional']['passed']
    for n,h in m['sources'].items():
        assert sha(a.fit/n)==sha(a.reproduce/n)==h,n
        if n not in CHANGED:assert h==m['baseline'][n],n
    t=load(a.test/'result.json');assert t['passed'] and t['sources']==m['sources']
    # The observer and three-bit witness share the NES clock; no new CDC.
    s=(a.fit/'nes_live_joint.sv').read_text();top=(a.fit/'fxpak_nes_screen137_top.sv').read_text()
    assert 'queue_clk=ext_clk,clk=ext_clk' in s and '.ext_clk(SNES_SYSCLK)' in top
    observer=top.split('nes_run_observer134 observer(',1)[1].split(');',1)[0]
    assert '.clk(SNES_SYSCLK)' in observer
    assert 'reg armed,owned_seen,previous_bad;' in (a.fit/'nes_reject_witness180.sv').read_text()
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
    for n in ['tools/check_nes_minreject180.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:public[n]=sha(ROOT/n)
    f=inspect(a.fit);nm=nominal(a.fit)
    result=dict(passed=bool(f['fit_pass'] and nm['passed'] and io and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']),fit=f,nominal=nm,io=io,
        sources=m['sources'],public_sources=public,changed=CHANGED,functional=t,source_reproduced=True,
        game_path_unchanged=True,observer_same_clock=True,snes_mif_4096_equal=True,preserved_routed_db_files=len(db),
        schema=3,physical=False,video_fix=False,fps60=False,full_io_signoff=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],le=f['fit_le'],labs=f['used_labs'],setup=nm['worst_setup']['slack'],io_checked=io is not None)))


if __name__=='__main__':main()
