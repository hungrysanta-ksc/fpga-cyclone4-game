# SPDX-License-Identifier: MIT
"""P1 semantic raster projection and bounded parallel-raw relocation models.

Actual host C output/reference replay; Python wire/resource models only.
No product source change, FPGA area result, ARM/65816 timing or FPS claim.
"""
from pathlib import Path
import argparse, ctypes, csv, json, os, shutil, struct, subprocess
from nes_delta231 import BASE, ROOT, sha, once
from run_nes_scroll229 import ROM_SHA
from analyze_nes_geometry230 import packets
from analyze_nes_path236 import variant
from analyze_nes_source234 import blocks


def project(g):
    """Validate before discarding fields; current accepted planner contract."""
    values = struct.unpack_from('<224Q',g,3872)
    palettes = struct.unpack_from('<H',g,5738)[0]//32
    assert palettes in (1,2)
    normal = [v for v in values if not (v>>49)&1]
    assert normal
    mode = (normal[0]>>36)&255
    assert mode in (0x18,0x1e)
    out = []
    raw = 0
    for v in values:
        if (v>>49)&1:
            assert v>>53 == 0 and v&((1<<49)-1) == 0
            assert (v>>50)&7 == raw and raw < g[5740]
            out.append(1024 | raw<<11)
            raw += 1
        else:
            assert v>>49 == 0 and (v>>44)&31 < palettes and (v>>36)&255 == mode
            out.append((v&31)|((v>>5)&32)|((v>>30)&7)<<6|((v>>44)&1)<<9)
    assert raw == g[5740]
    return struct.pack('<224H',*out)+bytes([mode])


C_PROJECT = r'''
/* Test-only adapter. Original reference203 input remains untouched. */
static bool decode_projection247(const uint8_t *p,unsigned n,unsigned palettes,
                                 unsigned patches,uint64_t out[224]){
 if(n!=449||(p[448]!=0x18&&p[448]!=0x1e)||!palettes||palettes>2)return false;
 unsigned raw=0;
 for(unsigned y=0;y<224;y++){
  unsigned v=p[y*2]|((unsigned)p[y*2+1]<<8);
  if(v&0xc000)return false;
  if(v&1024){
   if((v&1023)||((v>>11)&7)!=raw||raw>=patches)return false;
   out[y]=(UINT64_C(1)<<49)|((uint64_t)raw++<<50);
  }else{
   if((v&0x3800)||((v>>9)&1)>=palettes)return false;
   out[y]=(v&31)|((uint64_t)(v&32)<<5)|((uint64_t)((v>>6)&7)<<30)|
          ((uint64_t)p[448]<<36)|((uint64_t)((v>>9)&1)<<44);
  }
 }
 return raw==patches;
}
static void apply_projection247(void){
 char name[80];snprintf(name,sizeof name,"frame%u.projected",frame247);
 FILE *f=fopen(name,"rb");uint8_t p[449];assert(f&&fread(p,1,sizeof p,f)==sizeof p&&fgetc(f)==EOF);fclose(f);
 assert(decode_projection247(p,sizeof p,input.counts[5]/32,input.patch_count,input.raster));
}
static void projection_guards247(void){
 uint8_t p[449]={0};uint64_t out[224];unsigned checks=0;p[448]=0x18;
 assert(decode_projection247(p,449,1,0,out));checks++;
 assert(!decode_projection247(p,448,1,0,out));checks++;
 p[448]=0;assert(!decode_projection247(p,449,1,0,out));checks++;p[448]=0x18;
 p[1]=0x40;assert(!decode_projection247(p,449,1,0,out));checks++;
 p[1]=2;assert(!decode_projection247(p,449,1,0,out));checks++;
 p[1]=8;assert(!decode_projection247(p,449,1,0,out));checks++;
 p[1]=4;p[0]=1;assert(!decode_projection247(p,449,1,1,out));checks++;p[0]=0;
 p[1]=12;assert(!decode_projection247(p,449,1,1,out));checks++;
 p[1]=4;assert(!decode_projection247(p,449,1,0,out));checks++;
 p[1]=0;assert(!decode_projection247(p,449,1,1,out));checks++;
 printf("PROJECT247 guards=%u PASS\n",checks);
}
'''


def c_replay(out, observer, rom, gcc, pins):
    assert sha(rom) == ROM_SHA
    evidence = json.loads((observer/'result.json').read_text())
    for name,digest in evidence['observed_sources'].items():
        assert sha(observer/name) == digest
    for src in observer.iterdir():
        if src.suffix in ('.c','.h','.inc','.delta') or src.name=='palette.bin':
            shutil.copyfile(src,out/src.name)
            pins[src.relative_to(BASE).as_posix()] = sha(src)
    for f in range(905,976):
        source = observer/f'frame{f}.geometry'
        assert sha(source) == evidence['output_hashes'][source.name]
        packed = project(source.read_bytes())
        (out/f'frame{f}.projected').write_bytes(packed)
    host = out/'host.c'
    s = host.read_text()
    s = once(s,'static void run_frame(uint32_t epoch){',C_PROJECT+'\nstatic void run_frame(uint32_t epoch){')
    s = once(s,' convert_input();memset(sizes,0,sizeof sizes);',
             ' convert_input();apply_projection247();memset(sizes,0,sizeof sizes);')
    s = once(s,' fclose(map247);fclose(slot247);fclose(csv);source_faults231();',
             ' fclose(map247);fclose(slot247);fclose(csv);projection_guards247();source_faults231();')
    host.write_text(s,encoding='utf-8',newline='\n')
    env = os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    def native(p):
        b=ctypes.create_unicode_buffer(32768)
        n=ctypes.windll.kernel32.GetShortPathNameW(str(p.resolve()),b,len(b))
        assert 0<n<len(b) and b.value.isascii()
        return b.value
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c',
           'nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    for label,cmd in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),
                      ('run',[out/'host.exe',native(BASE/'probes/nes-geometry230/rtl02'),native(rom),905,975,native(out)])]:
        with (out/(label+'.log')).open('wb') as log:
            r=subprocess.run(list(map(str,cmd)),cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,
                             timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(out/(label+'.log')).read_text(errors='replace')[-4000:]
    log=(out/'run.log').read_text()
    assert 'reference_checks=4066624' in log and 'PROJECT247 guards=10 PASS' in log
    compared=[]
    for f in range(905,976):
        for ext in ('geometry','raw','metadata','packets','plans'):
            name=f'frame{f}.{ext}'
            assert sha(observer/name)==evidence['output_hashes'][name]
            assert (observer/name).read_bytes()==(out/name).read_bytes(),name
            compared.append(name)
    for name in ('cost.csv','map247.csv','slot247.csv'):
        assert (observer/name).read_bytes()==(out/name).read_bytes(),name
    return dict(frames=71,exact_files=len(compared),cost_map_slot_exact=True,reference_checks=4066624,
                decoder_guards=10,original_reference_raster_unchanged=True,
                note='geometry dumps precede projection; final C metadata/packets/plans and reference pixels are compared.',
                host_sha256=sha(host),build_log_sha256=sha(out/'build.log'),run_log_sha256=sha(out/'run.log'))


def analyze(out, observer):
    prior=json.loads((BASE/'probes/nes-wholepath247/analysis06/result.json').read_text())
    schedule=json.loads((BASE/'probes/nes-wholepath247/schedule04/result.json').read_text())
    assert prior['passed'] and schedule['passed']
    # Corrupt fields must be rejected before a lossy semantic projection can
    # erase the evidence. These are source validation guards, not CRC tests.
    fixture=(observer/'frame905.geometry').read_bytes()
    rv=struct.unpack_from('<224Q',fixture,3872)
    normal=next(i for i,v in enumerate(rv) if not(v>>49)&1)
    rawrow=next(i for i,v in enumerate(rv) if (v>>49)&1)
    corruptions=[(normal,rv[normal]|1<<63),
                 (normal,(rv[normal]&~(31<<44))|2<<44),
                 (normal,(rv[normal]&~(255<<36))|0x19<<36),
                 (rawrow,rv[rawrow]|1),
                 (rawrow,(1<<49)|(7<<50))]
    for at,value in corruptions:
        bad=bytearray(fixture);struct.pack_into('<Q',bad,3872+at*8,value)
        try:project(bad)
        except AssertionError:pass
        else:raise AssertionError('Projection erased an invalid source field')
    sr={r['frame']:r for r in schedule['rows']}
    prev=bytes(4398);rows=[]
    original_changes=projected_changes=0;old_raster=bytes(1792);old_packed=bytes(449)
    for r in prior['rows']:
        f=r['frame'];g=(observer/f'frame{f}.geometry').read_bytes();raw=(observer/f'frame{f}.raw').read_bytes()
        packed=project(g)
        new=g[:3872]+packed+g[5664:]
        assert len(new)==4398
        records=variant(prev,new,raw,f-904,f-904,'shift')
        payload=sum(map(len,records));nb=blocks(list(map(len,records)))
        records_no_raw=variant(prev,new,b'',f-904,f-904,'shift')
        no_raw_payload=sum(map(len,records_no_raw));no_raw_blocks=blocks(list(map(len,records_no_raw)))
        w=r['spi']['ready4_components']
        delta=payload-w['source_payload']+19*(nb-w['source_block_framing']//3)
        no_raw_delta=no_raw_payload-payload+19*(no_raw_blocks-nb)
        pp=list(packets((observer/f'frame{f}.packets').read_bytes()))
        removable=[];raw_payload=raw_packets=0
        for p in pp:
            if p[0] not in (2,4,5,8) or p[1]!=5:continue
            at,n,expanded=struct.unpack_from('<HHH',p,10)
            size=n if p[0]==2 else expanded
            if 1121<=at and at+size<=3169:
                raw_payload+=n;raw_packets+=1;removable.append(p)
        # Charge only packets wholly contained in raw CHR; never remove mode/
        # HDMA/palette, BEGIN/SEAL or final ownership controls as "free" work.
        row=dict(frame=f,raw_pixels=len(raw),projected_input_payload=payload,projected_input_blocks=nb,
                 raw_output_payload=raw_payload,raw_output_packets=raw_packets,
                 full_raw_2048_charge=r['snes']['charge_model']-r['snes']['upload']['raw']['charge']+2048+96,
                 models={})
        for output in ('batched16','causal_words'):
            old=r['p1_models'][output]
            model={k:old[k+'_bytes']+delta for k in ('ready4','ready1')}
            model['snes_charge']=sr[f]['models']['full_'+output]['snes_charge']
            model['extra_arm_state']=old['additional_arm_retained_bytes']
            row['models']['semantic_shift_'+output]=model
            # Ceiling only: sparse FPGA producer must replace BOTH raw input
            # and output conversion; descriptors, CPU and CDC are still added.
            count=len(pp)-2-r['spi']['output_section_envelope_bytes'].get('2',0)//19+old['map_packets']
            model2=dict(model)
            for ready,q in (('ready4',4),('ready1',1)):
                polls=20*((count-raw_packets+q-1)//q-(count+q-1)//q)
                model2[ready]+=no_raw_delta-raw_payload-19*raw_packets+polls
            model2['added_parallel_control_bytes']=None
            model2['sparse_raw_producer_implemented']=False
            row['models']['semantic_shift_sparse_raw_ceiling_'+output]=model2
        if f>=907:
            original_changes+=sum(a!=b for a,b in zip(g[3872:5664],old_raster))
            projected_changes+=sum(a!=b for a,b in zip(packed,old_packed))
        old_raster=g[3872:5664];old_packed=packed;prev=new;rows.append(row)
    summaries={}
    for name in rows[0]['models']:
        rr=[(r['frame'],r['models'][name]) for r in rows[2:]]
        summaries[name]=dict(ready4_max=max(v['ready4'] for _,v in rr),ready1_max=max(v['ready1'] for _,v in rr),
            over_ready4=[f for f,v in rr if v['ready4']>5468.75],over_ready1=[f for f,v in rr if v['ready1']>5468.75],
            over_snes=[f for f,v in rr if v['snes_charge']>4192],qualified_for_p2=False)
    # A direct port of these coexisting arrays, even before geometry buffers,
    # needs more than the optimistic reclaimed RAM. Not a universal HW bound.
    arrays=dict(current_bg_exact=1024*8,current_obj_exact=128*4,retained_bg=1024*2,retained_obj=128*4,
                resident_used_dirty=(2+1+1)*144,index=256*2+1152*2,map=4096)
    return dict(rows=rows,models=summaries,source_projection_guards=len(corruptions),source_raster_changed_bytes=original_changes,
                projected_raster_changed_bytes=projected_changes,
                full_raw_2048_over_snes=[r['frame'] for r in rows[2:] if r['full_raw_2048_charge']>4192],
                literal_planner_port=dict(arrays=arrays,bytes=sum(arrays.values()),
                    m9k_bit_capacity_floor=(sum(arrays.values())*8+9215)//9216,
                    max_reclaimed_m9k_scenario=12,area_approved=False,
                    scope='Unchanged array layout;not a lower bound for a redesigned allocator. Geometry/output buffers omitted.'),
                hybrid_memory_scenario=dict(source_base_bytes=4398,source_base_m9k_banked_estimate=5,
                    sparse_raw_last_base_bytes=2048,sparse_raw_stale_bitmap_bytes=32,
                    board_m9k_arithmetic=55,unallocated=1,
                    note='54-1 projected source base+2 raw base=55;bitmap/ports/packing/control and margin unproven. No extra aperture RAM counted.'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','rom','gcc'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    observer=BASE/'probes/nes-wholepath247/observer03';pins={}
    c=c_replay(out,observer,a.rom.resolve(),a.gcc.resolve(),pins)
    result=analyze(out,observer)
    for name in ('probes/nes-wholepath247/analysis06/result.json','probes/nes-wholepath247/schedule04/result.json',
                 'probes/nes-wholepath247/observer03/result.json',
                 'probes/nes-source240/board01/result.json','probes/nes-source240/board01/nes_live_joint.sv',
                 'probes/nes-source240/board01/nes_direct206.sv','probes/nes-source240/board01/nes_tile_bulk206.sv',
                 'repository-nes-milestone/src/nes/rtl/nes_source_query235.sv','repository-nes-milestone/src/nes/rtl/nes_bulk_aperture188.sv',
                 'repository-nes-milestone/tools/analyze_nes_path236.py','repository-nes-milestone/tools/analyze_nes_geometry230.py',
                 'repository-nes-milestone/tools/analyze_nes_source234.py'):
        pins[name]=sha(BASE/name)
    result.update(stage=247,passed=True,scope=__doc__,c_replay=c,input_hashes=pins,
                  analyzer_sha256=sha(Path(__file__)),physical=False,new_fit=False,new_arm=False,new_snes=False,
                  selected_implementation=None)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in result.items() if k not in ('rows','input_hashes')}
    public['residual_rows']=[r for r in result['rows'] if r['frame'] in (952,954,955,963,968)]
    public['private_result_sha256']=sha(out/'result.json');public['input_count']=len(pins)
    public['evidence_sha256']={k:v for k,v in pins.items() if k.endswith(('result.json','.sv','.h','.c'))}
    (out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    rows=[]
    for r in result['rows']:
        row={k:v for k,v in r.items() if k!='models'}
        for name,values in r['models'].items():row.update({name+'.'+k:('UNKNOWN' if v is None else v) for k,v in values.items()})
        rows.append(row)
    with (out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ('passed','c_replay','models','source_raster_changed_bytes','projected_raster_changed_bytes','full_raw_2048_over_snes','literal_planner_port')},indent=2))


if __name__=='__main__':main()
