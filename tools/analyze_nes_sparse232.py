# SPDX-License-Identifier: MIT
"""Check actual232 consumer evidence against sealed231, not physical FPS."""
from pathlib import Path
import argparse,json
from nes_delta231 import BASE,sha
from analyze_nes_geometry230 import packets,summary


def analyze(before,after,synthetic,build):
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    old=read(before/'result.json');new=read(after/'result.json')
    tests=read(synthetic/'result.json');client=read(build/'build.json')
    prior=BASE/'probes/nes-delta231'
    model=read(prior/'analysis03/result.json');rows=[]
    assert old['passed'] and new['passed'] and tests['passed']
    assert len(tests['cases'])==13 and all(c['passed'] for c in tests['cases'])
    assert tests['cases'][0]['mode']=='normal' and tests['cases'][0]['commits']==30
    assert old['commits']==new['commits']==71
    assert new['host_sha256']==old['host_sha256']
    assert new['rom_sha256']=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
    for name in ('body.bin','sink-program.hex','sink165.sfc'):
        assert (build/name).read_bytes()==(after/'client'/name).read_bytes()==(synthetic/'client'/name).read_bytes()
    assert client['body_bytes']==3910 and client['body_free']==26 and client['program_bytes']==4096
    total_bulk=total_wire=0
    for r in model['frame_results']:
        f=r['frame'];g=str(r['generation'])
        for ext in ('geometry','raw','metadata'):
            name=f'frame{f}.{ext}';b=(prior/'test07'/name).read_bytes()
            assert (after/'run'/name).read_bytes()==b==(before/'run'/name).read_bytes(),(f,ext)
        baseline=list(packets((prior/'test07'/f'frame{f}.packets').read_bytes()))
        pp=list(packets((after/'run'/f'frame{f}.packets').read_bytes()))
        # Actual bulk op7 consumes sequence numbers; baseline231 modeled
        # pattern writes outside this transport. Verify actual ordering, then
        # ignore ONLY those two sequence bytes when comparing E1 content.
        assert [int.from_bytes(p[2:4],'little') for p in pp]==list(range(len(pp)))
        content=lambda p:p[:2]+p[4:]
        assert [content(p) for p in pp if p[0]!=7]==[content(p) for p in baseline],(f,'metadata packets')
        assert pp==list(packets((before/'run'/f'frame{f}.packets').read_bytes()))
        bulk=[p for p in pp if p[0]==7]
        assert len(bulk)==r['plans'] and all(len(p)==20 for p in bulk)
        total_bulk+=len(bulk);total_wire+=sum(len(p)+3 for p in pp)
        palette=any(p[0] in (2,4,5,8) and p[1]==3 for p in baseline)
        charge=r['merged_vblank_charge']-(0 if palette else 608)
        v=new['vblanks'][g];ov=old['vblanks'][g]
        if int(g)>2:
            assert (ov>1)==(r['merged_vblank_charge']>4192),(f,'old budget')
            assert (v>1)==(charge>4192),(f,'new budget')
        rows.append(dict(frame=f,generation=int(g),before_vblanks=ov,after_vblanks=v,
                         palette_upload=palette,charge_model=charge,
                         before_charge_model=r['merged_vblank_charge']))
    warm=rows[2:]
    assert total_bulk==new['retired_chunks']==598 and total_wire==131902
    assert total_wire-23*total_bulk==118148
    assert new['vram_bytes']==old['vram_bytes']==133600
    assert new['vram_commands']==old['vram_commands']==478
    return dict(passed=True,stage=232,scope=__doc__,frames=71,warm_frames=69,
        exact_metadata_frames=71,exact_geometry_raw_frames=71,e1_identical_except_verified_sequence=True,
        warm_before_single=sum(r['before_vblanks']==1 for r in warm),
        warm_after_single=sum(r['after_vblanks']==1 for r in warm),
        warm_before_multiple=sum(r['before_vblanks']>1 for r in warm),
        warm_after_multiple=sum(r['after_vblanks']>1 for r in warm),
        remaining_frames=[r['frame'] for r in warm if r['after_vblanks']>1],
        cold_vblanks=[r['after_vblanks'] for r in rows[:2]],
        charge_model=summary([r['charge_model'] for r in warm]),frame_results=rows,
        synthetic_reference_frames=30,fault_modes=[c['mode'] for c in tests['cases'][1:]],
        actual_reference_checks=4066624,actual_vram_bytes=new['vram_bytes'],
        actual_vram_commands=new['vram_commands'],largest_command_list=new['largest_list'],
        single_tile_bulk_chunks=total_bulk,metadata_wire_bytes=118148,
        bulk_control_wire_bytes=23*total_bulk,total_recorded_output_wire_bytes=total_wire,
        client={k:client[k] for k in ('body_bytes','program_bytes','body_free','command_capacity','metadata_end')},
        additional_private_snes_wram=dict(metadata=188,command_list=2552,total=2740),
        preserved_arm_extra_retained=160,arm_margin1640_is_arithmetic_only=True,
        physical_fps=False,full_pipeline=False,source_rtl=False,full_run_irq=False,
        limitations=['fileRPC cadence and seal_master_cycles are NOT runtime timing',
                    'one-tile bulk fixture, not production grouped source scheduling',
                    'complete metadata/used VRAM plus synthetic RGB; not whole NES/SNES RGB equivalence',
                    'palette skip requires paired231 two-bank dirty propagation',
                    'five warm frames still occupy two VBlanks; no60fps adoption'],
        evidence_hashes={str(p):sha(p) for p in (before/'result.json',after/'result.json',synthetic/'result.json',build/'build.json')},
        analyzer_sha256=sha(Path(__file__)))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('before','after','synthetic','build','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    r=analyze(a.before,a.after,a.synthetic,a.build)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:r[k] for k in ('passed','warm_before_multiple','warm_after_multiple','remaining_frames','charge_model','client')},indent=2))
