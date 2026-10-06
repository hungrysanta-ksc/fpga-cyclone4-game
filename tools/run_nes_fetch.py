"""Capture and verify actual NES PPU fetches in an isolated Mesen. SPDX-License-Identifier: MIT."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import subprocess

# Selected default Mesen 2.2.1 RGB entries for NES indices 0F,21,30,16.
# UI/Config/NesConfig.cs at pinned local Mesen source; no color fitting to captures.
RGB = tuple(bytes.fromhex(c) for c in ('000000', '64b0ff', 'fffeff', 'b53120'))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(chrdata, table):
    pixels = bytearray()
    for y in range(240):
        for x in range(256):
            tile = ((y//8)*32+x//8) & 255
            address = table+tile*16+y%8
            bit = 7-x%8
            color = ((chrdata[address] >> bit) & 1) | (((chrdata[address+8] >> bit) & 1) << 1)
            pixels.extend(RGB[color])
    return bytes(pixels)


def analyze(probe, out, first, count, returncode):
    manifest = json.loads((probe/'manifest.json').read_text())
    rom = (probe/'fetch.nes').read_bytes()
    assert manifest['original_diagnostic'] and manifest['mapper']==0
    assert hashlib.sha256(rom).hexdigest()==manifest['sha256']
    assert len(rom)==16+32768+8192 and rom[:16]==b'NES\x1a'+bytes([2,1])+bytes(10)
    chrdata = rom[16+32768:]
    errors = Counter()
    if returncode: errors['emulator_exit'] += 1
    names = ['frame','line','dot','ppu_master','cpu_cycles','address','value','physical','memtype','bg_table']
    trace = []
    for line in (out/'trace.tsv').read_text().splitlines():
        values=line.split('\t')
        trace.append(dict(kind=values[0], **dict(zip(names,map(int,values[1:]),strict=True))))
    if any(a['ppu_master']>b['ppu_master'] for a,b in zip(trace,trace[1:])): errors['trace_clock_order'] += 1
    meta = [list(map(int,row.split('\t'))) for row in (out/'frames.tsv').read_text().splitlines()]
    if [r[0] for r in meta]!=list(range(first,first+count)): errors['frame_sequence'] += 1
    frames=[]
    for frame,line,dot,clock,cpu,table,counter,width,height,chr_enum in meta:
        if (width,height,line,dot)!=(256,240,240,0): errors['frame_geometry'] += 1
        if table not in (0,4096): errors['invalid_table'] += 1; continue
        reads=[t for t in trace if t['kind']=='read' and t['frame']==frame]
        controls=[t for t in trace if t['kind']=='ctrl' and t['frame']==frame]
        if len(controls)!=1: errors['control_count'] += 1
        control=controls[0] if controls else None
        if control and (control['line']!=241 or control['value']*256!=table or control['bg_table']==table): errors['control_switch'] += 1
        bg=[t for t in reads if t['dot']<=256 or t['dot']>=321]
        sprites=[t for t in reads if 257<=t['dot']<=320]
        expected_slots=Counter((y,d) for y in range(-1,240) for k in range(34)
                               for d in ((8*k+5,8*k+7) if k<32 else (325+8*(k-32),327+8*(k-32))))
        if Counter((t['line'],t['dot']) for t in bg)!=expected_slots: errors['bg_fetch_cadence'] += 1
        sprite_slots=Counter({(y,261+8*k):2 for y in range(-1,240) for k in range(8)})
        if Counter((t['line'],t['dot']) for t in sprites)!=sprite_slots: errors['sprite_fetch_cadence'] += 1
        for t in reads:
            if t['memtype']!=chr_enum or t['physical']!=t['address']: errors['physical_mapping'] += 1
            if not 0<=t['address']<8192 or chrdata[t['address']]!=t['value']: errors['chr_value'] += 1
        used=[]
        for t in bg:
            y,d=t['line'],t['dot']
            if y>=0 and d<=239: x=d//8+2
            elif y<239 and d>=321: y+=1; x=(d-321)//8
            else: continue  # unused pre-render and right-edge pipeline reads
            plane=8 if d%8==7 else 0
            expected=table+(((y//8)*32+x)&255)*16+y%8+plane
            if t['address']!=expected: errors['pixel_fetch_address'] += 1
            used.append(t)
        if len(used)!=240*32*2: errors['pixel_fetch_count'] += 1
        actual=(out/f'frame-{frame:03}.rgb').read_bytes()
        expected=reference(chrdata,table)
        if len(actual)!=len(expected): errors['rgb_size'] += 1
        different=sum(actual[i:i+3]!=expected[i:i+3] for i in range(0,len(expected),3))
        if different: errors['rgb_pixels'] += different
        first_bg=min(bg,key=lambda t:t['ppu_master']) if bg else None
        first_used=min(used,key=lambda t:t['ppu_master']) if used else None
        lead=lambda t: t['ppu_master']-control['ppu_master'] if t and control else None
        frames.append(dict(frame=frame,ppu_master=clock,cpu_cycles=cpu,table=table,rom_counter=counter,
            chr_reads=len(reads),bg_reads=len(bg),sprite_dummy_reads=len(sprites),pixel_referenced_reads=len(used),
            pixel_referenced_tiles=len({t['physical']//16 for t in used}),different_pixels=different,
            rgb_sha256=sha(out/f'frame-{frame:03}.rgb'),
            ctrl_dot=control['dot'] if control else None,first_bg_lead_master_clocks=lead(first_bg),
            first_pixel_fetch_lead_master_clocks=lead(first_used)))
    for a,b in zip(frames,frames[1:]):
        if b['table']==a['table'] or b['rom_counter']!=a['rom_counter']+1: errors['switch_sequence'] += 1
        # NTSC odd-frame dot skip; master clock is four ticks per PPU dot.
        if b['ppu_master']-a['ppu_master']!=357368-(4 if b['frame']%2 else 0): errors['frame_period'] += 1
    return dict(candidate=manifest['candidate'],passed=not errors,errors=dict(errors),returncode=returncode,
        frames=frames,trace_rows=len(trace),capture_frames=count,source_height=240,displayed_height=240,
        clock_unit='ppu.masterClock: NTSC oscillator counter, 4/PPU dot. Raw callback counter deltas: PPU reads occur inside Exec before its counter increment; CPU writes are observed after Run increments it. Not exact CPU phi2 timing; callback phase differs by one PPU dot. Top-level masterClock is CPU cycles.',
        scope=manifest['scope'],rom_sha256=manifest['sha256'],trace_sha256=sha(out/'trace.tsv'))


def main():
    p=argparse.ArgumentParser()
    for name in ('mesen','probe','out'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--first-frame',type=int,default=6);p.add_argument('--frames',type=int,default=8)
    a=p.parse_args();out=a.out.resolve();probe=a.probe.resolve();exe=a.mesen.resolve()
    assert str(out).isascii() and 6<=a.first_frame and 2<=a.frames<=16
    # This runner accepts the original diagnostic generator's exact current bytes only.
    from build_nes_fetch import build
    out.mkdir(parents=True,exist_ok=False)
    reference_dir=out/'original-check';build(reference_dir)
    assert (probe/'fetch.nes').read_bytes()==(reference_dir/'fetch.nes').read_bytes()
    script=Path(__file__).resolve().parents[1]/'tests/nes-functional/capture_fetch.lua'
    prefix=f'local OUT_DIR={json.dumps(out.as_posix())}\nlocal FIRST_FRAME={a.first_frame}\nlocal LAST_FRAME={a.first_frame+a.frames-1}\n'
    (out/'capture.lua').write_text(prefix+script.read_text(),encoding='utf-8',newline='\n')
    command=[str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'fetch.nes'),'--timeout=50','--doNotSaveSettings','--enableStdout']
    with (out/'mesen.log').open('wb') as log:
        process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    result=analyze(probe,out,a.first_frame,a.frames,process.returncode)
    result['sources']={p.name:sha(p) for p in (Path(__file__),script,Path(__file__).with_name('build_nes_fetch.py'))}
    result['tools']={n:sha(exe.parent/n) for n in ('Mesen.exe','Mesen.dll','MesenCore.dll','settings.json')}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__': main()
