"""Offer the first background read before render enable reaches the bus.

No memory latency, priority, CPU/PPU CE, mapper commit, sample deadline or
fault suppression changes. Predict immutable tagged data in idle slots only.
"""
import argparse,json,shutil
from pathlib import Path
from nes_game147 import sha

def prepare(base,out,compact=False,reuse=False,readtail=False):
    m=json.loads((base/'inputs703.json').read_text())
    pins={n:m['changed'].get(n,h) for n,h in m['base'].items()}
    out.mkdir(parents=True,exist_ok=False)
    for n,h in pins.items():
        assert sha(base/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
    p=out/'rtl/ppu.sv';s=p.read_text()
    s=s.replace('assign game160_restart_hint=restart160;', '''//707 Start one dot earlier, before a new CPU request occupies the reader.
// re_sr[1] means next dot will drive ALE, so predict the complete pattern
// address. Otherwise first rendering is on the even read dot and retains
// the old external low latch (the same rule as restart160).
wire restart707=re_sr[0] && !re_sr[2] && scanline<240 &&
    !sprite_load_en && cycle>0 && cycle<336 &&
    (cycle[2:0]==4 || cycle[2:0]==6) &&
    read_2007_delayed==0 && write_2007_delayed==0;
assign game160_restart_hint=restart160 || restart707;''')
    s=s.replace('assign game147_prefetch_hint=restart160 ||', 'assign game147_prefetch_hint=restart707 || restart160 ||')
    s=s.replace('assign game148_hint_logic=sprite_low703 ?', '''assign game148_hint_logic=restart707 ?
    (re_sr[1] ? {1'b0,bg_patt,bg_name_table,cycle[1],vram[14:12]} :
               {1'b0,bg_patt,bg_name_table[7:4],vram_a_byte}) : sprite_low703 ?''')
    if compact:
        a=s.index('wire restart160 =');b=s.index('// Y/tile/attribute',a)
        s=s[:a]+'''//707 Share the restart admission/decode. Odd dot uses stage1 and the
// retained latch. Even dot can use stage0; when stage1 is also set the
// next ALE will drive the full calculated pattern address instead.
wire restart160 = !re_sr[2] && scanline<240 &&
    !sprite_load_en && cycle>0 && cycle<336 && cycle[2] &&
    (cycle[0] ? re_sr[1] : re_sr[0]) &&
    read_2007_delayed==0 && write_2007_delayed==0;
assign game160_restart_hint=restart160;
'''+s[b:]
        s=s.replace('assign game147_prefetch_hint=restart707 || restart160 ||', 'assign game147_prefetch_hint=restart160 ||')
        a=s.index('assign game148_hint_logic=');b=s.index('//154 fault-only',a)
        s=s[:a]+'''assign game148_hint_logic=sprite_low703 ?
    {1'b0,sprite_vram_addr[12:4],1'b0,sprite_vram_addr[2:0]} : restart160 ?
    {1'b0,bg_patt,bg_name_table[7:4],
     ((!cycle[0] && re_sr[1]) ? {bg_name_table[3:0],cycle[1],vram[14:12]} : vram_a_byte)} : overlap155 ?
    {1'b0,bg_patt1,bg_name_table[7:4],vram_din} :
    {1'b0,bg_patt1,bg_name_table,(cycle[2:0]>=5),vram[14:12]};
'''+s[b:]
    if reuse:
        # Reuse the existing full-pattern branch instead of adding another
        # eight-bit address selector. Only the bank bit needs early sampling.
        s=(base/'rtl/ppu.sv').read_text()
        anchor='wire normal155=is_rendering_d &&'
        assert s.count(anchor)==1
        s=s.replace(anchor,'''wire earlynormal707=re_sr[1] && !re_sr[2] && scanline<240 &&
    (cycle[2:0]==4 || cycle[2:0]==6);
wire normal155=(is_rendering_d || earlynormal707) &&''')
        s=s.replace('wire restart160 = re_sr[1] && !re_sr[2] && scanline<240 &&',
                    'wire restart160 = !re_sr[2] && scanline<240 &&')
        s=s.replace('(cycle[2:0]==5 || cycle[2:0]==7) &&',
                    '(re_sr[1] ? cycle[2] && cycle[0] : re_sr[0] && cycle[2] && !cycle[0]) &&')
        s=s.replace('assign game160_restart_hint=restart160;',
                    'assign game160_restart_hint=restart160 || (earlynormal707 && normal155);')
        s=s.replace("{1'b0,bg_patt1,bg_name_table,(cycle[2:0]>=5),vram[14:12]};",
                    "{1'b0,(earlynormal707 ? bg_patt : bg_patt1),bg_name_table,(cycle[2:0]>=5),vram[14:12]};")
    if readtail:
        s=s.replace('module VramAddressGen (', 'module VramAddressGen (\noutput wire [2:0] native_fine_next,',1)
        anchor='// Handle updating vram_t and vram_v'
        s=s.replace(anchor,'''//707 Reuse the actual fine-Y increment/mask; preview the next CE value.
wire [2:0] fine_increment707=(vram_v[14:12]+3'd1) & vram_t_mask[14:12];
assign native_fine_next=(inc_vertical || (trigger_2007 && is_rendering)) ?
    fine_increment707 : copy_vscroll ? vram_t[14:12] : vram_v[14:12];
'''+anchor,1)
        s=s.replace("(vram_v[14:12] + 1'd1) & vram_t_mask[14:12]",'fine_increment707')
        s=s.replace('wire native_scroll_effect;', 'wire native_scroll_effect;\nwire [2:0] native_fine_next;')
        s=s.replace('VramAddressGen vram0(', 'VramAddressGen vram0(.native_fine_next(native_fine_next),')
        s=s.replace('wire normal155=', '''// The last PPUDATA read advances fine Y at the end of this dot.
// Predict the following pattern read while its current NT/data demand is
// already supplied; the service still gives actual CPU/PPU demand priority.
wire readtail707=is_rendering_d && is_rendering && !sprite_load_en &&
    cycle>0 && cycle<336 && (cycle[2:0]==4 || cycle[2:0]==6) &&
    read_2007_delayed==5'b10000 && write_2007_delayed==0;
wire normal155=''')
        s=s.replace('assign game147_prefetch_hint=', 'assign game147_prefetch_hint=readtail707 || ')
        s=s.replace("bg_name_table,(cycle[2:0]>=5),vram[14:12]};", "bg_name_table,(cycle[2:0]>=5),(readtail707 ? native_fine_next : vram[14:12])};")
    p.write_text(s,encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    assert set(changed)=={'rtl/ppu.sv'}
    (out/'inputs707.json').write_text(json.dumps(dict(stage=707,scope=__doc__,compact=compact,reuse=reuse,readtail=readtail,base=pins,changed=changed,base_directory=str(base),constraints_changed=False,seed_changed=False),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--compact',action='store_true')
    p.add_argument('--reuse',action='store_true')
    p.add_argument('--readtail',action='store_true')
    a=p.parse_args();assert not(a.compact and a.reuse);prepare(a.base,a.out,a.compact,a.reuse,a.readtail)
