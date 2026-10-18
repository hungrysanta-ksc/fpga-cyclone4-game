# SPDX-License-Identifier: MIT
"""Same71-frame A feature sensitivity and B topology gate, not FPS/RTL proof."""
from pathlib import Path
import argparse,csv,json,struct,subprocess,shutil,re
from nes_delta231 import ROOT,BASE,sha
from nes_stream234 import crc,encode
from analyze_nes_geometry230 import spans,summary,packets
from analyze_nes_source234 import blocks

def variant(old,new,raw,serial,generation,mode):
    if mode=='full':return encode(old,new,raw,serial,generation)[0]
    cold=serial==1;ops=[]
    def literal(a,b):
        for at,data in spans(old[a:b],new[a:b]):ops.append(struct.pack('<HB',a+at,len(data))+data)
    if cold:
        ops=[struct.pack('<HB',at,len(new[at:at+240]))+new[at:at+240] for at in range(0,len(new),240)]
    elif mode=='literal':literal(0,len(new))
    else:
        # Keep row shifts but replace raster-XOR with canonical byte spans.
        for at in range(0,2112,66):
            a,b=old[at:at+66],new[at:at+66]
            if a==b:continue
            if a[2:]==b[:-2]:ops.append(struct.pack('<HBBB',at,0,2,1)+b[-2:])
            elif a[:-2]==b[2:]:ops.append(struct.pack('<HBBB',at,0,2,255)+b[:2])
            else:literal(at,at+66)
        literal(2112,3872);literal(3872,5664);literal(5664,len(new))
    records=[struct.pack('<2sBBIIIHH',b'N4',1,int(cold),1,0 if cold else serial-1,serial,generation,0)]
    c=crc(records[0]);expanded=0
    for op in ops:
        expanded+=op[2] if op[2] else 66;c=crc(op,c);records.append(op)
    tail=struct.pack('<HBBHH',65535,0,3,len(ops),expanded);c=crc(tail,c);records.append(tail+struct.pack('<H',c))
    for at in range(0,len(raw),240):
        op=struct.pack('<HB',at,len(raw[at:at+240]))+raw[at:at+240];c=crc(op,c);records.append(op)
    tail=struct.pack('<HBB',65535,0,4);c=crc(tail,c);records.append(tail+struct.pack('<H',c));return records

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--map',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
    prior=BASE/'probes/nes-source234/test03';old_analysis=json.loads((ROOT/'analysis/source234-verification.json').read_text())
    mapped=json.loads((a.map/'result.json').read_text());assert mapped['passed']
    base_rows={r['frame']:r for r in old_analysis['rows']}
    cost={int(c['frame']):{k:int(v) for k,v in c.items()} for c in csv.DictReader((prior/'cost.csv').open())}
    fit=BASE/'probes/nes-counter224/mapfit02/output_files/board.fit.rpt';fittext=fit.read_text(encoding='latin-1')
    names={'export':'nes_native_export203:native_export','records':'nes_native_mailbox165:native_records',
           'prepared':'nes_native_mailbox165:native_prepared','spi':'nes_native_spi165:native_spi'}
    fitrows={}
    for k,n in names.items():
        row=next(l for l in fittext.splitlines() if '|'+n+'|' in l and re.search(r';\s*\d+ \(\d+\)',l))
        cols=[x.strip() for x in row.split(';')];fitrows[k]=dict(le=int(cols[2].split()[0]),ff=int(cols[3].split()[0]),line=row.strip())
    assert [fitrows[n]['le'] for n in names]==[644,219,50,479]
    # Same executable already compiled/tested235; no different C decoder.
    executable=BASE/'probes/nes-source235/test02/host/host.exe';records_by_mode={};cases={};pins={}
    for mode in ('full','literal','shift'):
        d=out/mode;d.mkdir();previous=bytes(5741);rows=[]
        for n,f in enumerate(range(905,976),1):
            new=(prior/f'frame{f}.geometry').read_bytes();raw=(prior/f'frame{f}.raw').read_bytes()
            pp=variant(previous,new,raw,n,cost[f]['generation'],mode);previous=new
            stream=b''.join(struct.pack('<H',len(b))+b for b in pp)
            if mode=='full':assert stream==(prior/f'frame{f}.stream').read_bytes()
            (d/f'frame{f}.stream').write_bytes(stream)
            count=blocks([len(b) for b in pp]);payload=sum(map(len,pp));b=base_rows[f]
            ready4=b['ready4_wire_model']+payload-b['source_wire_bytes']+19*(count-b['blocks'])
            ready1=b['ready1_wire_model']+payload-b['source_wire_bytes']+19*(count-b['blocks'])
            rows.append(dict(frame=f,payload=payload,blocks=count,ready4=ready4,ready1=ready1,wire_ms=ready4*8/2625))
        for name in ('host.exe','palette.bin','wrap.stream','coldwrap.stream'):
            src=(executable.parent/name) if name=='host.exe' else prior/name;shutil.copyfile(src,d/name);pins[str(src.relative_to(BASE)).replace('\\','/')]=sha(src)
        with (d/'run.log').open('wb') as log:
            q=subprocess.run([str(d/'host.exe'),str(BASE/'probes/nes-geometry230/rtl02'),'C:/Users/mohallo/Downloads/test/Super Mario Bros 3 (J).nes','905','975',str(d)],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        log=(d/'run.log').read_text();assert q.returncode==0 and 'reference_checks=4066624' in log,log[-3000:]
        for f in range(905,976):
            for ext in ('geometry','raw','metadata','packets','plans'):assert (d/f'frame{f}.{ext}').read_bytes()==(prior/f'frame{f}.{ext}').read_bytes(),(mode,f,ext)
        warm=rows[2:];cases[mode]=dict(stats={k:summary([r[k] for r in warm]) for k in ('payload','ready4','ready1','wire_ms')},
            over_ready4=[r['frame'] for r in warm if r['ready4']>5468.75],over_ready1=[r['frame'] for r in warm if r['ready1']>5468.75],rows=rows,c_output=log,exact_files=355)
    b_rows=[]
    for f in range(905,976):
        c=cost[f];pp=list(packets((prior/f'frame{f}.packets').read_bytes()))
        assert sum(len(p)+3 for p in pp)==c['metadata_spi']
        # B output-only gets an unrealistically free conversion/egress/ACK.
        # Full production source payload ALONE still occupies the same SPI.
        b_rows.append(dict(frame=f,full_ingress_payload=c['ingress_payload'],payload_only_ms=c['ingress_payload']*8/2625,
            ingress_with_minimum_block_control=c['ingress_payload']+19*c['ingress_blocks'],
            arm_refill_output_bytes=c['metadata_spi'],raw_output_packet_bytes=sum(map(len,pp))))
    live=(BASE/'probes/nes-counter224/mapfit02/nes_live_joint.sv').read_text()
    for needle in ('WIDTH(96)) native_records','WIDTH(17)) native_prepared','nes_native_spi165 native_spi'):assert needle in live
    result=dict(stage=236,passed=True,scope=__doc__,cases=cases,
        resource=dict(old_fit_entities=fitrows,old_fit_replace_le=sum(r['le'] for r in fitrows.values()),
            omitted235_le=269,spare_fit_le=159,corrected_replace_plus_spare_le=1551,previous235_partial_ceiling_le=1282,
            same_boundary_map=mapped['projects'],endpoint_only_map_difference=mapped['endpoint_only_difference_le'],
            mixed_fit_map_residual_arithmetic=1551-mapped['projects']['new']['le'],whole_board_approved=False,encoder_included=False),
        parallel=dict(output_only_ingress_floor=summary([r['payload_only_ms'] for r in b_rows[2:]]),
            output_only_over_60hz=[r['frame'] for r in b_rows[2:] if r['payload_only_ms']>1000/60],rows=b_rows,
            arm_refill='ARM->SPI->FPGA->parallelSNES retains ARM output bytes; not a SPI bypass',
            full_parallel='Needs moving geometry conversion/planning from ARM or a demonstrated new physical ingress. No such implementation/resource/time proof exists. Do not reuse188 tile DMA as proof of full metadata conversion.'),
        pins={**pins,str(fit.relative_to(BASE)).replace('\\','/'):sha(fit),
            'probes/nes-counter224/mapfit02/nes_live_joint.sv':sha(BASE/'probes/nes-counter224/mapfit02/nes_live_joint.sv'),
            'probes/nes-source234/test03/cost.csv':sha(prior/'cost.csv')},
        map_result_sha256=sha(a.map/'result.json'),prior235_manifest_sha256=sha(BASE/'probes/nes-source235/manifest.json'),
        new_fit=False,new_sta=False,physical=False,fps_proven=False,full_input_run_approved=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(resource={k:v for k,v in result['resource'].items() if k not in ('old_fit_entities','same_boundary_map')},
        cases={k:{'stats':v['stats'],'over_ready4':v['over_ready4']} for k,v in cases.items()},parallel_floor=result['parallel']['output_only_ingress_floor']),indent=2))
if __name__=='__main__':main()
