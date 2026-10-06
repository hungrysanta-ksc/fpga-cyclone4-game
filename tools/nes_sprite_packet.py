# One captured front8x8 sprite, original diagnostic only. SPDX-License-Identifier: MIT.
from pathlib import Path
from build_nes_fine_scroll import encode as bg_encode,decode as bg_decode
from build_nes_trace_replay import convert,palette
from verify_nes_rtl_fetch import PALETTE
def sprite_state(capture,frame,reads,chrdata,case):
    raw=[(v[0],*map(int,v[1:])) for line in (capture/'trace.tsv').read_text().splitlines() if (v:=line.split())]
    writes=[r for r in raw if r[0]=='ppu_write']
    assert [r[7] for r in writes if r[6]==0x2006][:2]==[63,0]
    assert [r[7] for r in writes if r[6]==0x2007][:32]==list(PALETTE)*8
    oam=bytearray(256);seen=set();cursor=0
    for kind,f,line,dot,tick,cpu,addr,value,physical in writes:
        if addr not in (0x2003,0x2004):continue
        assert f<6,'dynamic OAM unsupported'
        if addr==0x2003:cursor=value
        else:oam[cursor]=value;seen.add(cursor);cursor=(cursor+1)&255
    assert len(seen)==256
    visible=[i for i in range(64) if oam[i*4]<239]
    if case!='sprite':
        assert not visible
        return dict(count=0,oam_sha_input=bytes(oam).hex(),physical_tile=None,fetches=[]),bytes(32),bytes([0,240,0,48])
    assert visible==[0]
    y,tile,attr,x=oam[:4]
    assert attr==0 and y<231 and x<=248,'only unclipped front8x8 noflip/palette0 supported'
    fetches=[e for e in reads if e['frame']==frame and y<=e['line']<y+8 and e['dot']==261
             and e['offset']%16%8==e['line']-y]
    assert len(fetches)==16 and len({e['tile'] for e in fetches})==1
    key=fetches[0]['tile'];seenbytes=set()
    for e in fetches:
        off=e['offset']%16
        assert e['value']==chrdata[e['offset']] and off not in seenbytes
        seenbytes.add(off)
    assert seenbytes==set(range(16))
    data=convert(chrdata[key*16:key*16+16])+bytes(16)
    state=dict(count=1,source_oam=[y,tile,attr,x],physical_tile=key,
               fetches=[dict(line=e['line'],dot=e['dot'],tick=e['tick'],physical=e['offset'],value=e['value']) for e in fetches])
    return state,data,bytes([x,y+1,0,48])
def encode(frame,seq,features,chrdata,state,obj,oam):
    assert state['count'] in (0,1) and len(obj)==32 and len(oam)==4
    assert features['ppu_mask']==(30 if state['count'] else 10)
    assert features['ppu_ctrl']==136 and oam[2:]==bytes([0,48])
    # Extract BG only after accounting for the separately validated sprite channel.
    base=bytearray(bg_encode(frame,seq,dict(features,ppu_mask=10),chrdata))
    base[:4]=b'NSP1';base[7]=state['count']
    return bytes(base)+obj+palette()+oam
def decode(p,atlas):
    assert len(p)==2052 and p[:4]==b'NSP1' and p[7] in (0,1)
    assert p[2040:2048]==palette() and p[2050:2052]==bytes([0,48])
    assert p[2024:2040]==bytes(16),'only two source color planes supported'
    base=bytearray(p[:2008]);base[:4]=b'NFX1';base[7]=0
    bg=bytearray(bg_decode(bytes(base),atlas))
    x,y=p[2048:2050]
    if not p[7]:assert y==240;return bytes(bg)
    assert x<=248 and y<=232
    for row in range(8):
        lo,hi=p[2008+row*2:2010+row*2]
        for col in range(8):
            index=(lo>>(7-col)&1)|((hi>>(7-col)&1)<<1)
            if index:bg[(y+row)*256+x+col]=PALETTE[index]
    return bytes(bg)