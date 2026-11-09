"""Actual CPU races and independent live-range accounting for interior map DMA."""
import argparse,json,shutil
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once,sha
from test_nes_idle524_priority import case
from test_nes_map526_priority import map_fixture
from test_nes_tile532_edges import width


def prepare(trace,out):
    out.mkdir();source=[json.loads(x) for x in (trace/'packets.jsonl').read_text().splitlines()]
    with (out/'packets.jsonl').open('w') as f:
        for g in (905,906,907):
            rows=[(r.copy(),bytearray.fromhex(r[2])) for r in source if int.from_bytes(bytes.fromhex(r[2])[8:10],'little')==g]
            if g!=905:
                tiles=[r for r in rows if r[1][0]==7]
                maps=[r for r in rows if r[1][:2]==b'\x02\x02'][:7 if g==906 else 1]
                take=[tiles[0],*maps,tiles[1]]
                rows=rows[:1]+take+[r for r in rows[1:] if r not in take]
            for seq,(r,b) in enumerate(rows):
                b[2:4]=seq.to_bytes(2,'little');r[2]=b.hex();print(json.dumps(r),file=f)
            for stem in ('map','expected','frame'):
                name=f'{stem}-{g}.'+('rgb' if stem=='frame' else 'bin');shutil.copyfile(trace/name,out/name)


def fixture(s,l,body):
    s=width(map_fixture(s,l),1152)
    start=s.index('local function mapTail()');end=s.index('local function rowImage()',start)
    s=s[:start]+'''local selected680,live680,limit680
local function mapTail()
 local h,t=word(0x1252),word(0x1250)-8
 if t<=h+8 or (word(0x4000+h)&0x7000)==0x5000 or (word(0x4000+t)&0x7000)==0x5000 then return false end
 for j=h+8,t-8,8 do
  if (word(0x4000+j)&0x7000)==0x5000 then selected680=j;return true end
 end
 return false
end
local function records680()
 local rows={}
 for j=word(0x1252),word(0x1250)-8,8 do
  rows[#rows+1]={word(0x4000+j),word(0x4002+j),word(0x4004+j)}
 end
 return rows
end
local function key680(v)return string.format('%d:%d:%d',v[1],v[2],v[3])end
''' + s[end:]
    s=once(s,'owner=activeImage();tail=word(0x1250)-8',
        'owner=activeImage();tail=assert(selected680);live680=records680();limit680=word(0x1250)')
    start=s.index('local function checkRow(sent)');end=s.index('local function activeImage()',start)
    s=s[:start]+'''local function checkRow(sent)
 local expected={}
 for _,row in ipairs(live680)do
  local a,b,n=row[1],row[2],row[3]
  if sent and a==source and b==dest then local size=math.min(length,1152);a=a+size;b=b+size;n=n-size end
  if n>0 then expected[#expected+1]=key680({a,b,n})end
 end
 local actual={};for _,row in ipairs(records680())do actual[#actual+1]=key680(row)end
 table.sort(expected);table.sort(actual)
 assert(table.concat(actual,';')==table.concat(expected,';'),'live ranges lost/duplicated')
 if not sent then assert(rowImage()==savedRow,'deferred map wrote VRAM');return end
 local off=dest-(word(0x1034)==0 and 0x6000 or 0xa000)
 assert(rowImage()==file('map-'..FAULT..'.bin'):sub(off+1,off+math.min(length,1152)),'interior payload')
end
''' + s[end:]
    # Offer actual VBlank only after line240 to force late tile/map arbitration.
    # This masks the first poll, never changes the beam latch or DMA duration.
    pc=0x7e2000+body.index(bytes.fromhex('ad1242'),l['prefix523']-0x7e2000)
    s=once(s,'local function loaded()',f'''local first680=false
emu.addMemoryCallback(function()first680=true end,emu.callbackType.exec,{pc})
emu.addMemoryCallback(function()first680=false end,emu.callbackType.exec,{pc+3})
emu.addMemoryCallback(function(a,v)
 if first680 and held and not armed and emu.getState()['ppu.scanline']<240 then return v&127 end
end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function(a,v)
 assert(v==0xa5 and dmaRemaining==0,'progress before actual DMA completion')
end,emu.callbackType.write,0x601d)
local function loaded()''')
    return s


def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'input';prepare(a.trace,source);rows=[];body=(a.client/'body.bin').read_bytes()
    for g in (906,907):
        sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/f'map{g}');sub.out.mkdir()
        for name in ('head','stop','both','late_head','late_stop','cold','bad_manifest'):
            r=case(sub,g,name,edit_fixture=lambda s,l:fixture(s,l,body));rows.append(r)
            if r['grant']:assert r['size']==(1152 if g==906 else 64)
            print(g,name,'PASS',flush=True)
    r=dict(passed=True,client_SHA256=sha(a.client/'sink165.sfc'),races=rows,
        scope='Real CPU; partial1344->192 and whole64 interior map; live-range multiset, pixels, new head/STOP before or during DMA, cold and missing coverage.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
