# Reaudit raw trace replay, union240-row coverage and malformed packets. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,json,hashlib
from run_nes_trace_replay import audit
from build_nes_trace_replay import decode,display_rgb
def rejected(fn):
    try:fn()
    except (AssertionError,ValueError):return True
    return False
def verify(root):
    summaries={};builds={}
    for case in ('top','bottom','chr','length'):
        build=root/case/('build-02' if case=='top' else 'build');capture=root/case/'capture';builds[case]=build
        result=audit(build,capture)
        assert result['expected_outcome_verified']
        assert result==json.loads((capture/'result.json').read_text())
        summaries[case]=result
    inverse={value:key for key,value in display_rgb().items()}
    assert len(inverse)==4
    coverage=[]
    for frame in range(1,5):
        observed={};comparisons=0
        for case in ('top','bottom'):
            offset=summaries[case]['viewport']
            rgb=(root/case/'capture'/f'frame-{frame-1:03}.rgb').read_bytes()
            indexed=bytes(inverse[rgb[i:i+3]] for i in range(0,len(rgb),3))
            for i,pixel in enumerate(indexed):
                dest=i+offset*256
                assert dest not in observed or observed[dest]==pixel,'overlap differs between observations'
                observed[dest]=pixel;comparisons+=1
        assert set(observed)==set(range(256*240))
        merged=bytes(observed[i] for i in range(256*240))
        expected=(builds['top']/f'expected-{frame}.idx').read_bytes()
        assert merged==expected
        coverage.append(dict(frame=frame,unique_source_pixels=len(merged),actual_pixel_comparisons=comparisons,
                             merged_indexed_sha256=hashlib.sha256(merged).hexdigest()))
    build=builds['top'];atlas=(build/'chr-snes.bin').read_bytes();p=(build/'packet-1.bin').read_bytes()
    negative={}
    for name,start,value in [('magic',0,0),('version',4,2),('width',7,0),('height',8,239),
                              ('map_length',10,0),('tile_range',17,255),('palette',1943,255)]:
        bad=bytearray(p);bad[start]=value
        negative[name]=rejected(lambda:decode(bytes(bad),atlas))
    negative['truncated_packet']=rejected(lambda:decode(p[:-1],atlas))
    # Raw NES planar bytes are deliberately different from SNES interleaved rows.
    swapped=bytes(v for i in range(0,len(atlas),2) for v in (atlas[i+1],atlas[i]))
    negative['plane_swap_pixel_mismatch']=decode(p,swapped)!=(build/'expected-1.idx').read_bytes()
    assert all(negative.values()),negative
    return dict(candidate='NES-R2-TRACE-REPLAY-020',audit_pass=True,cases=summaries,
                full_source_accounting=coverage,unique_source_pixels=245760,
                actual_normal_pixel_comparisons=sum(r['actual_pixel_comparisons'] for r in coverage),
                packet_negative_tests=negative,source_height=240,simultaneous_display_height=239,
                full240_simultaneous_display_proven=False,live_producer_deadline_proven=False,
                packet_bytes=1944,ppu_dma_bytes_per_frame=1928,startup_chr_dma_bytes=16384,
                palette='Four source symbols preserved under explicit RGB555 quantization; not exact original RGB/analog color calibration.',
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Offline ROM supplier of actual archived NES BG packets. Two independent239-row views cover all240source rows; no product crop policy or live NES/SNES clock bridge.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists()
    result=verify(a.runs);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(audit_pass=result['audit_pass'],unique_source_pixels=result['unique_source_pixels'],
         actual_normal_pixel_comparisons=result['actual_normal_pixel_comparisons'],packet_negative_tests=result['packet_negative_tests']),indent=2))