# SPDX-License-Identifier: MIT
"""Independent scanner command oracle and measured deadline counterexample."""
from pathlib import Path
import argparse,csv,json,re,struct
from nes_delta231 import BASE,sha
from analyze_nes_geometry230 import packets


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8',newline='')))
def stats(v):return dict(minimum=min(v),maximum=max(v))


def analyze(build,test,prior,observer):
    result=read(test/'result.json');assert result['passed'] and result['commits']==71
    b=read(build/'result.json');assert b['body_bytes']==3930 and b['charge_policy']==4192
    pins={}
    def pin(p):pins[p.relative_to(BASE).as_posix()]=sha(p);return p
    for p in (build/'result.json',build/'body.bin',build/'labels.json',test/'result.json',test/'run/capture.lua',test/'run/phase247.csv',test/'run/mesen.log',test/'run/state-keys.txt',prior):pin(p)
    for name,digest in result['inputs'].items():assert sha(BASE/name)==digest;pin(BASE/name)
    original=read(prior)['rows']
    phases=csvread(test/'run/phase247.csv')
    for r in phases:
        for k in r:
            if k!='event':r[k]=int(r[k])
    state=dict(line.split('=',1) for line in (test/'run/state-keys.txt').read_text().splitlines())
    assert state['clockRate']=='21477270' and state['ppu.overscanMode']=='false' and state['ppu.screenInterlace']=='false'
    clock=int(state['clockRate'])
    rows=[];valid=[set(),set()];allowed_uninit=set();command_total=byte_total=0
    for old in original:
        f,gen,target=old['frame'],old['generation'],old['bank'];pfx=observer/f'frame{f}'
        units={k:set() for k in (0,1,2,5)}
        plans=[tuple(map(int,line.split(','))) for line in pin(pfx.with_suffix('.plans')).read_text().splitlines()]
        for kind,slot,n in plans:units[kind].add(slot);valid[target].add(slot+(1024 if kind else 0))
        for packet in packets(pin(pfx.with_suffix('.packets')).read_bytes()):
            if packet[0] in (1,3):continue
            kind=packet[1];at,n,expanded=struct.unpack_from('<HHH',packet,10);size=n if packet[0]==2 else expanded
            if kind==2:assert at%16==0 and size%16==0;units[2].update(range(at//16,(at+size)//16))
            elif kind==5 and 1121<=at<3169:
                end=min(at+size,3169);assert (at-1121)%16==0 and (end-at)%16==0
                units[5].update(range((at-1121)//16,(end-1121)//16))
        expected=[]
        for kind,n,src,da,db in ((0,16,0,0,0xc000),(1,32,0x4000,0x4000,0x8000),(2,16,0x5000,0x6000,0xa000),(5,16,0x6961,0x5000,0x9000)):
            spans=[]
            for slot in sorted(units[kind]):
                at=slot*n
                if spans and at-(spans[-1][0]+spans[-1][1])<=96 and at+n-spans[-1][0]<=4096:
                    start,length=spans[-1]
                    if kind in (0,1):
                        for gap_slot in range((start+length)//n,slot):
                            if gap_slot+(1024 if kind else 0) not in valid[target]:
                                allowed_uninit.update(range(0x7f0000+target*0x8000+src+gap_slot*n,0x7f0000+target*0x8000+src+(gap_slot+1)*n))
                    spans[-1]=(start,at+n-start)
                else:spans.append((at,n))
            for at,length in spans:expected.append(dict(source=target*0x8000+src+at,destination=(db if target else da)+at,bytes=length))
        actual=[{k:int(v) for k,v in r.items()} for r in csvread(pin(test/f'run/commands-{gen}.csv'))]
        assert actual==expected,(f,'command oracle')
        command_total+=len(actual);byte_total+=sum(r['bytes'] for r in actual)
        pp=[r for r in phases if r['generation']==gen]
        start=next(r for r in pp if r['event']=='scan247');end=next(r for r in pp if r['event']=='scan_return247')
        assert end['service_visits']==192
        scan=end['master_clock']-start['master_clock']
        final=next(r for r in pp if r['event']=='final_upload212_return')
        assert 225<=final['scanline']<=261 and 0<=final['hclock']<1364
        # Nominal position overstates elapsed by at most4 on short line240.
        elapsed=(final['scanline']-225)*1364+final['hclock']
        # Validate coordinate units on last transfer->final if no intervening wait.
        last=next(r for r in reversed(pp[:pp.index(final)]) if r['event'] in ('wait169','transfer212'))
        if last['event']=='transfer212':
            nominal=(final['scanline']-last['scanline'])*1364+final['hclock']-last['hclock']
            assert final['master_clock']-last['master_clock'] in (nominal,nominal-4)
        vblanks=int(pin(test/f'run/vblank-{gen}.txt').read_text())
        charge=sum(r['bytes']+96 for r in actual)+old['snes']['fixed_charge']
        rows.append(dict(frame=f,scan_master_clocks=scan,scan_ms=scan*1000/clock,
            service_visits=192,max_service_gap_master_clocks=end['max_service_gap'],
            commands=len(actual),dma_bytes=sum(r['bytes'] for r in actual),charge=charge,vblanks=vblanks,
            final_return_scanline=final['scanline'],final_return_hclock=final['hclock'],
            blank_elapsed_upper_at_final_return=elapsed,blank_remaining_lower_at_final_return=50464-elapsed))
    assert command_total==result['vram_commands'] and byte_total==result['vram_bytes']
    warnings=[int(x,16) for x in re.findall(r'Uninitialized memory read: \$([0-9A-Fa-f]+)',(test/'run/mesen.log').read_text(errors='replace'))]
    assert warnings and set(warnings)<=allowed_uninit,sorted(set(warnings)-allowed_uninit)[:8]
    warm=rows[2:];assert all(r['scan_ms']>1000/60 for r in warm)
    return dict(stage=247,passed=True,decision='REJECT_per_bit_full_scan_latency',frames=71,body_bytes=3930,body_free=6,
        scanner_bytes=283,removed_receive_construction_net_bytes=271,extra_persistent_bytes=0,
        exact_command_frames=71,commands=command_total,dma_bytes=byte_total,
        warm_scan_master_clocks=stats([r['scan_master_clocks'] for r in warm]),warm_scan_ms=stats([r['scan_ms'] for r in warm]),
        warm_scan_over_16_67_ms=len(warm),service_gap_master_clocks=stats([r['max_service_gap_master_clocks'] for r in rows]),
        service_gap_ms_max=max(r['max_service_gap_master_clocks'] for r in rows)*1000/clock,
        warm_multi_vblank=[r['frame'] for r in warm if r['vblanks']>1],
        nominal_ntsc_noninterlace_224_vblank_clocks=[50464,50468],clock_rate=clock,
        final_return_remaining_clocks_lower=stats([r['blank_remaining_lower_at_final_return'] for r in rows]),
        uninitialized_warnings=len(warnings),unique_uninitialized_addresses=len(set(warnings)),warnings_only_expected_invalid_unused_gaps=True,
        runtime_checks='Existing actual65816 metadata/usedpattern/map/raw/VBlank checks plus independent generated descriptor oracle.',
        limitations=['No new full ARM/FPGA/physical runtime or FPS claim.',
            'Observed scanner latency already exceeds frame period; no need to pretend observed max is WCET.',
            '192 service entry intervals are measured;STOP injection and all service paths are not newly verified.',
            'VBlank geometry from primary Mesen PPU source and observed scanline/hClock agreement;not new dispatch authorization.',
            'Remaining clocks measured before final RTS/ACK;not end-to-end headroom.',
            'Old4192 policy and wire packets unchanged;word-map receiver not implemented.'],
        selected_implementation=None,product_changed=False,rows=rows,input_hashes=pins,analyzer_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','test','prior','observer','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=analyze(a.build.resolve(),a.test.resolve(),a.prior.resolve(),a.observer.resolve())
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','input_hashes')};public['input_count']=len(r['input_hashes']);public['private_result_sha256']=sha(raw)
    public['residual_rows']=[v for v in r['rows'] if v['frame'] in (952,954,955,963,968)]
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps({k:v for k,v in public.items() if k!='residual_rows'},indent=2))


if __name__=='__main__':main()
