"""Audit RTL CHR latch traces against coordinates and pinned Mesen capture. SPDX-License-Identifier: MIT."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, re

ROM_SHA='72f538f47f2292eb893602dd92d7a31c6749e1a215b95b2052a8b7b4c273c5d5'
PALETTE=(15,33,48,22)
RGB={15:bytes.fromhex('000000'),33:bytes.fromhex('64b0ff'),48:bytes.fromhex('fffeff'),22:bytes.fromhex('b53120')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return [tuple(map(int,s.split())) for s in Path(p).read_text().splitlines()]
def oracle(chrdata,table):
    output=bytearray()
    for y in range(240):
        for x in range(256):
            address=table+(((y//8)*32+x//8)&255)*16+y%8
            bit=7-x%8
            output.append(PALETTE[((chrdata[address]>>bit)&1)|(((chrdata[address+8]>>bit)&1)<<1)])
    return bytes(output)
def pixel_coordinate(line,dot):
    if line>=0 and dot<=239:return line,dot//8+2
    if line<239 and dot>=321:return line+1,(dot-321)//8
    return None

def check_fetch(records,chrdata,table,mesen):
    errors=Counter();used=0;tiles=set()
    slots=Counter((line,dot) for line in range(-1,240) for k in range(34)
                  for dot in ((8*k+5,8*k+7) if k<32 else (325+8*(k-32),327+8*(k-32))))
    if Counter((r[0],r[1]) for r in records)!=slots:errors['latch_cadence']+=1
    for line,dot,tick,address,physical,value,record_table in records:
        if record_table!=table:errors['record_table']+=1
        if physical!=0x200000+address:errors['physical_mapping']+=1
        if not 0<=address<8192 or chrdata[address]!=value:errors['chr_value']+=1
        pos=pixel_coordinate(line,dot)
        if pos is None:continue
        y,x=pos;expected=table+(((y//8)*32+x)&255)*16+y%8+(8 if dot%8==7 else 0)
        if address!=expected:errors['pixel_address']+=1
        if mesen.get((line,dot))!=(address,value):errors['mesen_fetch']+=1
        used+=1;tiles.add(address//16)
    if used!=15360:errors['pixel_fetch_count']+=1
    if len(tiles)!=256:errors['unique_tiles']+=1
    return dict(errors=dict(errors),pixel_referenced_reads=used,unique_tiles=len(tiles))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--mesen-reference',type=Path,required=True);a=p.parse_args()
    out,ref=a.run,a.mesen_reference
    build=json.loads((out/'build.json').read_text());manifest=json.loads((out/'manifest.json').read_text())
    chrdata=bytes(int(v,16) for v in (out/'chr.hex').read_text().split())
    prg=bytes(int(v,16) for v in (out/'prg.hex').read_text().split())
    assert manifest['sha256']==ROM_SHA and hashlib.sha256(b'NES\x1a'+bytes([2,1])+bytes(10)+prg+chrdata).hexdigest()==ROM_SHA
    reference_result=json.loads((ref/'result.json').read_text())
    assert reference_result['passed'] and reference_result['rom_sha256']==ROM_SHA
    assert sha(ref/'trace.tsv')==reference_result['trace_sha256']
    reference_frames={r['frame']:r for r in reference_result['frames']}
    reference_by_table={r['table']:r for r in reference_result['frames']}
    mesen={}
    for s in (ref/'trace.tsv').read_text().splitlines():
        v=s.split('\t')
        if v[0]!='read':continue
        f,line,dot,clock,cpu,address,value,physical,memtype,table=map(int,v[1:])
        if f in reference_frames:mesen.setdefault(f,{})[(line,dot)]=(address,value)
    log=(out/'simulation.log').read_text(errors='replace');m=re.search(r'^# RESULT (.+)$',log,re.M)
    assert m,'Missing RTL metrics'
    metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};errors=Counter()
    if not build.get('diagnostic_passed') or 'PASS NES DIAGNOSTIC' not in log or re.search(r'\*\* (?:Fatal|Error):',log):errors['rtl_assertions']+=1
    for k in ('pixel_errors','fetch_errors','cpu_period_errors','unknown_bus'):
        if metrics.get(k)!=0:errors[k]+=1
    if (metrics.get('frames'),metrics.get('pixels'),metrics.get('fetches'),metrics.get('table_changes'))!=(4,245760,65552,3):errors['metrics']+=1
    meta=rows(out/'frames.tsv');trace=rows(out/'fetch.tsv');controls=rows(out/'control.tsv');frames=[];negatives={}
    if [r[0] for r in meta]!=[1,2,3,4]:errors['frame_sequence']+=1
    for f,table,counter,start in meta:
        assert table in (0,4096)
        values=bytes(int(v,16) for v in (out/f'frame-{f:3}.hex').read_text().split())
        expected=oracle(chrdata,table)
        diff=sum(x!=y for x,y in zip(values,expected))+abs(len(values)-len(expected))
        if diff:errors['indexed_pixels']+=diff
        rgb=b''.join(RGB.get(v,b'\xff\x00\xff') for v in values)
        reference=reference_by_table[table];mesen_rgb=(ref/f"frame-{reference['frame']:03}.rgb").read_bytes()
        assert hashlib.sha256(mesen_rgb).hexdigest()==reference['rgb_sha256']
        if rgb!=mesen_rgb:errors['mesen_rgb']+=1
        records=[(line if line!=511 else -1,cycle-1,tick,address,physical,value,t) for frame,line,cycle,tick,address,physical,value,t in trace if frame==f]
        checked=check_fetch(records,chrdata,table,mesen[reference['frame']]);errors.update(checked['errors'])
        preceding=[r for r in controls if r[0]<start];ctrl=preceding[-1] if preceding else None
        if ctrl is None or ctrl[1]!=241 or (ctrl[3]&16)*256!=table:errors['control_switch']+=1
        if frames:
            prev=frames[-1]
            if table==prev['table'] or counter!=prev['rom_counter']+1:errors['switch_sequence']+=1
            if start-prev['start_master_tick'] not in (357364,357368):errors['frame_period']+=1
        frames.append(dict(frame=f,table=table,rom_counter=counter,start_master_tick=start,pixels=len(values),different_pixels=diff,
            rgb_sha256=hashlib.sha256(rgb).hexdigest(),indexed_sha256=hashlib.sha256(values).hexdigest(),mesen_frame=reference['frame'],
            bg_latches=len(records),**checked,preceding_control=ctrl))
        if not negatives:
            damaged=bytearray(values);damaged[0]^=1
            negatives['pixel_corruption_rejected']=bytes(damaged)!=expected
            negatives['truncated_frame_rejected']=values[:-1]!=expected
            negatives['wrong_table_rejected']=values!=oracle(chrdata,4096-table)
            altered=list(records);r=list(altered[0]);r[3]^=16;altered[0]=tuple(r)
            negatives['address_corruption_rejected']=bool(check_fetch(altered,chrdata,table,mesen[reference['frame']])['errors'])
            negatives['missing_latch_rejected']=bool(check_fetch(records[:-1],chrdata,table,mesen[reference['frame']])['errors'])
    result=dict(candidate='NES-P2-RTL-FETCH-007',passed=not errors and all(negatives.values()),errors=dict(errors),metrics=metrics,frames=frames,negative_tests=negatives,
        rom_sha256=ROM_SHA,driver_candidate=build['candidate'],driver_sha256=build['source_sha256'],verifier_sha256=sha(__file__),
        reference_result_sha256=sha(ref/'result.json'),reference_trace_sha256=sha(ref/'trace.tsv'),
        observation_time_ns=140020000,clock_half_period_ns=23.280,
        contract='PPU BgPainter pre-NBA latches at RTL cycles 6/8 mapped to Mesen read slots 5/7; compare pixel-referenced addresses/values, not absolute phase or unused fetch content. Registered colors at x+2 preserve 256x240. Existing RTL-006 driver reused unchanged.',
        scope='Original NROM alternating PPUCTRL pattern tables, four full frames, ideal one-master-tick memory. All CHR resident initially. No MMC3, A12/IRQ, real cache miss, NES-to-SNES integration, full-fit/STA, SMB3 or hardware claim.')
    (out/'fetch-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
