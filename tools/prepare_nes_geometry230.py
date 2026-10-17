# SPDX-License-Identifier: MIT
"""Translate observed Mesen fetches to the unchanged board collector interface.

This is a host stimulus adapter, not an NES core or mapper equivalence proof.
Read completion maps to the board's following-dot load edge. RGB raw rows use
the lowest equivalent digital-palette index; original ambiguous indices are
not recoverable from RGB. No placeholder attribute or raw pixel is accepted.
"""
from pathlib import Path
from collections import defaultdict, Counter
import argparse, hashlib, json, struct
from analyze_nes_scroll229 import FETCH, WRITE, records
from build_nes_game164 import RGB

NT = struct.Struct('<IhHHBHH')
ROW = struct.Struct('<IhHHHBBB32s')
ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for n in ('capture', 'prior', 'out'):
        p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--first', type=int, default=905)
    p.add_argument('--last', type=int, default=975)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    meta=json.loads((a.capture/'capture.json').read_text()); assert meta['exit_code']==0
    assert meta['capture_first']<=a.first<=a.last<=meta['capture_last']
    assert (a.capture/'frames.tsv').read_bytes()==(a.prior/'frames.tsv').read_bytes()
    colors={}
    for i,c in enumerate(RGB):colors.setdefault(bytes.fromhex(c),i)
    wanted=set(range(a.first,a.last+1))
    nt={}; anchors={}; fetch=defaultdict(list); writes=defaultdict(list)
    for f,y,d,addr,value,v,t in records(a.capture/'nametable.bin',NT):
        if f in wanted and 7<=y<232:
            key=(f,y,d);assert key not in nt,key;nt[key]=(addr,value,v,t)
    for f,y,d,v,t,x,mask,ctrl,palette in records(a.capture/'rows.bin',ROW):
        if f in wanted:
            assert d==1 and (f,y) not in anchors
            anchors[f,y]=(v,t,x,mask,ctrl,palette)
    for row in records(a.capture/'ppu-fetch.bin',FETCH):
        if row[0] in wanted and 7<=row[1]<232:fetch[row[0]].append(row)
    for row in records(a.capture/'writes.bin',WRITE):
        if row[1] in wanted and 7<=row[2]<232:writes[row[1]].append(row)
    summaries=[]
    for f in sorted(wanted):
        image=(a.capture/f'frame-{f:04d}.rgb').read_bytes()
        assert image==(a.prior/f'frame-{f:04d}.rgb').read_bytes()
        assert len(image)==256*240*3
        pixels=bytes(colors[image[i:i+3]] for i in range(0,len(image),3))
        # Palette mirroring is materialized as the collector sees it.
        # Mesen's paletteRam stores the mirrored universal entries separately.
        missing_anchors=[y for y in range(8,232) if (f,y) not in anchors]
        for y in missing_anchors:
            assert y in (193,194) and any(k==0 and addr==0x2001 and not(val&0x18) and 0<=y-line<=1 for k,_,line,d,addr,val in writes[f]),(f,y,'missing row anchor without rendering transition')
        palettes={anchors[f,y][5] for y in range(8,232) if (f,y) in anchors}
        assert len(palettes)==1, 'Need explicit per-dot palette changes'
        palette=bytearray(next(iter(palettes)))
        for i in range(4,32,4):palette[i]=palette[0]
        packed_palette=sum((c&63)<<(6*i) for i,c in enumerate(palette))
        states={}; signals={}; scroll_access=set(); tally=Counter()
        pattern_positions={(r[1],r[2]) for r in fetch[f]}
        forced_raw=set(missing_anchors)
        for y in range(8,232):
            if (f,y) in anchors:
                v,t,x,m,c,_=anchors[f,y];states[y*341+1]=(v,t,x,m,c)
            else:
                # No row-start observation while rendering was disabled.
                # Explicitly select a complete RGB-derived raw row; these
                # unused geometry fields are not asserted to be PPU state.
                states[y*341+1]=(0,0,0,0,0)
        for kind,_,y,d,addr,val in writes[f]:
            if kind==0 and addr in (0x2005,0x2006):scroll_access.add(y*341+d+1)
            if kind==2 and addr>=0x3f00:
                raise AssertionError('Midframe palette write needs exact event capture')
        for row in fetch[f]:
            _,y,d,addr,val,physical,kind,v,t,x,mask,ctrl,oy,ot,oa,ox=row
            assert kind==57 and physical<131072
            states[y*341+d+1]=(v,t,x,mask,ctrl)
            if d%8 not in (5,7):continue
            obj=257<=d<=320
            bg=1<=d<=256 or 321<=d<=336
            target=y+1 if obj or d>=321 else y
            col=(0 if d<329 else 1) if d>=321 else (d+7)//8+1
            if not (8<=target<232 and (obj or bg and col<=32)):continue
            valid=oy!=255 and 0<=y-oy<(16 if ctrl&32 else 8)
            if obj and not valid:continue
            # Attributes are the observed preceding fetch, not a frame-end RAM
            # lookup. High plane retains the same fetch-group attribute.
            attrdot=(d//8)*8+3
            if not obj:
                lowdot=(d//8)*8+5
                if (f,y,attrdot) not in nt or (y,lowdot) not in pattern_positions or (y,lowdot+2) not in pattern_positions:
                    # Partial group at a documented rendering transition:
                    # submit no invented pair/attribute. Missing columns must
                    # select the collector's complete raw-row fallback.
                    assert target in (193,194),(f,y,d,'unexplained incomplete group')
                    forced_raw.add(target);tally['omitted_incomplete_bg_planes']+=1
                    continue
                at,av,va,ta=nt[f,y,attrdot]
                expected=0x23c0|(va&0xc00)|((va>>4)&0x38)|((va>>2)&7)
                assert at==expected,(f,y,d,hex(at),hex(expected))
                attr=(av>>(((va>>4)&4)|(va&2)))&3
            else:attr=0
            # Native PPU signals mark the load one dot after the read.
            # Mesen reports both sprite plane reads at phase5. Keep the
            # observed values/bank identities, schedule high on phase7 for
            # the board collector. This is not a mapper timing equivalence.
            low=not bool(addr&8) if obj else d%8==5
            tick=y*341+d+1+(2 if obj and not low else 0)
            assert tick not in signals
            signals[tick]=(physical|(addr<<17)|(attr<<31)|(oa<<33)|(ox<<41)|
                (int(bg and low)<<49)|(int(bg and not low)<<50)|
                (int(obj and low)<<51)|(int(obj and not low)<<52)|
                (int(obj and valid)<<53)|(3<<54))
            tally['obj_planes' if obj else 'bg_planes']+=1
        # NT state preserves row-start observation. Later PPU bus reads update
        # fineX/mode/mask. PPUMASK writes are explicit even while reads stop.
        for (ff,y,d),(addr,val,v,t) in nt.items():
            if ff==f and d==1 and y>=8:
                assert (f,y) in anchors
        mask_events={y*341+d+1:val for k,_,y,d,addr,val in writes[f] if k==0 and addr==0x2001}
        state=anchors[f,8][:5]
        with (a.out/f'frame{f}.hex').open('w',encoding='ascii',newline='\n') as out:
            for tick in range(233*341):
                if tick in states:state=states[tick]
                v,t,x,mask,ctrl=state
                if tick in mask_events:mask=mask_events[tick];state=(v,t,x,mask,ctrl)
                assert mask&0xe1==0,'grayscale/emphasis unsupported by this adapter'
                y,d=divmod(tick,341)
                color=pixels[y*256+d-2] if 8<=y<232 and 2<=d<=257 else 0
                mode=((ctrl>>3)&3)|((ctrl>>3)&4)
                word=signals.get(tick,0)|(v<<56)|(t<<71)|(x<<86)|(mode<<89)|(mask<<92)|(color<<100)|(int(tick in scroll_access)<<106)
                out.write(f'{word:027x}\n')
        (a.out/f'frame{f}.palette').write_text(f'{packed_palette:048x}\n')
        summaries.append(dict(frame=f,**tally,forced_raw_rows=sorted(forced_raw),rgb_sha256=sha(a.capture/f'frame-{f:04d}.rgb'),stimulus_sha256=sha(a.out/f'frame{f}.hex')))
    result=dict(passed=True,scope=__doc__,physical=False,full_core_equivalence=False,
                first=a.first,last=a.last,frames=summaries,source_sha256=sha(Path(__file__)),
                inputs={n:sha(a.capture/n) for n in ['capture.json','nametable.bin','rows.bin','ppu-fetch.bin','writes.bin','frames.tsv']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,frames=len(summaries),first=a.first,last=a.last)))


if __name__=='__main__':main()
