# SPDX-License-Identifier: MIT
"""Verify shared invalid-context storage, unchanged game path and routed gates."""
from pathlib import Path
import argparse,json,re
from nes_game147 import ROOT,sha
from nes_rejectstorage180 import prepare,CHANGED
from check_nes_check165 import inspect
from check_nes_retire165 import nominal
from check_nes_boundary165 import measurements


def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','fit','test','reproduce','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--io',type=Path)
    a=p.parse_args();load=lambda p:json.loads(p.read_bytes())
    m=load(a.fit/'preparation.json');assert prepare(a.baseline,a.reproduce)==m
    old=load(ROOT/'analysis/reject180-verification.json')['verification']
    assert m['baseline']==old['sources'] and old['native_frame_control_unchanged']
    for n,h in m['sources'].items():
        assert sha(a.fit/n)==sha(a.reproduce/n)==h,n
        if n not in CHANGED:assert h==m['baseline'][n],n
    t=load(a.test/'result.json');assert t['passed'] and t['sources']==m['sources']
    s=(a.fit/'nes_run_observer134.sv').read_text()
    prior=(a.baseline/'nes_run_observer134.sv').read_text()
    # No new storage declaration in the observer; all added declarations are wires.
    regs=lambda x:re.findall(r'\breg\s+[^;]+;',x)
    assert regs(s)==regs(prior)
    anchor='if(fault_trigger && !context_valid)begin context_valid<=1;first_context<=fault_context;first_ppu154<=ppu_fault_state154;end'
    assert anchor in prior and anchor+'\n   else if(!context_valid)begin' in s
    live=(a.fit/'nes_live_joint.sv').read_text();top=(a.fit/'fxpak_nes_screen137_top.sv').read_text()
    assert 'nes_reject_witness180 witness(' not in live
    assert 'queue_clk=ext_clk,clk=ext_clk' in live and '.ext_clk(SNES_SYSCLK)' in top
    assert '.clk(SNES_SYSCLK)' in top.split('nes_run_observer134 observer(',1)[1].split(');',1)[0]
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
    for n in ['tools/check_nes_rejectstorage180.py','tools/check_nes_check165.py','tools/check_nes_retire165.py','tools/check_nes_boundary165.py','tools/nes_boundary165_paths.tcl']:public[n]=sha(ROOT/n)
    fitlog=(a.fit/'fit.log').read_text(errors='replace')
    if 'Fitter was successful' in fitlog:
        f=inspect(a.fit);nm=nominal(a.fit)
    else:
        cap=re.search(r'Fitter requires (\d+) LABs.*contains only (\d+) LABs',fitlog)
        assert cap and not a.io
        f=dict(fit_pass=False,required_labs=int(cap[1]),available_labs=int(cap[2]))
        nm=None
    result=dict(passed=bool(f['fit_pass'] and nm['passed'] and io and io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']),fit=f,nominal=nm,io=io,
        sources=m['sources'],public_sources=public,changed=CHANGED,functional=t,source_reproduced=True,
        game_path_unchanged=True,observer_same_clock=True,observer_register_declarations_unchanged=True,
        invalid_context_payload_unspecified=True,first_fault_priority_preserved=True,
        snes_mif_4096_equal=True,preserved_routed_db_files=len(db),
        schema=2,physical=False,video_fix=False,fps60=False,full_io_signoff=False)
    assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],fit=f if not f['fit_pass'] else f['used_labs'],setup=nm['worst_setup']['slack'] if nm else None,io_checked=io is not None)))


if __name__=='__main__':main()
