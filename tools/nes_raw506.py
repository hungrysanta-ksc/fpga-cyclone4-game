# SPDX-License-Identifier: MIT
"""506 exact raw-color runs and one bounded ARM expansion; experimental only."""
import argparse,json,struct
from pathlib import Path
from hashlib import sha256
from check_nes_game478 import encode as old_encode
def sha(p):return sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def runs(raw):
    at=0
    while at<len(raw):
        n=1
        while n<256 and at+n<len(raw)and raw[at+n]==raw[at]:n+=1
        if n>=10:v=(n<<6)|raw[at]
        else:
            n=min(10,len(raw)-at);v=n<<60
            for i,c in enumerate(raw[at:at+n]):assert c<64;v|=c<<(6*(n-1-i))
        yield at,n,v
        at+=n
def encode(geometry,raw,generation):
    packets,counts,arrays=old_encode(geometry,raw,generation)
    records=[]
    for p in packets:
        at=0
        while at<len(p):
            key=int.from_bytes(p[at:at+2],'big');kind,index=key>>13,key&8191
            width=8 if kind==0 and index&4096 else [2,1,7,4,7,1,2,8][kind]
            q=p[at:at+4+width];at+=4+width
            if kind==7 and 0x1000<=index<0x1700:continue
            if kind==7 and index==0:q=q[:4]+b'\x22\x33'+q[6:]
            if kind==7 and index==1:
                records.extend(struct.pack('>HHQ',0xf000|a,generation,v)for a,n,v in runs(raw))
            records.append(q)
    out=[];b=bytearray()
    for q in records[:-1]:
        if len(b)+len(q)>256:out.append(bytes(b));b.clear()
        b+=q
    if b:out.append(bytes(b))
    out.append(records[-1]);return out,counts,arrays
def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False);patch=a.out/'patch';patch.mkdir()
    f=a.arm/'nes_native165.c';s=f.read_text()
    start=s.index(' if(s->next_kind==7){\n  /* Same two-byte')
    end=s.index(' if(kind<6){',start)
    # Wire kind6 raw is already rejected by record(); only the old per-pixel
    # expansion called this branch. Bounds move into its sole bulk caller.
    s=s[:start]+' if(s->next_kind==7)return fail(s,32);\n'+s[end:]
    start=s.index('  unsigned start=index-0x1000,n=');end=s.index(' unsigned k=(index>>8)',start)
    s=s[:start]+'''  unsigned start=index-0x1000,n=(unsigned)(v>>60),cap=(unsigned)s->patch_count*256;
  uint64_t colors=v&UINT64_C(0x0fffffffffffffff);
  if(s->next_kind!=7||start!=s->last_tile||start>=cap)return fail(s,33);
  unsigned left=cap-start;
  if(!n){
   n=(unsigned)(v>>6);
   if((v>>15)||n<10||n>256||n>left)return fail(s,33);
   memset(s->raw_pixels+start,(unsigned)v&63,n);
  }else{
   if(n>10||n!=(left>10?10:left)||(colors>>(6*n)))return fail(s,33);
   for(unsigned i=0;i<n;i++)s->raw_pixels[start+i]=(uint8_t)(colors>>(6*(n-1-i)))&63;
  }
  s->last_tile+=n;s->records+=n;s->bytes+=n;return true;
 }
'''+s[end:]
    s=once(s,'(v>>48)!=0x2232','(v>>48)!=0x2233')
    (patch/f.name).write_text(s,encoding='utf8',newline='\n')
    f=a.board/'nes_native_export203.sv';s=f.read_text()
    s=once(s,"16'h2232","16'h2233")
    s=once(s,"if(query_kind==7)tx_data={3'd7,generation,(13'h1000|pack_start),pack_count[3:0],held_data[59:0]};", """if(query_kind==7)begin
     if(map_repeat && pack_count>=10)
      tx_data={3'd7,generation,(13'h1000|pack_start),49'd0,pack_count,held_data[5:0]};
     else tx_data={3'd7,generation,(13'h1000|pack_start),pack_count[3:0],held_data[59:0]};
    end""")
    start=s.index("      held_data<={4'd0,held_data[53:0],data[5:0]};")
    end=s.index('     end else if(query_kind==1||query_kind==5)',start)
    s=s[:start]+'''      if(pack_count==0)begin
       held_data<=data;pack_count<=1;map_repeat<=1;query_index<=query_index+1'b1;state<=ASK;
      end else if(map_repeat && pack_count>=10 && (data[5:0]!=held_data[5:0] || pack_count==256))state<=VALUE;
      else begin
       held_data<={4'd0,held_data[53:0],data[5:0]};
       pack_count<=pack_count+1'b1;query_index<=query_index+1'b1;
       map_repeat<=map_repeat && data[5:0]==held_data[5:0];
       state<=pack_count==9 && !(map_repeat && data[5:0]==held_data[5:0])?VALUE:ASK;
      end
'''+s[end:]
    (a.out/f.name).write_text(s,encoding='utf8',newline='\n')
    r=dict(scope=__doc__,baseline_ARM=sha(a.arm/'nes_native165.c'),baseline_exporter=sha(f),patches={p.name:sha(p)for p in patch.iterdir()},exporter_SHA256=sha(a.out/f.name),new_persistent_RAM_B=0,wire_version='2233',delivery=False)
    (a.out/'prepare.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','board','out']:p.add_argument('--'+n,type=Path,required=True)
    print(json.dumps(prepare(p.parse_args())))
