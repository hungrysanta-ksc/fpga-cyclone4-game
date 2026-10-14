# SPDX-License-Identifier: MIT
"""Bind lifecycle evidence and both rejected observation fits to exact sources."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
import nes_lifecycle175 as events
import nes_snapshot175 as snapshot
from check_nes_check165 import inspect
from check_nes_retire165 import nominal

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','events','snapshot','test','history','arm-root','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();load=lambda p:json.loads(p.read_bytes())
    base=load(ROOT/'analysis/errorzero174-verification.json')['sources']
    for n,h in base.items():assert sha(a.baseline/n)==h,n
    t=load(a.test/'result.json');h=load(a.history/'result.json')
    assert t['passed'] and t['counts']==dict(commits=5,begins=5,ends=5,rejects=3,releases=8,held_frames=23,frames=31)
    assert t['dropped_release_negative_detected'] and h['passed'] and h['negative_detected']
    for n,digest in t['sources'].items():assert digest==base[n] and sha(a.test/n)==digest,n
    variants={}
    for name,d,mod in [('A4-events',a.events,events),('A5-snapshot',a.snapshot,snapshot)]:
        m=load(d/'preparation.json');assert m['baseline']==base
        for n,digest in m['sources'].items():
            assert sha(d/n)==digest,n
            if n in mod.CHANGED:assert (d/n).read_text()==mod.transform(n,(a.baseline/n).read_text()),n
            else:assert digest==base[n],n
        variants[name]=dict(sources=m['sources'],changed=mod.CHANGED,fit=inspect(d),nominal=nominal(d),adopted=False)
        assert not variants[name]['nominal']['passed']
    assert h['sources']==variants['A4-events']['sources']
    assert sha(a.snapshot/'nes_ppu_history157.sv')==base['nes_ppu_history157.sv']
    arms={}
    for name,label,check,report,manifest in [('A4-events','arm01','armcheck02','report01','preparation-lifecycle175.json'),('A5-snapshot','arm02','armcheck03','report02','preparation-snapshot175.json')]:
        ar=load(a.arm_root/check/'result.json');rp=load(a.arm_root/report/'result.json');m=load(a.arm_root/label/manifest)
        assert ar['passed'] and ar['remaining_margin']==1040 and rp['passed']
        assert sha(a.arm_root/label/'src/obj-nes-100/firmware.stm')==ar['firmware_sha256']
        assert rp['source_sha256']==sha(a.arm_root/label/'src/nes_menu_diagnostic.c')
        for n,digest in (m['copied']|m['changed']|m['added']).items():assert sha(a.arm_root/label/n)==digest,n
        arms[name]=dict(check=ar,report=rp,manifest_sha256=sha(a.arm_root/label/manifest),deployed=False)
    public={}
    for result in [t,h,*[x['check'] for x in arms.values()]]:
        public.update(result['public_sources'])
    for n in ['tools/nes_snapshot175.py','tools/nes_snapshot175_mcu.py','tools/check_nes_lifecycle175.py','tools/check_nes_check165.py','tools/check_nes_retire165.py']:
        public[n]=sha(ROOT/n)
    for n,digest in public.items():assert sha(ROOT/n)==digest,n
    r=dict(functional_boundary_passed=True,lifecycle=t,events_history=h,variants=variants,arms=arms,
           selected=None,hardware_package=False,continuous_video_proven=False,frame_rate_approved=False,
           baseline174_sources=base,public_sources=public,physical=False,
           scope='Real deployed174 lifecycle RTL with synthetic PPU/host/memory; A4 event RAM tested; A5 is only output wires and unchanged history hardware. Both builds failed actual memory-clock setup; no new IO/CDC signoff or hardware trial.')
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print('PASS evidence binding; A4/A5 NOT deployable; lifecycle5 commits/3 rejects recovered')

if __name__=='__main__':main()
