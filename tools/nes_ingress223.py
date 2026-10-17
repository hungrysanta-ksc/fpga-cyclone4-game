# SPDX-License-Identifier: MIT
"""Paired2231 geometry: four literal physical map words, existing equal-run packing.

No cross-frame reuse, new frame RAM, source epoch change, or consumer map change.
This generator alone is not a board/release approval.
"""
from pathlib import Path
import argparse
import json
from nes_resident211 import ROOT, BASE, sha, once


def prepare(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    board = BASE/'probes/nes-status220/source02'
    arm = BASE/'probes/nes-startup222/arm02/src'
    pins = {}
    for root, names in [(board, ['nes_native_export203.sv','nes_native_spi165.sv']),
                        (arm, ['nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'])]:
        archive = root.parents[0] if root == board else root.parents[1]
        manifest = json.loads((archive/'manifest01.json').read_bytes())
        for name in names:
            f = root/name
            assert manifest[f.relative_to(archive).as_posix()] == sha(f), name
            pins[f.relative_to(BASE).as_posix()] = sha(f)
            (out/name).write_bytes(f.read_bytes())
    f = out/'nes_native_export203.sv'
    s = f.read_text().replace("16'h2031", "16'h2231")
    s = once(s, 'reg [8:0] pack_count;', 'reg [8:0] pack_count;reg map_repeat;')
    s = once(s, '    else if(query_kind==1||query_kind==5)', '''    else if(query_kind==0&&!map_repeat)
     tx_data={3'd0,generation,(13'h1000|pack_start),pack_count[3:0],held_data[59:0]};
    else if(query_kind==1||query_kind==5)''')
    s = once(s, '     end else if(pack_count==0)begin', '''     end else if(query_kind==0)begin
      // Physical13-bit tag and2-bit attributes, unchanged. Do not truncate
      // invalid source bits into an apparently valid packed record.
      if(data[63:15]!=0)fail(3);
      else if(pack_count==0)begin
       held_data<=data;pack_count<=1;map_repeat<=0;query_index<=query_index+1'b1;state<=ASK;
      end else if(map_repeat)begin
       if(data==held_data&&pack_count<256)begin
        pack_count<=pack_count+1'b1;query_index<=query_index+1'b1;state<=ASK;
       end else state<=VALUE; // Re-query immutable first non-run word.
      end else if(pack_count==1&&data==held_data)begin
       map_repeat<=1;pack_count<=2;query_index<=query_index+1'b1;state<=ASK;
      end else begin
       held_data<={4'd0,held_data[44:0],data[14:0]};
       pack_count<=pack_count+1'b1;query_index<=query_index+1'b1;
       state<=pack_count==3?VALUE:ASK;
      end
     end else if(pack_count==0)begin''')
    s = s.replace('pack_count<=0;', 'pack_count<=0;map_repeat<=0;')
    f.write_text(s, encoding='utf8', newline='\n')
    f = out/'nes_native_spi165.sv'
    s = f.read_text()
    s = once(s, 'total<=4+width(record_data[95:93]);',
             "total<=4+((record_data[95:93]==0&&record_data[76])?4'd8:width(record_data[95:93]));")
    # Existing max record12B, CRC, block room/seal, D0-D3 and CDC stay exact.
    f.write_text(s, encoding='utf8', newline='\n')
    f = out/'nes_native165.c'
    s = f.read_text().replace('0x2031', '0x2231')
    needle = ' if(kind!=7 || index<0x800){'
    s = once(s, needle, ''' if(kind==0&&(index&0x1000)){
  unsigned start=index&0xfff,n=(unsigned)(v>>60);
  uint64_t words=v&UINT64_C(0x0fffffffffffffff);
  if(s->state!=NES_NATIVE165_RECEIVING||gen!=s->generation||s->next_kind!=0||
     start!=s->at[0]||start>=s->counts[0]||!n||n>4||
     n!=((unsigned)s->counts[0]-start>4?4:(unsigned)s->counts[0]-start)||
     (words>>(15*n)))return fail(s,36);
  for(unsigned i=0;i<n;i++)if(!logical_record(s,0,gen,start+i,
      (words>>(15*(n-1-i)))&32767))return false;
  return true;
 }
''' + needle)
    s = once(s, '  if(n-pos<widths[kind])return fail(s,20);\n  uint64_t value=0;for(unsigned j=0;j<widths[kind];j++)',
             '  unsigned width=(kind==0&&(index&0x1000))?8:widths[kind];\n  if(n-pos<width)return fail(s,20);\n  uint64_t value=0;for(unsigned j=0;j<width;j++)')
    f.write_text(s, encoding='utf8', newline='\n')
    result = dict(source_pins=pins, public_source_sha256=sha(Path(__file__)),
                  wire_version='2231', new_frame_ram=False, cross_frame_reuse=False,
                  generated={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().out)))
